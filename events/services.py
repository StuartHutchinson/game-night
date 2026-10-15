"""Business rules for an event: inventory, interest and the ranked list.

Vote secrecy: nothing returned from this module names the players who are
interested in a game, except the requesting player's own interest and the
runners (who are named on purpose, so people know who can teach a game).
"""

from dataclasses import dataclass, field

from django.db import transaction

from .models import GameCopy, Interest, Notice, Player, normalise_title


class RuleError(Exception):
    """A user-facing validation or permission error."""


@dataclass
class Runner:
    name: str
    run_min: int
    run_max: int


@dataclass
class RankedGame:
    title: str
    normalised_title: str
    copies: int
    bringers: list[str]
    box_min: int | None
    box_max: int | None
    interest_count: int
    runners: list[Runner] = field(default_factory=list)
    my_interest: Interest | None = None

    @property
    def needs_runner(self):
        return self.interest_count > 0 and not self.runners

    @property
    def my_range_outside_box(self):
        """Soft warning: my run range falls outside the box player count."""
        mine = self.my_interest
        if not mine or not mine.will_run:
            return False
        if self.box_min is not None and mine.run_min < self.box_min:
            return True
        if self.box_max is not None and mine.run_max > self.box_max:
            return True
        return False


def ranked_list(event, viewer=None):
    """Every game in the inventory, sorted by interest, then runners, then title."""
    copies = list(event.copies.select_related("owner"))
    interests = list(event.interests.select_related("player"))

    games = {}
    for copy in copies:
        game = games.get(copy.normalised_title)
        if game is None:
            game = games[copy.normalised_title] = RankedGame(
                title=copy.title,
                normalised_title=copy.normalised_title,
                copies=0,
                bringers=[],
                box_min=None,
                box_max=None,
                interest_count=0,
            )
        game.copies += 1
        if copy.owner.display_name not in game.bringers:
            game.bringers.append(copy.owner.display_name)
        if copy.box_min_players is not None:
            game.box_min = min(game.box_min or copy.box_min_players, copy.box_min_players)
        if copy.box_max_players is not None:
            game.box_max = max(game.box_max or copy.box_max_players, copy.box_max_players)

    for interest in interests:
        game = games.get(interest.normalised_title)
        if game is None:
            continue
        game.interest_count += 1
        if interest.will_run:
            game.runners.append(Runner(interest.player.display_name, interest.run_min, interest.run_max))
        if viewer is not None and interest.player_id == viewer.id:
            game.my_interest = interest

    for game in games.values():
        game.runners.sort(key=lambda r: r.name.casefold())

    return sorted(
        games.values(),
        key=lambda g: (-g.interest_count, -len(g.runners), g.title.casefold()),
    )


def _check_unlocked(event):
    if event.locked:
        raise RuleError("The organiser has locked this event, so changes are closed.")


def _parse_count(value, label):
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise RuleError(f"{label} must be a whole number.")
    if number < 1 or number > 99:
        raise RuleError(f"{label} must be between 1 and 99.")
    return number


def join_event(event, display_name):
    """Join under a display name. An existing name is rejoined (friendly-group trust model)."""
    name = " ".join((display_name or "").split())
    if not name:
        raise RuleError("Enter a display name.")
    if len(name) > 40:
        raise RuleError("Display names can be at most 40 characters.")
    existing = event.players.filter(display_name__iexact=name).first()
    if existing:
        return existing
    return Player.objects.create(event=event, display_name=name)


def add_game(player, title, box_min=None, box_max=None):
    event = player.event
    _check_unlocked(event)
    title = " ".join((title or "").split())
    if not title:
        raise RuleError("Enter a game title.")
    if len(title) > 100:
        raise RuleError("Game titles can be at most 100 characters.")
    box_min = _parse_count(box_min, "Box minimum")
    box_max = _parse_count(box_max, "Box maximum")
    if box_min is not None and box_max is not None and box_min > box_max:
        raise RuleError("Box minimum can't be more than the maximum.")
    return GameCopy.objects.create(
        event=event, owner=player, title=title, box_min_players=box_min, box_max_players=box_max
    )


@transaction.atomic
def remove_game(player, copy_id):
    """Remove one of the player's own copies. If it was the last copy, interests go too."""
    event = player.event
    _check_unlocked(event)
    copy = player.copies.filter(id=copy_id).first()
    if copy is None:
        raise RuleError("You can only remove games you added.")
    key = copy.normalised_title
    copy.delete()
    if event.copies.filter(normalised_title=key).exists():
        return
    affected = event.interests.filter(normalised_title=key).select_related("player")
    for interest in affected:
        if interest.player_id != player.id:
            Notice.objects.create(
                player=interest.player,
                message=f"{copy.title} is no longer being brought, so your interest in it was removed.",
            )
    affected.delete()


def set_interest(player, title_key, interested, will_run=False, run_min=None, run_max=None):
    """Create, update or clear a player's interest in a title."""
    event = player.event
    _check_unlocked(event)
    key = normalise_title(title_key or "")
    if not event.copies.filter(normalised_title=key).exists():
        raise RuleError("That game isn't in the inventory any more.")

    if not interested:
        player.interests.filter(normalised_title=key).delete()
        return None

    if will_run:
        run_min = _parse_count(run_min, "Minimum players")
        run_max = _parse_count(run_max, "Maximum players")
        if run_min is None or run_max is None:
            raise RuleError("Enter the minimum and maximum players you're happy to run it for.")
        if run_min > run_max:
            raise RuleError("Minimum players can't be more than the maximum.")
    else:
        run_min = run_max = None

    interest, _ = Interest.objects.update_or_create(
        player=player,
        normalised_title=key,
        defaults={"event": event, "will_run": will_run, "run_min": run_min, "run_max": run_max},
    )
    return interest


def pop_notices(player):
    notices = list(player.notices.order_by("created_at").values_list("message", flat=True))
    player.notices.all().delete()
    return notices

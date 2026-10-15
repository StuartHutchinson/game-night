import secrets

from django.db import models
from django.db.models.functions import Lower


def new_event_id():
    return secrets.token_urlsafe(9)


def new_secret_token():
    return secrets.token_urlsafe(24)


def normalise_title(title):
    """Matching key for game titles: trimmed, inner whitespace collapsed, case-insensitive."""
    return " ".join(title.split()).casefold()


class Event(models.Model):
    # The player link uses this id; the admin link uses admin_token.
    id = models.CharField(primary_key=True, max_length=16, default=new_event_id, editable=False)
    name = models.CharField(max_length=100)
    date = models.DateField()
    start_time = models.TimeField()
    location = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    admin_token = models.CharField(max_length=64, unique=True, default=new_secret_token, editable=False)
    locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Player(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="players")
    display_name = models.CharField(max_length=40)
    player_token = models.CharField(max_length=64, unique=True, default=new_secret_token, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                "event", Lower("display_name"), name="unique_display_name_per_event"
            ),
        ]

    def __str__(self):
        return self.display_name


class GameCopy(models.Model):
    """One row per physical copy a player is bringing."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="copies")
    owner = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="copies")
    title = models.CharField(max_length=100)
    normalised_title = models.CharField(max_length=100, db_index=True)
    box_min_players = models.PositiveSmallIntegerField(null=True, blank=True)
    box_max_players = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def save(self, *args, **kwargs):
        self.title = " ".join(self.title.split())
        self.normalised_title = normalise_title(self.title)
        super().save(*args, **kwargs)


class Interest(models.Model):
    """A player's interest in a game title (not a specific copy)."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="interests")
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="interests")
    normalised_title = models.CharField(max_length=100)
    will_run = models.BooleanField(default=False)
    run_min = models.PositiveSmallIntegerField(null=True, blank=True)
    run_max = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["player", "normalised_title"], name="one_interest_per_player_per_title"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(will_run=False, run_min__isnull=True, run_max__isnull=True)
                    | models.Q(
                        will_run=True,
                        run_min__gte=1,
                        run_max__gte=models.F("run_min"),
                    )
                ),
                name="valid_run_range",
            ),
        ]


class Notice(models.Model):
    """A one-off message shown to a player on their next visit."""

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="notices")
    message = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

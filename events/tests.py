import datetime

from django.test import TestCase
from django.urls import reverse

from . import services
from .models import Event, Interest, Notice


def make_event(**kwargs):
    defaults = {"name": "Friday games", "date": datetime.date(2026, 11, 6), "start_time": datetime.time(19, 0)}
    defaults.update(kwargs)
    return Event.objects.create(**defaults)


class InventoryTests(TestCase):
    def setUp(self):
        self.event = make_event()
        self.ann = services.join_event(self.event, "Ann")
        self.ben = services.join_event(self.event, "Ben")

    def test_duplicate_titles_merge_with_copy_count(self):
        services.add_game(self.ann, "Wingspan")
        services.add_game(self.ben, "  wingSPAN ")
        [game] = services.ranked_list(self.event)
        self.assertEqual(game.title, "Wingspan")
        self.assertEqual(game.copies, 2)
        self.assertEqual(game.bringers, ["Ann", "Ben"])

    def test_box_range_validation(self):
        with self.assertRaises(services.RuleError):
            services.add_game(self.ann, "Azul", box_min=4, box_max=2)
        with self.assertRaises(services.RuleError):
            services.add_game(self.ann, "", box_min=1, box_max=2)

    def test_can_only_remove_own_copy(self):
        copy = services.add_game(self.ann, "Azul")
        with self.assertRaises(services.RuleError):
            services.remove_game(self.ben, copy.id)

    def test_removing_last_copy_removes_interests_and_notifies(self):
        copy = services.add_game(self.ann, "Azul")
        services.set_interest(self.ann, "Azul", interested=True)
        services.set_interest(self.ben, "Azul", interested=True)
        services.remove_game(self.ann, copy.id)
        self.assertFalse(Interest.objects.exists())
        self.assertEqual(services.pop_notices(self.ben), [
            "Azul is no longer being brought, so your interest in it was removed."
        ])
        self.assertEqual(services.pop_notices(self.ann), [])
        self.assertEqual(services.pop_notices(self.ben), [])

    def test_removing_one_of_two_copies_keeps_interests(self):
        copy = services.add_game(self.ann, "Azul")
        services.add_game(self.ben, "Azul")
        services.set_interest(self.ben, "Azul", interested=True)
        services.remove_game(self.ann, copy.id)
        self.assertEqual(Interest.objects.count(), 1)
        self.assertFalse(Notice.objects.exists())


class InterestTests(TestCase):
    def setUp(self):
        self.event = make_event()
        self.ann = services.join_event(self.event, "Ann")
        services.add_game(self.ann, "Azul", box_min=2, box_max=4)

    def test_run_range_must_be_valid(self):
        for run_min, run_max in [(0, 3), (4, 2), (None, 3), ("x", 3)]:
            with self.assertRaises(services.RuleError):
                services.set_interest(self.ann, "Azul", True, will_run=True, run_min=run_min, run_max=run_max)

    def test_range_outside_box_is_allowed_with_warning(self):
        services.set_interest(self.ann, "Azul", True, will_run=True, run_min=2, run_max=5)
        [game] = services.ranked_list(self.event, viewer=self.ann)
        self.assertTrue(game.my_range_outside_box)

    def test_unticking_run_clears_range(self):
        services.set_interest(self.ann, "Azul", True, will_run=True, run_min=2, run_max=4)
        interest = services.set_interest(self.ann, "Azul", True, will_run=False, run_min=2, run_max=4)
        self.assertIsNone(interest.run_min)

    def test_interest_needs_game_in_inventory(self):
        with self.assertRaises(services.RuleError):
            services.set_interest(self.ann, "Catan", True)

    def test_locked_event_blocks_changes(self):
        self.event.locked = True
        self.event.save()
        with self.assertRaises(services.RuleError):
            services.set_interest(self.ann, "Azul", True)
        with self.assertRaises(services.RuleError):
            services.add_game(self.ann, "Catan")


class RankingTests(TestCase):
    def test_sort_by_interest_then_runners_then_title(self):
        event = make_event()
        players = [services.join_event(event, name) for name in ["A", "B", "C"]]
        for title in ["Zoo", "Apple", "Mango", "Banana"]:
            services.add_game(players[0], title)
        # Zoo: 3 interested. Mango and Banana: 2 each, Mango has a runner. Apple: 0.
        for p in players:
            services.set_interest(p, "Zoo", True)
        services.set_interest(players[0], "Mango", True, will_run=True, run_min=2, run_max=4)
        services.set_interest(players[1], "Mango", True)
        services.set_interest(players[0], "Banana", True)
        services.set_interest(players[1], "Banana", True)

        games = services.ranked_list(event)
        self.assertEqual([g.title for g in games], ["Zoo", "Mango", "Banana", "Apple"])
        self.assertEqual([g.interest_count for g in games], [3, 2, 2, 0])
        self.assertTrue(games[0].needs_runner)
        self.assertFalse(games[1].needs_runner)
        self.assertFalse(games[3].needs_runner)


class JoinTests(TestCase):
    def setUp(self):
        self.event = make_event()

    def test_rejoin_by_name_returns_same_player(self):
        first = services.join_event(self.event, "Ann")
        again = services.join_event(self.event, "  ann ")
        self.assertEqual(first.id, again.id)

    def test_join_sets_cookie_and_returning_player_is_recognised(self):
        response = self.client.post(reverse("join", args=[self.event.id]), {"display_name": "Ann"})
        self.assertEqual(response.status_code, 302)
        page = self.client.get(reverse("event", args=[self.event.id]))
        self.assertContains(page, "Playing as <strong>Ann</strong>", html=False)


class VoteSecrecyTests(TestCase):
    """No page shown to anyone may reveal which players voted for a game."""

    def setUp(self):
        self.event = make_event()
        self.bringer = services.join_event(self.event, "Bringer")
        self.voter = services.join_event(self.event, "SecretVoter")
        self.runner = services.join_event(self.event, "OpenRunner")
        services.add_game(self.bringer, "Wingspan")
        services.set_interest(self.voter, "Wingspan", True)
        services.set_interest(self.runner, "Wingspan", True, will_run=True, run_min=2, run_max=4)

    def _as(self, player):
        self.client.cookies[f"gn_{self.event.id}"] = player.player_token

    def test_other_players_cannot_see_who_voted(self):
        self._as(self.bringer)
        response = self.client.get(reverse("event", args=[self.event.id]))
        self.assertContains(response, "Wingspan")
        self.assertContains(response, "OpenRunner")  # runners are named on purpose
        self.assertNotContains(response, "SecretVoter")

    def test_anonymous_viewer_cannot_see_who_voted(self):
        response = self.client.get(reverse("event", args=[self.event.id]))
        self.assertNotContains(response, "SecretVoter")

    def test_htmx_board_does_not_reveal_voters(self):
        self._as(self.bringer)
        response = self.client.post(
            reverse("game_add", args=[self.event.id]), {"title": "Azul"}, HTTP_HX_REQUEST="true"
        )
        self.assertContains(response, "Azul")
        self.assertNotContains(response, "SecretVoter")

    def test_organiser_page_does_not_reveal_voters(self):
        response = self.client.get(reverse("manage", args=[self.event.admin_token]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "SecretVoter")

    def test_ranked_list_only_exposes_viewers_own_interest(self):
        [game] = services.ranked_list(self.event, viewer=self.bringer)
        self.assertIsNone(game.my_interest)
        self.assertEqual([r.name for r in game.runners], ["OpenRunner"])
        [game] = services.ranked_list(self.event, viewer=self.voter)
        self.assertEqual(game.my_interest.player_id, self.voter.id)


class OrganiserTests(TestCase):
    def test_create_event_then_lock_and_unlock(self):
        response = self.client.post(
            reverse("home"), {"name": "Games", "date": "2026-11-06", "start_time": "19:00"}
        )
        event = Event.objects.get()
        self.assertRedirects(response, reverse("manage", args=[event.admin_token]))
        page = self.client.get(response.url)
        self.assertContains(page, reverse("event", args=[event.id]))

        self.client.post(response.url, {"action": "lock"})
        event.refresh_from_db()
        self.assertTrue(event.locked)
        self.client.post(response.url, {"action": "unlock"})
        event.refresh_from_db()
        self.assertFalse(event.locked)

    def test_wrong_admin_token_is_404(self):
        make_event()
        self.assertEqual(self.client.get(reverse("manage", args=["nope"])).status_code, 404)

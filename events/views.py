from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import services
from .forms import EventForm
from .models import Event, Player, normalise_title


def _cookie_name(event):
    return f"gn_{event.id}"


def _current_player(request, event):
    token = request.COOKIES.get(_cookie_name(event))
    if not token:
        return None
    return Player.objects.filter(event=event, player_token=token).first()


def _set_player_cookie(response, event, player):
    response.set_cookie(
        _cookie_name(event),
        player.player_token,
        max_age=settings.PLAYER_COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
        secure=not settings.DEBUG,
    )


def _board_context(event, player, error=None, error_title=None):
    """error_title puts the error on that game's card instead of the top of the board."""
    return {
        "event": event,
        "player": player,
        "games": services.ranked_list(event, viewer=player),
        "my_copies": list(player.copies.all()) if player else [],
        "error": error,
        "error_title": error_title,
    }


def _respond(request, event, player, error=None, error_title=None):
    """HTMX requests get the refreshed board; plain form posts get the full page back."""
    if request.headers.get("HX-Request"):
        return render(request, "events/_board.html", _board_context(event, player, error, error_title))
    if error:
        context = _board_context(event, player, error, error_title)
        context["notices"] = []
        return render(request, "events/event.html", context, status=400)
    return redirect("event", event_id=event.id)


def home(request):
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save()
            return redirect("manage", admin_token=event.admin_token)
    else:
        form = EventForm()
    return render(request, "events/home.html", {"form": form})


def event_page(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    player = _current_player(request, event)
    context = _board_context(event, player)
    context["notices"] = services.pop_notices(player) if player else []
    return render(request, "events/event.html", context)


@require_POST
def join(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    try:
        player = services.join_event(event, request.POST.get("display_name"))
    except services.RuleError as e:
        context = _board_context(event, None, error=str(e))
        context["notices"] = []
        context["join_name"] = request.POST.get("display_name", "")
        return render(request, "events/event.html", context, status=400)
    response = redirect("event", event_id=event.id)
    _set_player_cookie(response, event, player)
    return response


@require_POST
def leave(request, event_id):
    """Forget this device's player (e.g. to switch name). The player's data stays."""
    event = get_object_or_404(Event, id=event_id)
    response = redirect("event", event_id=event.id)
    response.delete_cookie(_cookie_name(event))
    return response


def _require_player(request, event):
    player = _current_player(request, event)
    if player is None:
        raise Http404("Join the event first.")
    return player


@require_POST
def game_add(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    player = _require_player(request, event)
    error = None
    try:
        services.add_game(
            player,
            request.POST.get("title"),
            request.POST.get("box_min"),
            request.POST.get("box_max"),
        )
    except services.RuleError as e:
        error = str(e)
    return _respond(request, event, player, error)


@require_POST
def game_remove(request, event_id, copy_id):
    event = get_object_or_404(Event, id=event_id)
    player = _require_player(request, event)
    error = None
    try:
        services.remove_game(player, copy_id)
    except services.RuleError as e:
        error = str(e)
    return _respond(request, event, player, error)


@require_POST
def interest(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    player = _require_player(request, event)
    error = None
    try:
        services.set_interest(
            player,
            request.POST.get("title"),
            interested=request.POST.get("interested") == "1",
            will_run=request.POST.get("will_run") == "1",
            run_min=request.POST.get("run_min"),
            run_max=request.POST.get("run_max"),
        )
    except services.RuleError as e:
        error = str(e)
    return _respond(request, event, player, error, error_title=normalise_title(request.POST.get("title", "")))


def manage(request, admin_token):
    event = get_object_or_404(Event, admin_token=admin_token)
    saved = False
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "lock":
            event.locked = True
            event.save(update_fields=["locked"])
            return redirect("manage", admin_token=admin_token)
        if action == "unlock":
            event.locked = False
            event.save(update_fields=["locked"])
            return redirect("manage", admin_token=admin_token)
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            saved = True
    else:
        form = EventForm(instance=event)
    player_url = request.build_absolute_uri(reverse("event", args=[event.id]))
    admin_url = request.build_absolute_uri(reverse("manage", args=[event.admin_token]))
    return render(
        request,
        "events/manage.html",
        {
            "event": event,
            "form": form,
            "saved": saved,
            "player_url": player_url,
            "admin_url": admin_url,
            "player_count": event.players.count(),
            "games": services.ranked_list(event),
        },
    )

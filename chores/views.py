from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Chore, Completion, Member
from .rotation import ROTATION_ANCHOR, responsible_member


def home(request):
    """The root path is just a doorway to the board."""
    return redirect("chores:board")


def _row_context(chore, today, now):
    """Build one `_chore_row` context dict per `_docs/api.md`.

    `overdue` is always falsy here; #13 fills it in.
    """
    return {
        "chore": chore,
        "responsible_member": responsible_member(chore, today, ROTATION_ANCHOR),
        "done_this_period": Completion.objects.completed_in_current_period(
            chore, now
        ),
        "overdue": None,
    }


def build_board_context(now=None):
    """Shared board context for `chores:board` and `chores:board_list`.

    #10 inlined this as a nested `rows_for` closure inside `board()`; it is
    hoisted here so the full page and the polled `_board_list` fragment build
    their daily / weekly grouping from one place and cannot drift.

    Returns `daily_chores`, `weekly_chores` (iterables of `_chore_row` context
    per `_docs/api.md`), `overdue_count` (always `0` until #13), and
    `has_active_chores` (drives `board.html`'s empty state).

    `now` may be injected for tests; it defaults to the current local time.
    """
    now = now or timezone.localtime()
    today = now.date()

    def rows_for(frequency):
        chores = Chore.objects.filter(
            is_active=True, frequency=frequency
        ).order_by("name")
        return [_row_context(chore, today, now) for chore in chores]

    daily_chores = rows_for(Chore.Frequency.DAILY)
    weekly_chores = rows_for(Chore.Frequency.WEEKLY)

    return {
        "daily_chores": daily_chores,
        "weekly_chores": weekly_chores,
        "overdue_count": 0,
        "has_active_chores": bool(daily_chores or weekly_chores),
    }


def board(request):
    """Full board page: active chores grouped daily / weekly, ordered by name."""
    return render(request, "chores/board.html", build_board_context())


def board_list(request):
    """Polled fragment: the daily / weekly chore list only.

    `GET /board/list/` (`chores:board_list`), refreshed every 10s by the board
    page. Returns the `_board_list` partial (no `<html>` wrapper), status 200,
    built from the same `build_board_context` the full page uses. GET only, no
    CSRF. The overdue banner is deliberately not rendered here — per
    `_docs/design-system.md` it updates via an out-of-band swap from the
    complete / swap responses, not from this poll.
    """
    return render(
        request,
        "chores/partials/_board_list.html",
        build_board_context(),
    )


def _acting_member(request):
    """Resolve the member a mutation is attributed to.

    Reads the session key defensively and falls back to the first active
    member; returns ``None`` only when no active member exists at all.
    """
    # TODO(#17): use session["current_member_id"] once the picker lands
    member_id = request.session.get("current_member_id")
    if member_id is not None:
        member = Member.objects.filter(pk=member_id).first()
        if member is not None:
            return member
    return Member.objects.filter(is_active=True).first()


@require_POST
def chore_complete(request, pk):
    """Record a `Completion` for the current period and swap the chore row.

    Idempotent per period: a second POST in the same period creates no extra
    `Completion` and re-renders the row unchanged (still done). Returns the
    `_chore_row` partial only, status 200. Unknown or inactive `pk` -> 404.
    """
    chore = get_object_or_404(Chore, pk=pk, is_active=True)
    now = timezone.localtime()
    today = now.date()

    member = _acting_member(request)
    if member is None:
        context = _row_context(chore, today, now)
        context["error"] = True
        return render(request, "chores/partials/_chore_row.html", context)

    if not Completion.objects.completed_in_current_period(chore, now):
        Completion.objects.create(chore=chore, member=member)

    return render(
        request,
        "chores/partials/_chore_row.html",
        _row_context(chore, today, now),
    )

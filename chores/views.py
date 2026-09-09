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


def board(request):
    """Full board page: active chores grouped daily / weekly, ordered by name."""
    now = timezone.localtime()
    today = now.date()

    def rows_for(frequency):
        chores = Chore.objects.filter(
            is_active=True, frequency=frequency
        ).order_by("name")
        return [_row_context(chore, today, now) for chore in chores]

    daily_chores = rows_for(Chore.Frequency.DAILY)
    weekly_chores = rows_for(Chore.Frequency.WEEKLY)

    context = {
        "daily_chores": daily_chores,
        "weekly_chores": weekly_chores,
        "has_active_chores": bool(daily_chores or weekly_chores),
    }
    return render(request, "chores/board.html", context)


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

from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Chore, Completion
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

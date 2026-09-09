"""Decide whether a chore is currently overdue, and by how many periods.

:func:`overdue_status` is a pure function: it never touches the ORM and never
calls :func:`django.utils.timezone.now`. The caller passes ``reference`` (the
"now" to judge against) and ``last_completed_at`` (the most recent completion
timestamp, or ``None`` if the chore has never been done). #13 renders the
result on the board.

Period bucketing is not re-implemented here: the weekly branch reuses
:func:`chores.periods.period_key` for the "same ISO week" check. All calendar
comparisons happen in local time via :func:`django.utils.timezone.localtime`,
matching ``chores/periods.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

from django.utils import timezone

from .periods import DAILY, WEEKLY, period_key


@dataclass(frozen=True)
class OverdueStatus:
    """Result of :func:`overdue_status`.

    ``missed_periods`` is the number of whole periods that have elapsed since
    the chore was last done without it being done again; ``is_overdue`` is
    simply ``missed_periods > 0``.
    """

    is_overdue: bool
    missed_periods: int


def _local(dt):
    """``dt`` in local time; aware datetimes are converted, naive ones kept."""
    return timezone.localtime(dt) if timezone.is_aware(dt) else dt


def overdue_status(frequency, last_completed_at, reference, daily_cutoff=time(0, 0)):
    """Return an :class:`OverdueStatus` for a chore.

    ``frequency`` is ``"daily"`` or ``"weekly"`` (anything else raises
    ``ValueError``). ``last_completed_at`` is a tz-aware ``datetime`` or
    ``None``. ``reference`` is a tz-aware ``datetime``. ``daily_cutoff`` is a
    naive ``time``: for daily chores, a chore done on the previous local day is
    only overdue once ``reference``'s local time reaches the cutoff (a grace
    window). It is ignored for weekly chores.
    """
    if frequency not in (DAILY, WEEKLY):
        raise ValueError(f"Unknown frequency: {frequency!r}")

    if last_completed_at is None:
        return OverdueStatus(is_overdue=True, missed_periods=1)

    ref_local = _local(reference)
    last_local = _local(last_completed_at)

    if frequency == DAILY:
        days = (ref_local.date() - last_local.date()).days
        if days <= 0:
            return OverdueStatus(is_overdue=False, missed_periods=0)
        if ref_local.time() < daily_cutoff:
            days -= 1
        return OverdueStatus(is_overdue=days > 0, missed_periods=days)

    # Weekly: compare ISO year-week.
    if period_key(WEEKLY, reference) == period_key(WEEKLY, last_completed_at):
        return OverdueStatus(is_overdue=False, missed_periods=0)

    ref_iso = ref_local.isocalendar()
    last_iso = last_local.isocalendar()
    weeks = (
        date.fromisocalendar(ref_iso[0], ref_iso[1], 1)
        - date.fromisocalendar(last_iso[0], last_iso[1], 1)
    ).days // 7
    if weeks <= 0:
        return OverdueStatus(is_overdue=False, missed_periods=0)
    return OverdueStatus(is_overdue=True, missed_periods=weeks)

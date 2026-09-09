"""The shared "which period does this datetime fall in?" primitive.

:func:`period_key` is the single place the period-bucketing logic lives. It is
imported by :class:`chores.models.Completion` (this issue, #6) and reused by the
overdue calculation (#8) and the mark-done endpoint (#11) -- there must be no
second copy of this logic anywhere.

The key is always computed in the household's local time
(``django.utils.timezone.localtime``) so that "today" lines up with the local
calendar day. ``USE_TZ`` is ``True`` and ``TIME_ZONE`` in settings is the
reference zone.
"""

from __future__ import annotations

from django.utils import timezone

DAILY = "daily"
WEEKLY = "weekly"


def period_key(frequency, dt):
    """Return the period key for ``dt`` given a chore ``frequency``.

    ``frequency`` is ``"daily"`` or ``"weekly"``. ``dt`` is a ``datetime``;
    aware datetimes are converted to local time, naive datetimes are assumed
    to already be local.

    * Daily -> local calendar date, ``"2026-09-10"``.
    * Weekly -> ISO year and week, ``"2026-W37"``.

    Any other ``frequency`` raises ``ValueError``.
    """
    local = timezone.localtime(dt) if timezone.is_aware(dt) else dt

    if frequency == DAILY:
        return local.strftime("%Y-%m-%d")
    if frequency == WEEKLY:
        iso = local.isocalendar()
        return f"{iso[0]:04d}-W{iso[1]:02d}"
    raise ValueError(f"Unknown frequency: {frequency!r}")

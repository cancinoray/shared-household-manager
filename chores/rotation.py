"""The "whose turn is it?" scheduling primitive.

The core of this module is the pure function :func:`whose_turn`. It performs no
ORM queries, touches no HTTP or template machinery, and never calls
``timezone.now()`` -- every time-dependent input is passed in as an argument.
Keep it that way.

:func:`responsible_member` (#7) is the DB-aware wrapper on top: it builds a
chore's rotation from the ORM, calls :func:`whose_turn` for the base result,
and applies a one-off :class:`chores.models.Swap` override for that period.
#10 renders the result.
"""

from __future__ import annotations

from datetime import datetime

DAILY = "daily"
WEEKLY = "weekly"


def whose_turn(rotation, frequency, reference_date, anchor_date):
    """Return the ``Member`` whose turn it is for ``reference_date``.

    ``rotation`` is an already-ordered sequence of ``Member`` (the caller
    sorts it, e.g. via ``Chore.rotation_members()``). ``frequency`` is
    ``"daily"`` or ``"weekly"``. ``reference_date`` and ``anchor_date`` are
    ``datetime.date`` instances.

    The ``anchor_date`` is period index 0. For ``"daily"`` each calendar day
    advances the rotation by one; for ``"weekly"`` the rotation advances every
    7 days measured from ``anchor_date`` -- so ``anchor_date`` itself defines
    the week alignment (a rotation anchored on a Monday rolls over on
    Mondays; anchored on a Thursday it rolls over on Thursdays).

    Behaviour at the edges:

    * Empty ``rotation`` -> ``None`` (never raises, never ``IndexError``).
    * Single-member ``rotation`` -> that member, for any date.
    * ``reference_date == anchor_date`` -> ``rotation[0]``.
    * ``reference_date`` before ``anchor_date`` is allowed and deterministic,
      not an error: Python's ``%`` wraps negative period indexes correctly,
      so e.g. the day before the anchor of a 3-member daily rotation is
      ``rotation[-1 % 3] == rotation[2]``.
    * Any ``frequency`` other than ``"daily"`` or ``"weekly"`` raises
      ``ValueError``.
    """
    if not rotation:
        return None

    delta_days = (reference_date - anchor_date).days

    if frequency == DAILY:
        period_index = delta_days
    elif frequency == WEEKLY:
        period_index = delta_days // 7
    else:
        raise ValueError(f"Unknown frequency: {frequency!r}")

    return rotation[period_index % len(rotation)]


def responsible_member(chore, reference_date, anchor_date):
    """Return the ``Member`` responsible for ``chore`` on ``reference_date``,
    applying any one-off :class:`~chores.models.Swap` for that period.

    Unlike :func:`whose_turn`, this function *is* DB-aware: it reads the
    chore's rotation via ``Chore.rotation_members()`` and looks up a ``Swap``
    row. It still takes its dates as arguments and never reads the wall clock.

    Steps:

    1. Build the ordered rotation for ``chore`` and call :func:`whose_turn`
       to get the *base* member.
    2. Look up a ``Swap`` for ``(chore, period_key)`` where ``period_key`` is
       derived from ``reference_date`` (see below).
    3. If a swap exists **and** ``swap.from_member`` equals the base member,
       return ``swap.to_member``. Otherwise return the base member -- a swap
       whose ``from_member`` no longer matches the recomputed base (e.g. the
       rotation was edited after the swap was made) is silently ignored.

    An empty rotation returns ``None``; a swap alone never invents a
    responsible member.

    ``period_key`` note: :func:`chores.periods.period_key` takes a
    ``datetime`` but this wrapper receives a ``date``. We widen it to a naive
    midnight ``datetime`` (``datetime.combine(reference_date, time.min)``).
    ``period_key`` treats a naive datetime as already-local, so the daily key
    is ``reference_date`` itself and the weekly key is its ISO year-week --
    exactly the bucket #6/#10 compute for that calendar day.
    """
    from . import periods
    from .models import Swap

    rotation = chore.rotation_members()
    base = whose_turn(rotation, chore.frequency, reference_date, anchor_date)
    if base is None:
        return None

    key = periods.period_key(
        chore.frequency, datetime.combine(reference_date, datetime.min.time())
    )
    swap = Swap.objects.filter(chore=chore, period_key=key).first()
    if swap is not None and swap.from_member_id == base.id:
        return swap.to_member
    return base

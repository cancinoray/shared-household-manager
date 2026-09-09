"""The "whose turn is it?" scheduling primitive.

This module holds a single pure function, :func:`whose_turn`. It performs no
ORM queries, touches no HTTP or template machinery, and never calls
``timezone.now()`` -- every time-dependent input is passed in as an argument.

#7 wraps this with a DB-aware convenience layer and swap overrides; #10
renders the result. This function only does the arithmetic.
"""

from __future__ import annotations

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

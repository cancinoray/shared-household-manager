"""The curated preset chore list.

This is the single source of truth for the presets a new household can load
with ``manage.py load_presets``. The ``name`` values are the source of truth
for idempotency — do not reword them without a migration.
"""

from .models import Chore

PRESET_CHORES = [
    ("Wash dishes", Chore.Frequency.DAILY),
    ("Wipe kitchen counters", Chore.Frequency.DAILY),
    ("Take out trash", Chore.Frequency.DAILY),
    ("Sweep floors", Chore.Frequency.DAILY),
    ("Clean bathroom", Chore.Frequency.WEEKLY),
    ("Vacuum", Chore.Frequency.WEEKLY),
    ("Change bed sheets", Chore.Frequency.WEEKLY),
    ("Mop floors", Chore.Frequency.WEEKLY),
]

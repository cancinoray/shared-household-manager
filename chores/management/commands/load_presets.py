from django.core.management.base import BaseCommand

from chores.models import Chore
from chores.presets import PRESET_CHORES


class Command(BaseCommand):
    help = "Create any missing preset chores. Idempotent; never modifies existing rows."

    def handle(self, *args, **options):
        created = 0
        skipped = 0
        for name, frequency in PRESET_CHORES:
            _, was_created = Chore.objects.get_or_create(
                name=name,
                defaults={"frequency": frequency, "is_active": True, "notes": ""},
            )
            if was_created:
                created += 1
            else:
                skipped += 1
        self.stdout.write(f"Created {created}, skipped {skipped} (already present)")

from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from .models import Chore, Member
from .presets import PRESET_CHORES


class SmokeTest(TestCase):
    def test_home_returns_200(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)


class MemberModelTest(TestCase):
    def test_str_returns_name(self):
        member = Member.objects.create(name="Alex")
        self.assertEqual(str(member), "Alex")

    def test_duplicate_name_raises_integrity_error(self):
        Member.objects.create(name="Alex")
        with self.assertRaises(IntegrityError):
            Member.objects.create(name="Alex")


class ChoreModelTest(TestCase):
    def test_str_returns_name(self):
        chore = Chore.objects.create(name="Dishes", frequency=Chore.Frequency.DAILY)
        self.assertEqual(str(chore), "Dishes")

    def test_invalid_frequency_fails_full_clean(self):
        chore = Chore(name="Dishes", frequency="monthly")
        with self.assertRaises(ValidationError):
            chore.full_clean()

    def test_daily_and_weekly_round_trip_via_full_clean(self):
        for value in ("daily", "weekly"):
            chore = Chore(name=f"Chore {value}", frequency=value)
            chore.full_clean()
            chore.save()
            self.assertEqual(Chore.objects.get(pk=chore.pk).frequency, value)

    def test_duplicate_name_raises_integrity_error(self):
        Chore.objects.create(name="Dishes", frequency=Chore.Frequency.DAILY)
        with self.assertRaises(IntegrityError):
            Chore.objects.create(name="Dishes", frequency=Chore.Frequency.WEEKLY)

    def test_notes_defaults_to_empty_string(self):
        chore = Chore.objects.create(name="Dishes", frequency=Chore.Frequency.DAILY)
        self.assertEqual(chore.notes, "")


class LoadPresetsCommandTest(TestCase):
    def _run(self):
        out = StringIO()
        call_command("load_presets", stdout=out)
        return out.getvalue().strip()

    def test_empty_db_creates_all_eight_presets(self):
        self._run()
        self.assertEqual(Chore.objects.count(), 8)
        by_name = {c.name: c for c in Chore.objects.all()}
        for name, frequency in PRESET_CHORES:
            self.assertIn(name, by_name)
            self.assertEqual(by_name[name].frequency, frequency)
            self.assertTrue(by_name[name].is_active)
            self.assertEqual(by_name[name].notes, "")

    def test_first_run_reports_created_eight(self):
        self.assertEqual(self._run(), "Created 8, skipped 0 (already present)")

    def test_second_run_is_idempotent(self):
        self._run()
        second = self._run()
        self.assertEqual(Chore.objects.count(), 8)
        self.assertEqual(second, "Created 0, skipped 8 (already present)")

    def test_existing_chore_with_same_name_is_not_modified(self):
        Chore.objects.create(
            name="Wash dishes",
            frequency=Chore.Frequency.WEEKLY,
            notes="hand wash only",
            is_active=False,
        )
        self._run()
        self.assertEqual(Chore.objects.filter(name="Wash dishes").count(), 1)
        chore = Chore.objects.get(name="Wash dishes")
        self.assertEqual(chore.frequency, Chore.Frequency.WEEKLY)
        self.assertEqual(chore.notes, "hand wash only")
        self.assertFalse(chore.is_active)
        self.assertEqual(Chore.objects.count(), 8)

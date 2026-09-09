from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

from .models import Chore, Completion, Member, RotationSlot, Swap
from .periods import period_key
from .presets import PRESET_CHORES
from .rotation import responsible_member, whose_turn


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


class RotationSlotModelTest(TestCase):
    def setUp(self):
        self.chore = Chore.objects.create(
            name="Vacuum", frequency=Chore.Frequency.WEEKLY
        )
        self.sam = Member.objects.create(name="Sam")
        self.alex = Member.objects.create(name="Alex")
        self.jo = Member.objects.create(name="Jo")

    def test_str_is_readable(self):
        slot = RotationSlot.objects.create(chore=self.chore, member=self.sam, position=0)
        self.assertEqual(str(slot), "Vacuum #0: Sam")

    def test_rotation_members_reads_back_in_position_order(self):
        RotationSlot.objects.create(chore=self.chore, member=self.jo, position=2)
        RotationSlot.objects.create(chore=self.chore, member=self.sam, position=0)
        RotationSlot.objects.create(chore=self.chore, member=self.alex, position=1)
        self.assertEqual(
            self.chore.rotation_members(), [self.sam, self.alex, self.jo]
        )

    def test_rotation_order_is_by_position_not_contiguity(self):
        RotationSlot.objects.create(chore=self.chore, member=self.jo, position=5)
        RotationSlot.objects.create(chore=self.chore, member=self.sam, position=0)
        RotationSlot.objects.create(chore=self.chore, member=self.alex, position=3)
        self.assertEqual(
            self.chore.rotation_members(), [self.sam, self.alex, self.jo]
        )

    def test_duplicate_position_within_chore_raises_integrity_error(self):
        RotationSlot.objects.create(chore=self.chore, member=self.sam, position=0)
        with self.assertRaises(IntegrityError):
            RotationSlot.objects.create(chore=self.chore, member=self.alex, position=0)

    def test_same_member_twice_in_one_chore_raises_integrity_error(self):
        RotationSlot.objects.create(chore=self.chore, member=self.sam, position=0)
        with self.assertRaises(IntegrityError):
            RotationSlot.objects.create(chore=self.chore, member=self.sam, position=1)

    def test_same_position_under_two_chores_is_allowed(self):
        other = Chore.objects.create(name="Mop floors", frequency=Chore.Frequency.WEEKLY)
        RotationSlot.objects.create(chore=self.chore, member=self.sam, position=0)
        RotationSlot.objects.create(chore=other, member=self.alex, position=0)
        self.assertEqual(RotationSlot.objects.filter(position=0).count(), 2)

    def test_same_member_in_two_chores_is_allowed(self):
        other = Chore.objects.create(name="Mop floors", frequency=Chore.Frequency.WEEKLY)
        RotationSlot.objects.create(chore=self.chore, member=self.sam, position=0)
        RotationSlot.objects.create(chore=other, member=self.sam, position=0)
        self.assertEqual(RotationSlot.objects.filter(member=self.sam).count(), 2)

    def test_rotation_members_on_empty_rotation_returns_empty_list(self):
        self.assertEqual(self.chore.rotation_members(), [])

    def test_member_in_rotation_cannot_be_hard_deleted(self):
        RotationSlot.objects.create(chore=self.chore, member=self.sam, position=0)
        with self.assertRaises(IntegrityError):
            self.sam.delete()


class WhoseTurnTest(TestCase):
    ANCHOR = date(2026, 1, 5)

    def setUp(self):
        self.alex = Member.objects.create(name="Alex")
        self.blair = Member.objects.create(name="Blair")
        self.casey = Member.objects.create(name="Casey")
        self.trio = [self.alex, self.blair, self.casey]

    def test_empty_rotation_returns_none(self):
        self.assertIsNone(
            whose_turn([], "daily", self.ANCHOR, self.ANCHOR)
        )

    def test_single_member_rotation_on_day_zero_and_100_days_later(self):
        self.assertEqual(
            whose_turn([self.alex], "daily", self.ANCHOR, self.ANCHOR),
            self.alex,
        )
        self.assertEqual(
            whose_turn(
                [self.alex],
                "daily",
                self.ANCHOR + timedelta(days=100),
                self.ANCHOR,
            ),
            self.alex,
        )

    def test_reference_date_equals_anchor_returns_first_member(self):
        self.assertEqual(
            whose_turn(self.trio, "daily", self.ANCHOR, self.ANCHOR),
            self.alex,
        )

    def test_daily_three_member_rotation_over_four_days(self):
        expected = [self.alex, self.blair, self.casey, self.alex]
        for offset, member in enumerate(expected):
            self.assertEqual(
                whose_turn(
                    self.trio,
                    "daily",
                    self.ANCHOR + timedelta(days=offset),
                    self.ANCHOR,
                ),
                member,
                msg=f"day {offset}",
            )

    def test_weekly_holds_for_seven_days_then_advances(self):
        for offset in range(7):
            self.assertEqual(
                whose_turn(
                    self.trio,
                    "weekly",
                    self.ANCHOR + timedelta(days=offset),
                    self.ANCHOR,
                ),
                self.alex,
                msg=f"day {offset}",
            )
        self.assertEqual(
            whose_turn(
                self.trio,
                "weekly",
                self.ANCHOR + timedelta(days=7),
                self.ANCHOR,
            ),
            self.blair,
        )

    def test_reference_date_one_day_before_anchor_returns_last_member(self):
        self.assertEqual(
            whose_turn(
                self.trio,
                "daily",
                self.ANCHOR - timedelta(days=1),
                self.ANCHOR,
            ),
            self.casey,
        )

    def test_span_of_several_full_cycles_wraps_correctly(self):
        self.assertEqual(
            whose_turn(
                self.trio,
                "daily",
                self.ANCHOR + timedelta(days=7),
                self.ANCHOR,
            ),
            self.blair,
        )

    def test_unknown_frequency_raises_value_error(self):
        with self.assertRaises(ValueError):
            whose_turn(self.trio, "monthly", self.ANCHOR, self.ANCHOR)


class PeriodKeyTest(TestCase):
    def test_daily_key_is_local_date(self):
        dt = datetime(2026, 9, 10, 14, 30, tzinfo=dt_timezone.utc)
        self.assertEqual(period_key("daily", dt), "2026-09-10")

    def test_weekly_key_is_iso_year_week(self):
        dt = datetime(2026, 9, 10, 14, 30, tzinfo=dt_timezone.utc)
        self.assertEqual(period_key("weekly", dt), "2026-W37")

    def test_weekly_key_zero_pads_week_number(self):
        dt = datetime(2026, 1, 5, 9, 0, tzinfo=dt_timezone.utc)
        self.assertEqual(period_key("weekly", dt), "2026-W02")

    def test_unknown_frequency_raises_value_error(self):
        dt = datetime(2026, 9, 10, tzinfo=dt_timezone.utc)
        with self.assertRaises(ValueError):
            period_key("monthly", dt)


class CompletionModelTest(TestCase):
    def setUp(self):
        self.daily = Chore.objects.create(
            name="Vacuum", frequency=Chore.Frequency.DAILY
        )
        self.weekly = Chore.objects.create(
            name="Mow lawn", frequency=Chore.Frequency.WEEKLY
        )
        self.sam = Member.objects.create(name="Sam")

    def _at(self, *args):
        return datetime(*args, tzinfo=dt_timezone.utc)

    def test_str_is_readable(self):
        completion = Completion.objects.create(
            chore=self.daily,
            member=self.sam,
            completed_at=self._at(2026, 9, 10, 8, 0),
        )
        self.assertEqual(str(completion), "Vacuum by Sam on 2026-09-10")

    def test_save_sets_daily_period_key_as_date(self):
        completion = Completion.objects.create(
            chore=self.daily,
            member=self.sam,
            completed_at=self._at(2026, 9, 10, 8, 0),
        )
        self.assertEqual(completion.period_key, "2026-09-10")

    def test_save_sets_weekly_period_key_as_iso_week(self):
        completion = Completion.objects.create(
            chore=self.weekly,
            member=self.sam,
            completed_at=self._at(2026, 9, 10, 8, 0),
        )
        self.assertEqual(completion.period_key, "2026-W37")

    def test_explicit_period_key_is_not_overwritten(self):
        completion = Completion.objects.create(
            chore=self.daily,
            member=self.sam,
            completed_at=self._at(2026, 9, 10, 8, 0),
            period_key="custom-key",
        )
        self.assertEqual(completion.period_key, "custom-key")

    def test_deleting_member_with_completion_is_protected(self):
        Completion.objects.create(
            chore=self.daily,
            member=self.sam,
            completed_at=self._at(2026, 9, 10, 8, 0),
        )
        with self.assertRaises(ProtectedError):
            self.sam.delete()

    def test_deleting_chore_cascades_to_completions(self):
        Completion.objects.create(
            chore=self.daily,
            member=self.sam,
            completed_at=self._at(2026, 9, 10, 8, 0),
        )
        self.daily.delete()
        self.assertEqual(Completion.objects.count(), 0)


class CompletionQueryHelpersTest(TestCase):
    def setUp(self):
        self.daily = Chore.objects.create(
            name="Vacuum", frequency=Chore.Frequency.DAILY
        )
        self.other = Chore.objects.create(
            name="Dishes", frequency=Chore.Frequency.DAILY
        )
        self.sam = Member.objects.create(name="Sam")

    def _make(self, chore, *args):
        return Completion.objects.create(
            chore=chore,
            member=self.sam,
            completed_at=datetime(*args, tzinfo=dt_timezone.utc),
        )

    def test_recent_returns_completions_newest_first(self):
        first = self._make(self.daily, 2026, 9, 8, 8, 0)
        second = self._make(self.daily, 2026, 9, 9, 8, 0)
        third = self._make(self.daily, 2026, 9, 10, 8, 0)
        self.assertEqual(
            list(Completion.objects.recent()), [third, second, first]
        )

    def test_recent_limit_caps_the_count(self):
        self._make(self.daily, 2026, 9, 8, 8, 0)
        self._make(self.daily, 2026, 9, 9, 8, 0)
        self._make(self.daily, 2026, 9, 10, 8, 0)
        self.assertEqual(Completion.objects.recent(limit=2).count(), 2)

    def test_completed_in_current_period_true_for_reference_period(self):
        self._make(self.daily, 2026, 9, 10, 8, 0)
        reference = datetime(2026, 9, 10, 21, 0, tzinfo=dt_timezone.utc)
        self.assertTrue(
            Completion.objects.completed_in_current_period(self.daily, reference)
        )

    def test_completed_in_current_period_false_for_different_period(self):
        self._make(self.daily, 2026, 9, 10, 8, 0)
        reference = datetime(2026, 9, 11, 8, 0, tzinfo=dt_timezone.utc)
        self.assertFalse(
            Completion.objects.completed_in_current_period(self.daily, reference)
        )

    def test_two_completions_same_period_are_both_kept_and_still_current(self):
        self._make(self.daily, 2026, 9, 10, 8, 0)
        self._make(self.daily, 2026, 9, 10, 20, 0)
        reference = datetime(2026, 9, 10, 22, 0, tzinfo=dt_timezone.utc)
        self.assertEqual(
            Completion.objects.filter(chore=self.daily).count(), 2
        )
        self.assertTrue(
            Completion.objects.completed_in_current_period(self.daily, reference)
        )


class SwapModelTest(TestCase):
    def setUp(self):
        self.chore = Chore.objects.create(
            name="Vacuum", frequency=Chore.Frequency.WEEKLY
        )
        self.sam = Member.objects.create(name="Sam")
        self.alex = Member.objects.create(name="Alex")
        self.jo = Member.objects.create(name="Jo")

    def test_str_is_readable(self):
        swap = Swap.objects.create(
            chore=self.chore,
            period_key="2026-W37",
            from_member=self.sam,
            to_member=self.alex,
        )
        self.assertEqual(str(swap), "Vacuum 2026-W37: Sam -> Alex")

    def test_from_member_equal_to_to_member_raises_integrity_error(self):
        with self.assertRaises(IntegrityError):
            Swap.objects.create(
                chore=self.chore,
                period_key="2026-W37",
                from_member=self.sam,
                to_member=self.sam,
            )

    def test_second_create_for_same_chore_and_period_raises_integrity_error(self):
        Swap.objects.create(
            chore=self.chore,
            period_key="2026-W37",
            from_member=self.sam,
            to_member=self.alex,
        )
        with self.assertRaises(IntegrityError):
            Swap.objects.create(
                chore=self.chore,
                period_key="2026-W37",
                from_member=self.sam,
                to_member=self.jo,
            )

    def test_update_or_create_replaces_the_swap_for_the_same_period(self):
        Swap.objects.create(
            chore=self.chore,
            period_key="2026-W37",
            from_member=self.sam,
            to_member=self.alex,
        )
        obj, created = Swap.objects.update_or_create(
            chore=self.chore,
            period_key="2026-W37",
            defaults={"from_member": self.sam, "to_member": self.jo},
        )
        self.assertFalse(created)
        self.assertEqual(
            Swap.objects.filter(chore=self.chore, period_key="2026-W37").count(), 1
        )
        self.assertEqual(obj.to_member, self.jo)

    def test_same_period_key_under_two_chores_is_allowed(self):
        other = Chore.objects.create(
            name="Mop floors", frequency=Chore.Frequency.WEEKLY
        )
        Swap.objects.create(
            chore=self.chore,
            period_key="2026-W37",
            from_member=self.sam,
            to_member=self.alex,
        )
        Swap.objects.create(
            chore=other,
            period_key="2026-W37",
            from_member=self.sam,
            to_member=self.alex,
        )
        self.assertEqual(Swap.objects.filter(period_key="2026-W37").count(), 2)


class ResponsibleMemberTest(TestCase):
    ANCHOR = date(2026, 1, 5)

    def setUp(self):
        self.chore = Chore.objects.create(
            name="Vacuum", frequency=Chore.Frequency.WEEKLY
        )
        self.sam = Member.objects.create(name="Sam")
        self.alex = Member.objects.create(name="Alex")
        self.jo = Member.objects.create(name="Jo")
        self.kim = Member.objects.create(name="Kim")
        for position, member in enumerate(
            [self.sam, self.alex, self.jo, self.kim]
        ):
            RotationSlot.objects.create(
                chore=self.chore, member=member, position=position
            )
        # Base rotation for a weekly chore anchored on 2026-01-05:
        #   P-1 -> Kim, P -> Sam, P+1 -> Alex
        self.p_minus_1 = self.ANCHOR - timedelta(days=7)
        self.p = self.ANCHOR
        self.p_plus_1 = self.ANCHOR + timedelta(days=7)

    def _key(self, ref):
        return period_key(self.chore.frequency, datetime.combine(ref, time()))

    def test_base_rotation_without_a_swap(self):
        self.assertEqual(
            responsible_member(self.chore, self.p_minus_1, self.ANCHOR), self.kim
        )
        self.assertEqual(
            responsible_member(self.chore, self.p, self.ANCHOR), self.sam
        )
        self.assertEqual(
            responsible_member(self.chore, self.p_plus_1, self.ANCHOR), self.alex
        )

    def test_swap_overrides_only_its_own_period(self):
        Swap.objects.create(
            chore=self.chore,
            period_key=self._key(self.p),
            from_member=self.sam,
            to_member=self.jo,
        )
        self.assertEqual(
            responsible_member(self.chore, self.p, self.ANCHOR), self.jo
        )
        self.assertEqual(
            responsible_member(self.chore, self.p_minus_1, self.ANCHOR), self.kim
        )
        self.assertEqual(
            responsible_member(self.chore, self.p_plus_1, self.ANCHOR), self.alex
        )

    def test_swap_with_stale_from_member_is_ignored(self):
        Swap.objects.create(
            chore=self.chore,
            period_key=self._key(self.p),
            from_member=self.alex,
            to_member=self.jo,
        )
        self.assertEqual(
            responsible_member(self.chore, self.p, self.ANCHOR), self.sam
        )

    def test_empty_rotation_with_a_swap_present_returns_none(self):
        empty = Chore.objects.create(
            name="Dust", frequency=Chore.Frequency.WEEKLY
        )
        Swap.objects.create(
            chore=empty,
            period_key=self._key(self.p),
            from_member=self.sam,
            to_member=self.jo,
        )
        self.assertIsNone(responsible_member(empty, self.p, self.ANCHOR))

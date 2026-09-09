from django.db import models


class Member(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Chore(models.Model):
    class Frequency(models.TextChoices):
        DAILY = "daily"
        WEEKLY = "weekly"

    name = models.CharField(max_length=100, unique=True)
    frequency = models.CharField(max_length=10, choices=Frequency.choices)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["frequency", "name"]

    def __str__(self):
        return self.name

    def rotation_members(self):
        """The chore's rotation as a list of ``Member``s in ascending
        ``position`` order. This is the canonical accessor the whose-turn
        calculation (#5) reads. Returns ``[]`` when the chore has no slots.
        """
        return [slot.member for slot in self.rotation_slots.select_related("member")]


class RotationSlot(models.Model):
    """One member's seat in a chore's fixed rotation.

    The rotation is defined purely by ascending ``position`` order.
    ``position`` values start at 0 and **gaps are allowed** — do not assume
    the values are contiguous (e.g. removing the slot at position 1 leaves
    0, 2, 3 and that is a valid two-plus rotation). Read the order through
    ``Chore.rotation_members()``, never by indexing on ``position``.

    ``member`` uses ``on_delete=PROTECT``: a member who sits in any rotation
    cannot be hard-deleted. Deactivate them instead via ``Member.is_active``.
    """

    chore = models.ForeignKey(
        Chore, on_delete=models.CASCADE, related_name="rotation_slots"
    )
    member = models.ForeignKey(Member, on_delete=models.PROTECT)
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ["chore", "position"]
        constraints = [
            models.UniqueConstraint(
                fields=["chore", "position"], name="unique_position_per_chore"
            ),
            models.UniqueConstraint(
                fields=["chore", "member"], name="unique_member_per_chore"
            ),
        ]

    def __str__(self):
        return f"{self.chore.name} #{self.position}: {self.member.name}"

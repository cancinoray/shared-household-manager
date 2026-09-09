from django.contrib import admin

from .models import Chore, Completion, Member, RotationSlot, Swap


class RotationSlotInline(admin.TabularInline):
    model = RotationSlot
    fields = ("member", "position")
    ordering = ("position",)
    extra = 1


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
    list_display = ("name", "frequency", "is_active")
    list_filter = ("frequency", "is_active")
    search_fields = ("name",)
    inlines = [RotationSlotInline]


@admin.register(Completion)
class CompletionAdmin(admin.ModelAdmin):
    list_display = ("chore", "member", "completed_at", "period_key")
    list_filter = ("chore", "member")
    date_hierarchy = "completed_at"
    list_select_related = ("chore", "member")


@admin.register(Swap)
class SwapAdmin(admin.ModelAdmin):
    list_display = ("chore", "period_key", "from_member", "to_member", "created_at")
    list_filter = ("chore",)
    list_select_related = ("chore", "from_member", "to_member")

from django.contrib import admin

from .models import Chore, Member, RotationSlot


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

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import DeviceSession, User


class DeviceSessionInline(admin.TabularInline):
    model = DeviceSession
    extra = 0
    readonly_fields = ("id", "device_id", "platform", "created_at", "last_seen_at")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("__str__", "is_anonymous_user", "date_joined")
    list_filter = ("is_anonymous_user", "is_staff")
    inlines = [DeviceSessionInline]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("FootIQ", {"fields": ("is_anonymous_user",)}),
    )


@admin.register(DeviceSession)
class DeviceSessionAdmin(admin.ModelAdmin):
    list_display = ("device_id", "user", "platform", "last_seen_at")
    list_filter = ("platform",)
    raw_id_fields = ("user",)

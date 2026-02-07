from django.contrib import admin

from apps.progress.models import (
    CareerPathProgress,
    GridProgress,
    UserDailyCompletion,
    UserStreak,
    WordleProgress,
)


@admin.register(CareerPathProgress)
class CareerPathProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "puzzle", "status", "attempts_used", "completed_at")
    list_filter = ("status",)
    raw_id_fields = ("user", "puzzle")


@admin.register(GridProgress)
class GridProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "puzzle", "status", "total_guesses_used", "cells_filled")
    list_filter = ("status",)
    raw_id_fields = ("user", "puzzle")


@admin.register(WordleProgress)
class WordleProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "puzzle", "status", "attempts_used", "completed_at")
    list_filter = ("status",)
    raw_id_fields = ("user", "puzzle")


@admin.register(UserStreak)
class UserStreakAdmin(admin.ModelAdmin):
    list_display = ("user", "current_streak", "longest_streak", "last_completed_date")
    raw_id_fields = ("user",)


@admin.register(UserDailyCompletion)
class UserDailyCompletionAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "all_completed", "is_perfect")
    list_filter = ("all_completed", "is_perfect")
    raw_id_fields = ("user",)

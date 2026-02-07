from django.contrib import admin, messages
from django.utils import timezone

import nested_admin

from apps.games.models import (
    CareerPathHint,
    CareerPathPuzzle,
    DailySet,
    GridCell,
    GridCellAcceptedPlayer,
    GridLabel,
    GridPuzzle,
    WordlePuzzle,
)


# --- Career Path nested inlines ---

class CareerPathHintInline(nested_admin.NestedTabularInline):
    model = CareerPathHint
    extra = 1
    fields = ("order_index", "hint_type", "hint_data")


class CareerPathPuzzleInline(nested_admin.NestedStackedInline):
    model = CareerPathPuzzle
    extra = 0
    max_num = 1
    autocomplete_fields = ("answer_player",)
    inlines = [CareerPathHintInline]


# --- Grid nested inlines ---

class GridCellAcceptedPlayerInline(nested_admin.NestedTabularInline):
    model = GridCellAcceptedPlayer
    extra = 1
    autocomplete_fields = ("player",)


class GridCellInline(nested_admin.NestedStackedInline):
    model = GridCell
    extra = 0
    fields = ("row_index", "col_index")
    inlines = [GridCellAcceptedPlayerInline]


class GridLabelInline(nested_admin.NestedTabularInline):
    model = GridLabel
    extra = 0
    fields = ("axis", "index", "label_type", "display_text", "label_data")


class GridPuzzleInline(nested_admin.NestedStackedInline):
    model = GridPuzzle
    extra = 0
    max_num = 1
    inlines = [GridLabelInline, GridCellInline]


# --- Wordle inline ---

class WordlePuzzleInline(nested_admin.NestedStackedInline):
    model = WordlePuzzle
    extra = 0
    max_num = 1
    autocomplete_fields = ("answer_player",)
    fields = ("answer_player", "answer_word", "max_attempts", "allowed_chars")


# --- DailySet admin ---

@admin.register(DailySet)
class DailySetAdmin(nested_admin.NestedModelAdmin):
    list_display = ("date", "status", "has_career_path", "has_grid", "has_wordle")
    list_filter = ("status",)
    readonly_fields = ("created_at", "updated_at", "published_at")
    inlines = [CareerPathPuzzleInline, GridPuzzleInline, WordlePuzzleInline]
    actions = ["publish_sets", "unpublish_sets"]

    @admin.display(boolean=True, description="Career Path")
    def has_career_path(self, obj):
        return hasattr(obj, "career_path_puzzle")

    @admin.display(boolean=True, description="Grid")
    def has_grid(self, obj):
        return hasattr(obj, "grid_puzzle")

    @admin.display(boolean=True, description="Wordle")
    def has_wordle(self, obj):
        return hasattr(obj, "wordle_puzzle")

    @admin.action(description="Publish selected sets")
    def publish_sets(self, request, queryset):
        published = 0
        for daily_set in queryset:
            try:
                daily_set.status = DailySet.Status.PUBLISHED
                daily_set.full_clean()
                daily_set.published_at = timezone.now()
                daily_set.save()
                published += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Cannot publish {daily_set.date}: {e}",
                    messages.ERROR,
                )
        if published:
            self.message_user(
                request, f"{published} set(s) published.", messages.SUCCESS
            )

    @admin.action(description="Unpublish selected sets")
    def unpublish_sets(self, request, queryset):
        queryset.update(status=DailySet.Status.DRAFT, published_at=None)
        self.message_user(
            request, f"{queryset.count()} set(s) unpublished.", messages.SUCCESS
        )

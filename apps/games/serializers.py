from rest_framework import serializers

from apps.games.models import (
    CareerPathHint,
    CareerPathPuzzle,
    DailySet,
    GridCell,
    GridLabel,
    GridPuzzle,
    WordlePuzzle,
)
from apps.players.serializers import PlayerSearchSerializer


# --- Career Path ---

class CareerPathHintSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerPathHint
        fields = ["order_index", "hint_type", "hint_data"]


class CareerPathPuzzleSerializer(serializers.ModelSerializer):
    hints = serializers.SerializerMethodField()
    answer_player = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = CareerPathPuzzle
        fields = ["id", "max_attempts", "hints", "answer_player", "progress"]

    def get_hints(self, obj):
        """Only return hints up to the number revealed by user progress."""
        user = self.context.get("user")
        progress = self._get_progress(obj, user)
        hints_revealed = progress.hints_revealed if progress else 1
        hints = obj.hints.filter(order_index__lt=hints_revealed)
        return CareerPathHintSerializer(hints, many=True).data

    def get_answer_player(self, obj):
        """Only show answer if game is completed."""
        user = self.context.get("user")
        progress = self._get_progress(obj, user)
        if progress and progress.status != "in_progress":
            return PlayerSearchSerializer(obj.answer_player).data
        return None

    def get_progress(self, obj):
        user = self.context.get("user")
        progress = self._get_progress(obj, user)
        if not progress:
            return None
        return {
            "status": progress.status,
            "guesses": progress.guesses,
            "attempts_used": progress.attempts_used,
            "hints_revealed": progress.hints_revealed,
            "completed_at": progress.completed_at,
        }

    def _get_progress(self, obj, user):
        if not user or not user.is_authenticated:
            return None
        if not hasattr(obj, "_prefetched_progress"):
            from apps.progress.models import CareerPathProgress
            try:
                return CareerPathProgress.objects.get(user=user, puzzle=obj)
            except CareerPathProgress.DoesNotExist:
                return None
        return obj._prefetched_progress


# --- Grid ---

class GridLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = GridLabel
        fields = ["axis", "index", "label_type", "display_text", "label_data"]


class GridCellSerializer(serializers.ModelSerializer):
    class Meta:
        model = GridCell
        fields = ["row_index", "col_index"]


class GridPuzzleSerializer(serializers.ModelSerializer):
    labels = GridLabelSerializer(many=True, read_only=True)
    cells = GridCellSerializer(many=True, read_only=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = GridPuzzle
        fields = [
            "id",
            "max_total_guesses",
            "enforce_unique_players",
            "labels",
            "cells",
            "progress",
        ]

    def get_progress(self, obj):
        user = self.context.get("user")
        if not user or not user.is_authenticated:
            return None
        from apps.progress.models import GridProgress
        try:
            progress = GridProgress.objects.get(user=user, puzzle=obj)
        except GridProgress.DoesNotExist:
            return None
        return {
            "status": progress.status,
            "total_guesses_used": progress.total_guesses_used,
            "cells_filled": progress.cells_filled,
            "board_state": progress.board_state,
            "guesses": progress.guesses,
            "used_player_ids": progress.used_player_ids,
        }


# --- Wordle ---

class WordlePuzzleSerializer(serializers.ModelSerializer):
    answer_player = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = WordlePuzzle
        fields = [
            "id",
            "word_length",
            "max_attempts",
            "allowed_chars",
            "answer_player",
            "progress",
        ]

    def get_answer_player(self, obj):
        user = self.context.get("user")
        progress = self._get_progress(obj, user)
        if progress and progress.status != "in_progress":
            return PlayerSearchSerializer(obj.answer_player).data
        return None

    def get_progress(self, obj):
        user = self.context.get("user")
        progress = self._get_progress(obj, user)
        if not progress:
            return None
        return {
            "status": progress.status,
            "guesses": progress.guesses,
            "attempts_used": progress.attempts_used,
            "completed_at": progress.completed_at,
        }

    def _get_progress(self, obj, user):
        if not user or not user.is_authenticated:
            return None
        from apps.progress.models import WordleProgress
        try:
            return WordleProgress.objects.get(user=user, puzzle=obj)
        except WordleProgress.DoesNotExist:
            return None


# --- DailySet ---

class DailySetSerializer(serializers.ModelSerializer):
    career_path = serializers.SerializerMethodField()
    grid = serializers.SerializerMethodField()
    wordle = serializers.SerializerMethodField()

    class Meta:
        model = DailySet
        fields = ["date", "status", "career_path", "grid", "wordle"]

    def get_career_path(self, obj):
        if not hasattr(obj, "career_path_puzzle"):
            return None
        return CareerPathPuzzleSerializer(
            obj.career_path_puzzle, context=self.context
        ).data

    def get_grid(self, obj):
        if not hasattr(obj, "grid_puzzle"):
            return None
        return GridPuzzleSerializer(
            obj.grid_puzzle, context=self.context
        ).data

    def get_wordle(self, obj):
        if not hasattr(obj, "wordle_puzzle"):
            return None
        return WordlePuzzleSerializer(
            obj.wordle_puzzle, context=self.context
        ).data

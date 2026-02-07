from django.conf import settings
from django.db import models

from apps.games.models import CareerPathPuzzle, GridPuzzle, WordlePuzzle


class CareerPathProgress(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="career_path_progress"
    )
    puzzle = models.ForeignKey(
        CareerPathPuzzle, on_delete=models.CASCADE, related_name="progress"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PROGRESS
    )
    guesses = models.JSONField(default=list, help_text="List of {guess_text, player_id, correct}")
    attempts_used = models.PositiveIntegerField(default=0)
    hints_revealed = models.PositiveIntegerField(default=1, help_text="Hint 0 is shown initially")
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "progress_career_path"
        unique_together = [("user", "puzzle")]

    def __str__(self):
        return f"{self.user} - Career Path {self.puzzle_id} ({self.status})"


class GridProgress(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        EXHAUSTED = "exhausted", "Exhausted"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="grid_progress"
    )
    puzzle = models.ForeignKey(
        GridPuzzle, on_delete=models.CASCADE, related_name="progress"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PROGRESS
    )
    total_guesses_used = models.PositiveIntegerField(default=0)
    cells_filled = models.PositiveIntegerField(default=0)
    board_state = models.JSONField(
        default=dict, help_text='{"0_0": {"player_id": ..., "player_name": ...}, ...}'
    )
    guesses = models.JSONField(default=list, help_text="Full guess log")
    used_player_ids = models.JSONField(
        default=list, help_text="Player IDs used (for uniqueness enforcement)"
    )

    class Meta:
        db_table = "progress_grid"
        unique_together = [("user", "puzzle")]

    def __str__(self):
        return f"{self.user} - Grid {self.puzzle_id} ({self.status})"


class WordleProgress(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wordle_progress"
    )
    puzzle = models.ForeignKey(
        WordlePuzzle, on_delete=models.CASCADE, related_name="progress"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PROGRESS
    )
    guesses = models.JSONField(
        default=list, help_text="List of {word, feedback: [{letter, status}]}"
    )
    attempts_used = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "progress_wordle"
        unique_together = [("user", "puzzle")]

    def __str__(self):
        return f"{self.user} - Wordle {self.puzzle_id} ({self.status})"


class UserStreak(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="streak"
    )
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_completed_date = models.DateField(null=True, blank=True)
    total_days_played = models.PositiveIntegerField(default=0)
    total_perfect_days = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "progress_user_streak"

    def __str__(self):
        return f"{self.user} streak: {self.current_streak}"


class UserDailyCompletion(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_completions"
    )
    date = models.DateField()
    career_path_result = models.CharField(max_length=20, blank=True, default="")
    grid_result = models.CharField(max_length=20, blank=True, default="")
    wordle_result = models.CharField(max_length=20, blank=True, default="")
    all_completed = models.BooleanField(default=False)
    is_perfect = models.BooleanField(default=False)

    class Meta:
        db_table = "progress_user_daily_completion"
        unique_together = [("user", "date")]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.user} - {self.date}"

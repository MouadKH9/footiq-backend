from django.core.exceptions import ValidationError
from django.db import models

from apps.players.models import Player


class DailySet(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    date = models.DateField(unique=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, default="", help_text="Admin-only notes")

    class Meta:
        db_table = "games_daily_set"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.date} ({self.status})"

    def clean(self):
        if self.status == self.Status.PUBLISHED:
            errors = []
            if not hasattr(self, "career_path_puzzle"):
                errors.append("Missing Career Path puzzle.")
            if not hasattr(self, "grid_puzzle"):
                errors.append("Missing Grid puzzle.")
            if not hasattr(self, "wordle_puzzle"):
                errors.append("Missing Wordle puzzle.")
            if errors:
                raise ValidationError(
                    {"status": "Cannot publish: " + " ".join(errors)}
                )


class CareerPathPuzzle(models.Model):
    daily_set = models.OneToOneField(
        DailySet, on_delete=models.CASCADE, related_name="career_path_puzzle"
    )
    answer_player = models.ForeignKey(
        Player, on_delete=models.PROTECT, related_name="+"
    )
    max_attempts = models.PositiveIntegerField(default=6)

    class Meta:
        db_table = "games_career_path_puzzle"

    def __str__(self):
        return f"Career Path: {self.answer_player.name} ({self.daily_set.date})"

    def clean(self):
        if self.pk and self.hints.count() == 0:
            raise ValidationError("Career Path puzzle must have at least one hint.")


class CareerPathHint(models.Model):
    class HintType(models.TextChoices):
        CLUB_BADGE = "club_badge", "Club Badge"
        NATIONALITY = "nationality", "Nationality"
        POSITION = "position", "Position"
        AGE_RANGE = "age_range", "Age Range"
        LEAGUE = "league", "League"
        TROPHY = "trophy", "Trophy"
        TEXT = "text", "Text"
        IMAGE = "image", "Image"

    puzzle = models.ForeignKey(
        CareerPathPuzzle, on_delete=models.CASCADE, related_name="hints"
    )
    order_index = models.PositiveIntegerField(
        help_text="0-based, hint 0 is shown initially"
    )
    hint_type = models.CharField(max_length=20, choices=HintType.choices)
    hint_data = models.JSONField(
        help_text="Structured payload per hint type"
    )

    class Meta:
        db_table = "games_career_path_hint"
        unique_together = [("puzzle", "order_index")]
        ordering = ["order_index"]

    def __str__(self):
        return f"Hint {self.order_index}: {self.hint_type}"


class GridPuzzle(models.Model):
    daily_set = models.OneToOneField(
        DailySet, on_delete=models.CASCADE, related_name="grid_puzzle"
    )
    max_total_guesses = models.PositiveIntegerField(default=15)
    enforce_unique_players = models.BooleanField(default=True)

    class Meta:
        db_table = "games_grid_puzzle"

    def __str__(self):
        return f"Grid ({self.daily_set.date})"

    def clean(self):
        if self.pk:
            cell_count = self.cells.count()
            if cell_count < 9:
                raise ValidationError(
                    f"Grid puzzle should have 9 cells, found {cell_count}."
                )
            empty_cells = self.cells.filter(accepted_players__isnull=True).count()
            if empty_cells > 0:
                raise ValidationError(
                    f"{empty_cells} cell(s) have no accepted players."
                )


class GridLabel(models.Model):
    class Axis(models.TextChoices):
        ROW = "row", "Row"
        COL = "col", "Column"

    class LabelType(models.TextChoices):
        CLUB = "club", "Club"
        NATIONALITY = "nationality", "Nationality"
        POSITION = "position", "Position"
        LEAGUE = "league", "League"
        CUSTOM = "custom", "Custom"

    puzzle = models.ForeignKey(
        GridPuzzle, on_delete=models.CASCADE, related_name="labels"
    )
    axis = models.CharField(max_length=3, choices=Axis.choices)
    index = models.PositiveIntegerField(help_text="0-2")
    label_type = models.CharField(max_length=20, choices=LabelType.choices)
    display_text = models.CharField(max_length=100)
    label_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "games_grid_label"
        unique_together = [("puzzle", "axis", "index")]
        ordering = ["axis", "index"]

    def __str__(self):
        return f"{self.axis}[{self.index}]: {self.display_text}"


class GridCell(models.Model):
    puzzle = models.ForeignKey(
        GridPuzzle, on_delete=models.CASCADE, related_name="cells"
    )
    row_index = models.PositiveIntegerField(help_text="0-2")
    col_index = models.PositiveIntegerField(help_text="0-2")
    accepted_players = models.ManyToManyField(
        Player,
        through="GridCellAcceptedPlayer",
        related_name="+",
        blank=True,
    )

    class Meta:
        db_table = "games_grid_cell"
        unique_together = [("puzzle", "row_index", "col_index")]
        ordering = ["row_index", "col_index"]

    def __str__(self):
        return f"Cell ({self.row_index}, {self.col_index})"


class GridCellAcceptedPlayer(models.Model):
    cell = models.ForeignKey(GridCell, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)

    class Meta:
        db_table = "games_grid_cell_accepted_player"
        unique_together = [("cell", "player")]

    def __str__(self):
        return f"{self.player.name} in ({self.cell.row_index}, {self.cell.col_index})"


class WordlePuzzle(models.Model):
    daily_set = models.OneToOneField(
        DailySet, on_delete=models.CASCADE, related_name="wordle_puzzle"
    )
    answer_player = models.ForeignKey(
        Player, on_delete=models.PROTECT, related_name="+"
    )
    answer_word = models.CharField(
        max_length=30, help_text="Uppercase surname used as the Wordle word"
    )
    word_length = models.PositiveIntegerField(
        editable=False, help_text="Auto-computed from answer_word"
    )
    max_attempts = models.PositiveIntegerField(default=6)
    allowed_chars = models.CharField(
        max_length=50, default="ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    )

    class Meta:
        db_table = "games_wordle_puzzle"

    def __str__(self):
        return f"Wordle: {self.answer_word} ({self.daily_set.date})"

    def clean(self):
        if self.answer_word:
            self.answer_word = self.answer_word.upper()
            invalid = set(self.answer_word) - set(self.allowed_chars)
            if invalid:
                raise ValidationError(
                    {
                        "answer_word": f"Invalid characters: {', '.join(sorted(invalid))}"
                    }
                )

    def save(self, **kwargs):
        if self.answer_word:
            self.answer_word = self.answer_word.upper()
            self.word_length = len(self.answer_word)
        super().save(**kwargs)

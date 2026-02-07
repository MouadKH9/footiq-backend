"""
Share text generation for game results.
"""

from datetime import date

from apps.games.models import CareerPathPuzzle, DailySet, GridPuzzle, WordlePuzzle
from apps.progress.models import (
    CareerPathProgress,
    GridProgress,
    WordleProgress,
)


def generate_career_path_share(user, puzzle: CareerPathPuzzle) -> str | None:
    try:
        progress = CareerPathProgress.objects.get(user=user, puzzle=puzzle)
    except CareerPathProgress.DoesNotExist:
        return None
    if progress.status == CareerPathProgress.Status.IN_PROGRESS:
        return None

    puzzle_date = puzzle.daily_set.date
    won = progress.status == CareerPathProgress.Status.WON
    emoji = "\u2705" if won else "\u274c"

    lines = [
        f"FootIQ Career Path {puzzle_date.isoformat()}",
        f"{emoji} {'Solved' if won else 'Failed'} in {progress.attempts_used}/{puzzle.max_attempts} attempts",
        f"Hints used: {progress.hints_revealed}",
    ]
    return "\n".join(lines)


def generate_grid_share(user, puzzle: GridPuzzle) -> str | None:
    try:
        progress = GridProgress.objects.get(user=user, puzzle=puzzle)
    except GridProgress.DoesNotExist:
        return None
    if progress.status == GridProgress.Status.IN_PROGRESS:
        return None

    puzzle_date = puzzle.daily_set.date

    # Build 3x3 emoji grid
    grid_emojis = []
    for row in range(3):
        row_emojis = []
        for col in range(3):
            key = f"{row}_{col}"
            if key in progress.board_state:
                row_emojis.append("\U0001f7e9")  # green square
            else:
                row_emojis.append("\u2b1c")  # white square
        grid_emojis.append("".join(row_emojis))

    lines = [
        f"FootIQ Grid {puzzle_date.isoformat()}",
        f"{progress.cells_filled}/9 | {progress.total_guesses_used} guesses",
        "",
    ]
    lines.extend(grid_emojis)
    return "\n".join(lines)


def generate_wordle_share(user, puzzle: WordlePuzzle) -> str | None:
    try:
        progress = WordleProgress.objects.get(user=user, puzzle=puzzle)
    except WordleProgress.DoesNotExist:
        return None
    if progress.status == WordleProgress.Status.IN_PROGRESS:
        return None

    puzzle_date = puzzle.daily_set.date
    won = progress.status == WordleProgress.Status.WON
    score = str(progress.attempts_used) if won else "X"

    # Build emoji grid from feedback
    emoji_rows = []
    for guess in progress.guesses:
        row = ""
        for fb in guess["feedback"]:
            if fb["status"] == "correct":
                row += "\U0001f7e9"  # green
            elif fb["status"] == "present":
                row += "\U0001f7e8"  # yellow
            else:
                row += "\u2b1b"  # black
        emoji_rows.append(row)

    lines = [
        f"FootIQ Wordle {puzzle_date.isoformat()} {score}/{puzzle.max_attempts}",
        "",
    ]
    lines.extend(emoji_rows)
    return "\n".join(lines)


def generate_daily_share(user, puzzle_date: date) -> str | None:
    try:
        daily_set = DailySet.objects.get(date=puzzle_date)
    except DailySet.DoesNotExist:
        return None

    parts = [f"FootIQ {puzzle_date.isoformat()}", ""]

    has_any = False

    if hasattr(daily_set, "career_path_puzzle"):
        text = generate_career_path_share(user, daily_set.career_path_puzzle)
        if text:
            has_any = True
            # Extract just the result line (skip header)
            result_lines = text.split("\n")[1:]
            parts.append("Career Path: " + result_lines[0].lstrip("\u2705\u274c "))

    if hasattr(daily_set, "grid_puzzle"):
        text = generate_grid_share(user, daily_set.grid_puzzle)
        if text:
            has_any = True
            result_line = text.split("\n")[1]
            parts.append("Grid: " + result_line)

    if hasattr(daily_set, "wordle_puzzle"):
        text = generate_wordle_share(user, daily_set.wordle_puzzle)
        if text:
            has_any = True
            header = text.split("\n")[0]
            score_part = header.split(" ")[-1]
            parts.append(f"Wordle: {score_part}")

    if not has_any:
        return None

    return "\n".join(parts)

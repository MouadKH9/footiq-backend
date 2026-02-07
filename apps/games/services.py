"""
Game logic services for guess processing.
Business logic lives here, not in views or serializers.
"""

from datetime import date

from django.db import transaction
from django.utils import timezone

from apps.games.models import CareerPathPuzzle, GridCell, GridPuzzle, WordlePuzzle
from apps.players.models import Player
from apps.players.services import resolve_guess
from apps.progress.models import (
    CareerPathProgress,
    GridProgress,
    UserDailyCompletion,
    UserStreak,
    WordleProgress,
)


# --- Career Path ---

def process_career_path_guess(user, puzzle: CareerPathPuzzle, guess_text: str = None, player_id: int = None):
    """
    Process a Career Path guess. Returns dict with result data.
    """
    progress, _ = CareerPathProgress.objects.get_or_create(
        user=user, puzzle=puzzle
    )

    if progress.status != CareerPathProgress.Status.IN_PROGRESS:
        return {"error": "Game already completed.", "status": progress.status}

    # Resolve the guess
    if player_id:
        try:
            guessed_player = Player.objects.get(id=player_id)
        except Player.DoesNotExist:
            return {"error": "Player not found."}
        result_status = "exact"
    elif guess_text:
        result = resolve_guess(guess_text)
        if result.status == "ambiguous":
            return {
                "ambiguous_match": True,
                "candidates": [
                    {"id": p.id, "name": p.name, "image_url": p.image_url}
                    for p in result.candidates
                ],
            }
        if result.status == "no_match":
            return {"no_match": True}
        guessed_player = result.player
        result_status = result.status
    else:
        return {"error": "Provide guess_text or player_id."}

    correct = guessed_player.id == puzzle.answer_player_id

    # Record guess
    progress.guesses.append({
        "guess_text": guess_text or guessed_player.name,
        "player_id": guessed_player.id,
        "correct": correct,
    })
    progress.attempts_used += 1

    if correct:
        progress.status = CareerPathProgress.Status.WON
        progress.completed_at = timezone.now()
    elif progress.attempts_used >= puzzle.max_attempts:
        progress.status = CareerPathProgress.Status.LOST
        progress.completed_at = timezone.now()
    else:
        # Reveal next hint
        total_hints = puzzle.hints.count()
        if progress.hints_revealed < total_hints:
            progress.hints_revealed += 1

    progress.save()

    # Update daily completion if game ended
    if progress.status != CareerPathProgress.Status.IN_PROGRESS:
        _update_daily_completion(user, puzzle.daily_set.date, "career_path", progress.status)

    return {
        "correct": correct,
        "status": progress.status,
        "attempts_used": progress.attempts_used,
        "hints_revealed": progress.hints_revealed,
        "guessed_player": {
            "id": guessed_player.id,
            "name": guessed_player.name,
            "image_url": guessed_player.image_url,
        },
        "answer_player": (
            {"id": puzzle.answer_player.id, "name": puzzle.answer_player.name}
            if progress.status != CareerPathProgress.Status.IN_PROGRESS
            else None
        ),
    }


# --- Grid ---

def process_grid_guess(user, puzzle: GridPuzzle, row: int, col: int, guess_text: str = None, player_id: int = None):
    """Process a Grid guess for a specific cell."""
    progress, _ = GridProgress.objects.get_or_create(user=user, puzzle=puzzle)

    if progress.status != GridProgress.Status.IN_PROGRESS:
        return {"error": "Game already completed.", "status": progress.status}

    cell_key = f"{row}_{col}"
    if cell_key in progress.board_state:
        return {"error": "Cell already filled."}

    if progress.total_guesses_used >= puzzle.max_total_guesses:
        return {"error": "No guesses remaining."}

    # Resolve the guess
    if player_id:
        try:
            guessed_player = Player.objects.get(id=player_id)
        except Player.DoesNotExist:
            return {"error": "Player not found."}
    elif guess_text:
        result = resolve_guess(guess_text)
        if result.status == "ambiguous":
            return {
                "ambiguous_match": True,
                "candidates": [
                    {"id": p.id, "name": p.name, "image_url": p.image_url}
                    for p in result.candidates
                ],
            }
        if result.status == "no_match":
            return {"no_match": True}
        guessed_player = result.player
    else:
        return {"error": "Provide guess_text or player_id."}

    # Check uniqueness
    if puzzle.enforce_unique_players and guessed_player.id in progress.used_player_ids:
        return {"error": "Player already used in another cell."}

    # Check if player is accepted in this cell
    try:
        cell = GridCell.objects.get(puzzle=puzzle, row_index=row, col_index=col)
    except GridCell.DoesNotExist:
        return {"error": "Invalid cell."}

    accepted = cell.accepted_players.filter(id=guessed_player.id).exists()

    # Record guess
    progress.guesses.append({
        "row": row,
        "col": col,
        "player_id": guessed_player.id,
        "player_name": guessed_player.name,
        "accepted": accepted,
    })
    progress.total_guesses_used += 1

    if accepted:
        progress.board_state[cell_key] = {
            "player_id": guessed_player.id,
            "player_name": guessed_player.name,
        }
        progress.cells_filled += 1
        progress.used_player_ids.append(guessed_player.id)

    # Check completion
    if progress.cells_filled >= 9:
        progress.status = GridProgress.Status.COMPLETED
    elif progress.total_guesses_used >= puzzle.max_total_guesses:
        progress.status = GridProgress.Status.EXHAUSTED

    progress.save()

    if progress.status != GridProgress.Status.IN_PROGRESS:
        _update_daily_completion(user, puzzle.daily_set.date, "grid", progress.status)

    return {
        "accepted": accepted,
        "status": progress.status,
        "total_guesses_used": progress.total_guesses_used,
        "cells_filled": progress.cells_filled,
        "board_state": progress.board_state,
        "guessed_player": {
            "id": guessed_player.id,
            "name": guessed_player.name,
            "image_url": guessed_player.image_url,
        },
    }


# --- Wordle ---

def compute_wordle_feedback(guess_word: str, answer_word: str) -> list[dict]:
    """
    Standard Wordle feedback with correct repeated-letter handling.
    Two-pass: greens first, then yellows.
    Returns list of {letter, status} where status is "correct", "present", or "absent".
    """
    guess_word = guess_word.upper()
    answer_word = answer_word.upper()
    length = len(answer_word)

    feedback = [{"letter": guess_word[i], "status": "absent"} for i in range(length)]
    answer_remaining = list(answer_word)

    # Pass 1: Mark greens (correct position)
    for i in range(length):
        if guess_word[i] == answer_word[i]:
            feedback[i]["status"] = "correct"
            answer_remaining[i] = None

    # Pass 2: Mark yellows (correct letter, wrong position)
    for i in range(length):
        if feedback[i]["status"] == "correct":
            continue
        if guess_word[i] in answer_remaining:
            feedback[i]["status"] = "present"
            answer_remaining[answer_remaining.index(guess_word[i])] = None

    return feedback


def process_wordle_guess(user, puzzle: WordlePuzzle, word: str):
    """Process a Wordle guess."""
    progress, _ = WordleProgress.objects.get_or_create(user=user, puzzle=puzzle)

    if progress.status != WordleProgress.Status.IN_PROGRESS:
        return {"error": "Game already completed.", "status": progress.status}

    word = word.upper()

    if len(word) != puzzle.word_length:
        return {"error": f"Word must be {puzzle.word_length} letters."}

    invalid_chars = set(word) - set(puzzle.allowed_chars)
    if invalid_chars:
        return {"error": f"Invalid characters: {', '.join(sorted(invalid_chars))}"}

    feedback = compute_wordle_feedback(word, puzzle.answer_word)
    correct = word == puzzle.answer_word

    progress.guesses.append({"word": word, "feedback": feedback})
    progress.attempts_used += 1

    if correct:
        progress.status = WordleProgress.Status.WON
        progress.completed_at = timezone.now()
    elif progress.attempts_used >= puzzle.max_attempts:
        progress.status = WordleProgress.Status.LOST
        progress.completed_at = timezone.now()

    progress.save()

    if progress.status != WordleProgress.Status.IN_PROGRESS:
        _update_daily_completion(user, puzzle.daily_set.date, "wordle", progress.status)

    return {
        "correct": correct,
        "feedback": feedback,
        "status": progress.status,
        "attempts_used": progress.attempts_used,
        "answer_player": (
            {"id": puzzle.answer_player.id, "name": puzzle.answer_player.name, "answer_word": puzzle.answer_word}
            if progress.status != WordleProgress.Status.IN_PROGRESS
            else None
        ),
    }


# --- Daily Completion ---

def _update_daily_completion(user, puzzle_date: date, game_type: str, result: str):
    """Update or create daily completion record and recalculate streak."""
    completion, _ = UserDailyCompletion.objects.get_or_create(
        user=user, date=puzzle_date
    )

    setattr(completion, f"{game_type}_result", result)

    # Check if all 3 games are completed
    results = {
        "career_path": completion.career_path_result,
        "grid": completion.grid_result,
        "wordle": completion.wordle_result,
    }
    results[game_type] = result

    all_done = all(r != "" for r in results.values())
    completion.all_completed = all_done

    # Perfect = won all 3
    perfect_results = {"won", "completed"}  # Grid uses "completed"
    completion.is_perfect = all_done and all(
        r in perfect_results for r in results.values()
    )

    completion.save()

    if all_done:
        _update_streak(user, puzzle_date)


def _update_streak(user, puzzle_date: date):
    """Update user streak after completing all games for a date."""
    from datetime import timedelta

    streak, _ = UserStreak.objects.get_or_create(user=user)
    streak.total_days_played = UserDailyCompletion.objects.filter(
        user=user, all_completed=True
    ).count()
    streak.total_perfect_days = UserDailyCompletion.objects.filter(
        user=user, is_perfect=True
    ).count()
    streak.last_completed_date = puzzle_date

    # Calculate current streak
    current = 1
    check_date = puzzle_date - timedelta(days=1)
    while UserDailyCompletion.objects.filter(
        user=user, date=check_date, all_completed=True
    ).exists():
        current += 1
        check_date -= timedelta(days=1)

    streak.current_streak = current
    streak.longest_streak = max(streak.longest_streak, current)
    streak.save()

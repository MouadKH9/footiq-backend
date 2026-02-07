"""
Stats calculation services.
"""

from apps.progress.models import (
    CareerPathProgress,
    GridProgress,
    UserDailyCompletion,
    UserStreak,
    WordleProgress,
)


def get_user_stats(user) -> dict:
    """Get comprehensive stats for a user."""
    streak, _ = UserStreak.objects.get_or_create(user=user)

    # Career Path stats
    cp_total = CareerPathProgress.objects.filter(user=user).exclude(
        status=CareerPathProgress.Status.IN_PROGRESS
    ).count()
    cp_wins = CareerPathProgress.objects.filter(
        user=user, status=CareerPathProgress.Status.WON
    ).count()

    # Grid stats
    grid_total = GridProgress.objects.filter(user=user).exclude(
        status=GridProgress.Status.IN_PROGRESS
    ).count()
    grid_completed = GridProgress.objects.filter(
        user=user, status=GridProgress.Status.COMPLETED
    ).count()

    # Wordle stats
    wordle_total = WordleProgress.objects.filter(user=user).exclude(
        status=WordleProgress.Status.IN_PROGRESS
    ).count()
    wordle_wins = WordleProgress.objects.filter(
        user=user, status=WordleProgress.Status.WON
    ).count()

    return {
        "streak": {
            "current": streak.current_streak,
            "longest": streak.longest_streak,
            "last_completed_date": streak.last_completed_date,
            "total_days_played": streak.total_days_played,
            "total_perfect_days": streak.total_perfect_days,
        },
        "career_path": {
            "played": cp_total,
            "won": cp_wins,
            "win_rate": round(cp_wins / cp_total * 100, 1) if cp_total else 0,
        },
        "grid": {
            "played": grid_total,
            "completed": grid_completed,
            "completion_rate": round(grid_completed / grid_total * 100, 1) if grid_total else 0,
        },
        "wordle": {
            "played": wordle_total,
            "won": wordle_wins,
            "win_rate": round(wordle_wins / wordle_total * 100, 1) if wordle_total else 0,
        },
    }

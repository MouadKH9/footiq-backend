from django.db import transaction

from apps.progress.models import (
    CareerPathProgress,
    GridProgress,
    UserDailyCompletion,
    UserStreak,
    WordleProgress,
)


def merge_anonymous_into_email_user(anonymous_user, email_user):
    """
    Merge progress from an anonymous user into an email user's account.
    For dates without conflicts, reassign progress rows.
    Then recalculate streaks and delete the orphan anonymous user.
    """
    with transaction.atomic():
        existing_dates = set(
            UserDailyCompletion.objects.filter(user=email_user).values_list(
                "date", flat=True
            )
        )

        # Reassign CareerPathProgress
        for progress in CareerPathProgress.objects.filter(user=anonymous_user):
            puzzle_date = progress.puzzle.daily_set.date
            if puzzle_date not in existing_dates:
                progress.user = email_user
                progress.save(update_fields=["user"])

        # Reassign GridProgress
        for progress in GridProgress.objects.filter(user=anonymous_user):
            puzzle_date = progress.puzzle.daily_set.date
            if puzzle_date not in existing_dates:
                progress.user = email_user
                progress.save(update_fields=["user"])

        # Reassign WordleProgress
        for progress in WordleProgress.objects.filter(user=anonymous_user):
            puzzle_date = progress.puzzle.daily_set.date
            if puzzle_date not in existing_dates:
                progress.user = email_user
                progress.save(update_fields=["user"])

        # Reassign daily completions for non-conflicting dates
        for completion in UserDailyCompletion.objects.filter(user=anonymous_user):
            if completion.date not in existing_dates:
                completion.user = email_user
                completion.save(update_fields=["user"])

        # Recalculate streaks for the email user
        _recalculate_streak(email_user)

        # Delete the orphan anonymous user (cascades devices, remaining progress)
        anonymous_user.delete()


def _recalculate_streak(user):
    """Rebuild UserStreak from UserDailyCompletion history."""
    from datetime import date, timedelta

    completions = (
        UserDailyCompletion.objects.filter(user=user, all_completed=True)
        .order_by("date")
        .values_list("date", flat=True)
    )
    dates = list(completions)

    streak, _ = UserStreak.objects.get_or_create(user=user)
    streak.total_days_played = UserDailyCompletion.objects.filter(user=user).count()
    streak.total_perfect_days = UserDailyCompletion.objects.filter(
        user=user, is_perfect=True
    ).count()

    if not dates:
        streak.current_streak = 0
        streak.longest_streak = 0
        streak.last_completed_date = None
        streak.save()
        return

    # Calculate longest streak
    longest = 1
    current = 1
    for i in range(1, len(dates)):
        if dates[i] - dates[i - 1] == timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1

    # Calculate current streak (must include today or yesterday)
    today = date.today()
    current_streak = 0
    if dates[-1] >= today - timedelta(days=1):
        current_streak = 1
        for i in range(len(dates) - 2, -1, -1):
            if dates[i + 1] - dates[i] == timedelta(days=1):
                current_streak += 1
            else:
                break

    streak.current_streak = current_streak
    streak.longest_streak = longest
    streak.last_completed_date = dates[-1]
    streak.save()

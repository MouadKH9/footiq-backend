"""
Rebuild UserStreak from UserDailyCompletion history for all users.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.services import _recalculate_streak

User = get_user_model()


class Command(BaseCommand):
    help = "Recalculate streaks for all users from daily completion history"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            type=str,
            default=None,
            help="Recalculate for a specific user ID only",
        )

    def handle(self, *args, **options):
        user_id = options["user_id"]
        if user_id:
            users = User.objects.filter(id=user_id)
        else:
            users = User.objects.all()

        count = 0
        for user in users.iterator():
            _recalculate_streak(user)
            count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Recalculated streaks for {count} user(s).")
        )

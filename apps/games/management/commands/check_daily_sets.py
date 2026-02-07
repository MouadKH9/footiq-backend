"""
Validate completeness of daily sets in a date range.
"""

from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.games.models import DailySet


class Command(BaseCommand):
    help = "Validate completeness of daily sets in a date range"

    def add_arguments(self, parser):
        parser.add_argument(
            "--start", type=str, help="Start date (YYYY-MM-DD), default: today"
        )
        parser.add_argument(
            "--end", type=str, help="End date (YYYY-MM-DD), default: start + 7 days"
        )

    def handle(self, *args, **options):
        start = (
            date.fromisoformat(options["start"])
            if options["start"]
            else date.today()
        )
        end = (
            date.fromisoformat(options["end"])
            if options["end"]
            else start + timedelta(days=7)
        )

        current = start
        warnings = 0
        while current <= end:
            try:
                ds = DailySet.objects.get(date=current)
            except DailySet.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"{current}: No DailySet found")
                )
                warnings += 1
                current += timedelta(days=1)
                continue

            issues = []
            if not hasattr(ds, "career_path_puzzle"):
                issues.append("Missing Career Path puzzle")
            else:
                cp = ds.career_path_puzzle
                if cp.hints.count() == 0:
                    issues.append("Career Path has 0 hints")

            if not hasattr(ds, "grid_puzzle"):
                issues.append("Missing Grid puzzle")
            else:
                gp = ds.grid_puzzle
                cell_count = gp.cells.count()
                if cell_count < 9:
                    issues.append(f"Grid has {cell_count}/9 cells")
                empty = gp.cells.filter(
                    gridcellacceptedplayer__isnull=True
                ).count()
                if empty:
                    issues.append(f"Grid has {empty} cells with no accepted players")

            if not hasattr(ds, "wordle_puzzle"):
                issues.append("Missing Wordle puzzle")

            if ds.status != DailySet.Status.PUBLISHED:
                issues.append(f"Status is '{ds.status}', not published")

            if issues:
                for issue in issues:
                    self.stdout.write(
                        self.style.WARNING(f"{current}: {issue}")
                    )
                warnings += 1
            else:
                self.stdout.write(self.style.SUCCESS(f"{current}: OK"))

            current += timedelta(days=1)

        if warnings:
            self.stdout.write(
                self.style.WARNING(f"\n{warnings} date(s) with issues.")
            )
        else:
            self.stdout.write(self.style.SUCCESS("\nAll dates OK."))

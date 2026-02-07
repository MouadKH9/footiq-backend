"""
Management command to seed player data from Kaggle Transfermarkt CSVs.

Usage:
    python manage.py seed_players \
        --players-csv path/to/players.csv \
        --clubs-csv path/to/clubs.csv \
        --appearances-csv path/to/appearances.csv \
        --generate-aliases --batch-size 1000
"""

import csv
from collections import defaultdict
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.players.models import (
    Club,
    Player,
    PlayerAlias,
    PlayerClubHistory,
    normalize_name,
)


class Command(BaseCommand):
    help = "Seed player, club, and club history data from Kaggle Transfermarkt CSVs"

    def add_arguments(self, parser):
        parser.add_argument("--players-csv", type=str, required=True)
        parser.add_argument("--clubs-csv", type=str, required=True)
        parser.add_argument("--appearances-csv", type=str, default=None)
        parser.add_argument(
            "--generate-aliases", action="store_true", default=False
        )
        parser.add_argument("--batch-size", type=int, default=1000)

    def handle(self, *args, **options):
        batch_size = options["batch_size"]

        self.stdout.write("Importing clubs...")
        self._import_clubs(options["clubs_csv"], batch_size)

        self.stdout.write("Importing players...")
        self._import_players(options["players_csv"], batch_size)

        if options["generate_aliases"]:
            self.stdout.write("Generating aliases...")
            self._generate_aliases(batch_size)

        if options["appearances_csv"]:
            self.stdout.write("Importing club history from appearances...")
            self._import_club_history(options["appearances_csv"], batch_size)

        self.stdout.write(self.style.SUCCESS("Seed complete."))

    def _import_clubs(self, csv_path, batch_size):
        clubs = []
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                club_id = self._int_or_none(row.get("club_id"))
                if club_id is None:
                    continue
                clubs.append(
                    Club(
                        id=club_id,
                        name=row.get("name", "") or row.get("club_name", ""),
                        club_code=row.get("club_code", "") or "",
                        domestic_competition_id=row.get(
                            "domestic_competition_id", ""
                        )
                        or "",
                        stadium_name=row.get("stadium_name", "") or "",
                        logo_url=row.get("logo_url", "") or "",
                        url=row.get("url", "") or "",
                    )
                )

        Club.objects.bulk_create(
            clubs,
            batch_size=batch_size,
            update_conflicts=True,
            unique_fields=["id"],
            update_fields=[
                "name",
                "club_code",
                "domestic_competition_id",
                "stadium_name",
                "logo_url",
                "url",
            ],
        )
        self.stdout.write(f"  {len(clubs)} clubs processed.")

    def _import_players(self, csv_path, batch_size):
        players = []
        club_ids = set(Club.objects.values_list("id", flat=True))

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                player_id = self._int_or_none(row.get("player_id"))
                if player_id is None:
                    continue

                current_club_id = self._int_or_none(row.get("current_club_id"))
                if current_club_id not in club_ids:
                    current_club_id = None

                name = row.get("name", "") or ""
                players.append(
                    Player(
                        id=player_id,
                        first_name=row.get("first_name", "") or "",
                        last_name=row.get("last_name", "") or "",
                        name=name,
                        name_normalized=normalize_name(name),
                        country_of_birth=row.get("country_of_birth", "") or "",
                        city_of_birth=row.get("city_of_birth", "") or "",
                        country_of_citizenship=row.get(
                            "country_of_citizenship", ""
                        )
                        or "",
                        date_of_birth=self._parse_date(
                            row.get("date_of_birth", "")
                        ),
                        position=row.get("position", "") or "",
                        sub_position=row.get("sub_position", "") or "",
                        foot=row.get("foot", "") or "",
                        height_in_cm=self._int_or_none(
                            row.get("height_in_cm", "")
                        ),
                        image_url=row.get("image_url", "") or "",
                        url=row.get("url", "") or "",
                        current_club_id=current_club_id,
                        last_season=self._int_or_none(
                            row.get("last_season", "")
                        ),
                        market_value_in_eur=self._int_or_none(
                            row.get("market_value_in_eur", "")
                        ),
                        highest_market_value_in_eur=self._int_or_none(
                            row.get("highest_market_value_in_eur", "")
                        ),
                    )
                )

        Player.objects.bulk_create(
            players,
            batch_size=batch_size,
            update_conflicts=True,
            unique_fields=["id"],
            update_fields=[
                "first_name",
                "last_name",
                "name",
                "name_normalized",
                "country_of_birth",
                "city_of_birth",
                "country_of_citizenship",
                "date_of_birth",
                "position",
                "sub_position",
                "foot",
                "height_in_cm",
                "image_url",
                "url",
                "current_club_id",
                "last_season",
                "market_value_in_eur",
                "highest_market_value_in_eur",
            ],
        )
        self.stdout.write(f"  {len(players)} players processed.")

    def _generate_aliases(self, batch_size):
        # Delete existing auto-generated aliases
        PlayerAlias.objects.filter(is_auto_generated=True).delete()

        existing = set(
            PlayerAlias.objects.values_list("player_id", "alias_normalized")
        )

        aliases = []
        for player in Player.objects.all().iterator(chunk_size=batch_size):
            variants = set()

            # Full display name
            if player.name:
                variants.add(player.name)
            # Last name only
            if player.last_name:
                variants.add(player.last_name)
            # First + Last
            if player.first_name and player.last_name:
                variants.add(f"{player.first_name} {player.last_name}")

            for variant in variants:
                normalized = normalize_name(variant)
                if not normalized:
                    continue
                if (player.id, normalized) in existing:
                    continue
                existing.add((player.id, normalized))
                aliases.append(
                    PlayerAlias(
                        player_id=player.id,
                        alias=variant,
                        alias_normalized=normalized,
                        is_auto_generated=True,
                    )
                )

        PlayerAlias.objects.bulk_create(
            aliases, batch_size=batch_size, ignore_conflicts=True
        )
        self.stdout.write(f"  {len(aliases)} aliases generated.")

    def _import_club_history(self, csv_path, batch_size):
        player_ids = set(Player.objects.values_list("id", flat=True))
        club_ids = set(Club.objects.values_list("id", flat=True))

        # Group appearances by (player_id, club_id) to aggregate
        grouped = defaultdict(
            lambda: {
                "appearances": 0,
                "goals": 0,
                "assists": 0,
                "seasons": set(),
                "date_joined": None,
                "date_left": None,
            }
        )

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                player_id = self._int_or_none(row.get("player_id"))
                club_id = self._int_or_none(
                    row.get("player_current_club_id")
                    or row.get("current_club_id")
                    or row.get("club_id")
                )
                if player_id not in player_ids or club_id not in club_ids:
                    continue

                key = (player_id, club_id)
                entry = grouped[key]
                entry["appearances"] += self._int_or_none(
                    row.get("yellow_cards", 0)
                ) is not None and 1 or 0
                # Each row in appearances CSV is one appearance
                entry["appearances"] += 1
                entry["goals"] += self._int_or_none(row.get("goals", 0)) or 0
                entry["assists"] += self._int_or_none(
                    row.get("assists", 0)
                ) or 0

                season = row.get("season")
                if season:
                    try:
                        entry["seasons"].add(int(season))
                    except (ValueError, TypeError):
                        pass

                d = self._parse_date(row.get("date", ""))
                if d:
                    if entry["date_joined"] is None or d < entry["date_joined"]:
                        entry["date_joined"] = d
                    if entry["date_left"] is None or d > entry["date_left"]:
                        entry["date_left"] = d

        # Delete existing and bulk create
        PlayerClubHistory.objects.all().delete()
        histories = []
        for (player_id, club_id), data in grouped.items():
            seasons = sorted(data["seasons"]) if data["seasons"] else []
            histories.append(
                PlayerClubHistory(
                    player_id=player_id,
                    club_id=club_id,
                    season_start=seasons[0] if seasons else None,
                    season_end=seasons[-1] if seasons else None,
                    date_joined=data["date_joined"],
                    date_left=data["date_left"],
                    appearances=data["appearances"],
                    goals=data["goals"],
                    assists=data["assists"],
                )
            )

        PlayerClubHistory.objects.bulk_create(histories, batch_size=batch_size)
        self.stdout.write(f"  {len(histories)} club history entries created.")

    @staticmethod
    def _int_or_none(value):
        if value is None or value == "":
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_date(value):
        if not value or value.strip() == "":
            return None
        try:
            parts = value.strip().split("-")
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            return None

import re
import unicodedata

from django.db import models


def normalize_name(name):
    """Normalize a name: NFKD unicode → ASCII, lowercase, strip diacritics/hyphens/apostrophes."""
    if not name:
        return ""
    # NFKD decomposition then strip combining characters (diacritics)
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_text = nfkd.encode("ASCII", "ignore").decode("ASCII")
    # Lowercase, strip hyphens/apostrophes, collapse spaces
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"['\-]", "", ascii_text)
    ascii_text = re.sub(r"\s+", " ", ascii_text).strip()
    return ascii_text


class Club(models.Model):
    id = models.IntegerField(primary_key=True, help_text="Transfermarkt club_id")
    name = models.CharField(max_length=255)
    club_code = models.CharField(max_length=10, blank=True, default="")
    domestic_competition_id = models.CharField(max_length=20, blank=True, default="")
    stadium_name = models.CharField(max_length=255, blank=True, default="")
    logo_url = models.URLField(max_length=500, blank=True, default="")
    url = models.URLField(max_length=500, blank=True, default="")

    class Meta:
        db_table = "players_club"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Player(models.Model):
    class Position(models.TextChoices):
        GOALKEEPER = "Goalkeeper"
        DEFENDER = "Defender"
        MIDFIELD = "Midfield"
        ATTACK = "Attack"

    id = models.IntegerField(primary_key=True, help_text="Transfermarkt player_id")
    first_name = models.CharField(max_length=255, blank=True, default="")
    last_name = models.CharField(max_length=255, blank=True, default="")
    name = models.CharField(max_length=255, help_text="Display name")
    name_normalized = models.CharField(
        max_length=255, db_index=True, blank=True, default=""
    )
    country_of_birth = models.CharField(max_length=100, blank=True, default="")
    city_of_birth = models.CharField(max_length=100, blank=True, default="")
    country_of_citizenship = models.CharField(
        max_length=100, blank=True, default="", db_index=True
    )
    date_of_birth = models.DateField(null=True, blank=True)
    position = models.CharField(
        max_length=20, choices=Position.choices, blank=True, default=""
    )
    sub_position = models.CharField(max_length=50, blank=True, default="")
    foot = models.CharField(max_length=10, blank=True, default="")
    height_in_cm = models.PositiveIntegerField(null=True, blank=True)
    image_url = models.URLField(max_length=500, blank=True, default="")
    url = models.URLField(max_length=500, blank=True, default="")
    current_club = models.ForeignKey(
        Club, on_delete=models.SET_NULL, null=True, blank=True, related_name="players"
    )
    last_season = models.PositiveIntegerField(null=True, blank=True)
    market_value_in_eur = models.BigIntegerField(null=True, blank=True)
    highest_market_value_in_eur = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "players_player"
        indexes = [
            models.Index(fields=["last_name"]),
            models.Index(fields=["position"]),
        ]

    def __str__(self):
        return self.name

    def save(self, **kwargs):
        if not self.name_normalized:
            self.name_normalized = normalize_name(self.name)
        super().save(**kwargs)


class PlayerAlias(models.Model):
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="aliases"
    )
    alias = models.CharField(max_length=255)
    alias_normalized = models.CharField(max_length=255, db_index=True)
    is_auto_generated = models.BooleanField(default=False)

    class Meta:
        db_table = "players_player_alias"
        unique_together = [("player", "alias_normalized")]

    def __str__(self):
        return f"{self.alias} → {self.player.name}"

    def save(self, **kwargs):
        if not self.alias_normalized:
            self.alias_normalized = normalize_name(self.alias)
        super().save(**kwargs)


class PlayerClubHistory(models.Model):
    player = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="club_history"
    )
    club = models.ForeignKey(
        Club, on_delete=models.CASCADE, related_name="player_history"
    )
    season_start = models.PositiveIntegerField(null=True, blank=True)
    season_end = models.PositiveIntegerField(null=True, blank=True)
    date_joined = models.DateField(null=True, blank=True)
    date_left = models.DateField(null=True, blank=True)
    appearances = models.PositiveIntegerField(default=0)
    goals = models.PositiveIntegerField(default=0)
    assists = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "players_player_club_history"
        ordering = ["-season_start"]

    def __str__(self):
        return f"{self.player.name} @ {self.club.name} ({self.season_start})"

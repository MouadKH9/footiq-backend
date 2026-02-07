from rest_framework import serializers

from apps.players.models import Player


class PlayerSearchSerializer(serializers.ModelSerializer):
    current_club_name = serializers.CharField(
        source="current_club.name", default=None, read_only=True
    )
    nationality = serializers.CharField(
        source="country_of_citizenship", read_only=True
    )

    class Meta:
        model = Player
        fields = [
            "id",
            "name",
            "image_url",
            "current_club_name",
            "nationality",
        ]

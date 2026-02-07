from rest_framework import serializers

from apps.progress.models import UserDailyCompletion


class UserDailyCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDailyCompletion
        fields = [
            "date",
            "career_path_result",
            "grid_result",
            "wordle_result",
            "all_completed",
            "is_perfect",
        ]

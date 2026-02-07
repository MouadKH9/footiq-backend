from datetime import date

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.games.models import (
    CareerPathPuzzle,
    DailySet,
    GridPuzzle,
    WordlePuzzle,
)
from apps.games.serializers import DailySetSerializer
from apps.games.services import (
    process_career_path_guess,
    process_grid_guess,
    process_wordle_guess,
)


# --- Daily Set ---

class DailyTodayView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = date.today()
        daily_set = get_object_or_404(
            DailySet.objects.select_related(
                "career_path_puzzle__answer_player",
                "grid_puzzle",
                "wordle_puzzle__answer_player",
            ).prefetch_related(
                "career_path_puzzle__hints",
                "grid_puzzle__labels",
                "grid_puzzle__cells",
            ),
            date=today,
            status=DailySet.Status.PUBLISHED,
        )
        serializer = DailySetSerializer(
            daily_set, context={"user": request.user}
        )
        return Response(serializer.data)


class DailyDateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, date_str):
        try:
            puzzle_date = date.fromisoformat(date_str)
        except ValueError:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        daily_set = get_object_or_404(
            DailySet.objects.select_related(
                "career_path_puzzle__answer_player",
                "grid_puzzle",
                "wordle_puzzle__answer_player",
            ).prefetch_related(
                "career_path_puzzle__hints",
                "grid_puzzle__labels",
                "grid_puzzle__cells",
            ),
            date=puzzle_date,
            status=DailySet.Status.PUBLISHED,
        )
        serializer = DailySetSerializer(
            daily_set, context={"user": request.user}
        )
        return Response(serializer.data)


# --- Guess Endpoints ---

class CareerPathGuessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, puzzle_id):
        puzzle = get_object_or_404(CareerPathPuzzle, id=puzzle_id)
        guess_text = request.data.get("guess_text")
        player_id = request.data.get("player_id")

        result = process_career_path_guess(
            user=request.user,
            puzzle=puzzle,
            guess_text=guess_text,
            player_id=player_id,
        )

        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class GridGuessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, puzzle_id):
        puzzle = get_object_or_404(GridPuzzle, id=puzzle_id)
        guess_text = request.data.get("guess_text")
        player_id = request.data.get("player_id")
        row = request.data.get("row")
        col = request.data.get("col")

        if row is None or col is None:
            return Response(
                {"error": "row and col are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            row = int(row)
            col = int(col)
        except (TypeError, ValueError):
            return Response(
                {"error": "row and col must be integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = process_grid_guess(
            user=request.user,
            puzzle=puzzle,
            row=row,
            col=col,
            guess_text=guess_text,
            player_id=player_id,
        )

        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class WordleGuessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, puzzle_id):
        puzzle = get_object_or_404(WordlePuzzle, id=puzzle_id)
        word = request.data.get("word", "").strip()

        if not word:
            return Response(
                {"error": "word is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = process_wordle_guess(
            user=request.user,
            puzzle=puzzle,
            word=word,
        )

        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


# --- Share Endpoints ---

class ShareDailyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, date_str):
        try:
            puzzle_date = date.fromisoformat(date_str)
        except ValueError:
            return Response(
                {"detail": "Invalid date format."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.games.share import generate_daily_share
        text = generate_daily_share(request.user, puzzle_date)
        if text is None:
            return Response(
                {"detail": "No completed games for this date."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"share_text": text})


class ShareCareerPathView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, puzzle_id):
        puzzle = get_object_or_404(CareerPathPuzzle, id=puzzle_id)
        from apps.games.share import generate_career_path_share
        text = generate_career_path_share(request.user, puzzle)
        if text is None:
            return Response(
                {"detail": "Game not completed."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"share_text": text})


class ShareGridView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, puzzle_id):
        puzzle = get_object_or_404(GridPuzzle, id=puzzle_id)
        from apps.games.share import generate_grid_share
        text = generate_grid_share(request.user, puzzle)
        if text is None:
            return Response(
                {"detail": "Game not completed."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"share_text": text})


class ShareWordleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, puzzle_id):
        puzzle = get_object_or_404(WordlePuzzle, id=puzzle_id)
        from apps.games.share import generate_wordle_share
        text = generate_wordle_share(request.user, puzzle)
        if text is None:
            return Response(
                {"detail": "Game not completed."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"share_text": text})

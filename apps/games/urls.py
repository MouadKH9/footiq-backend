from django.urls import path

from apps.games.views import (
    CareerPathGuessView,
    DailyDateView,
    DailyTodayView,
    GridGuessView,
    ShareCareerPathView,
    ShareDailyView,
    ShareGridView,
    ShareWordleView,
    WordleGuessView,
)

app_name = "games"

urlpatterns = [
    # Daily
    path("daily/today/", DailyTodayView.as_view(), name="daily-today"),
    path("daily/<str:date_str>/", DailyDateView.as_view(), name="daily-date"),
    # Guess submissions
    path(
        "games/career-path/<int:puzzle_id>/guess/",
        CareerPathGuessView.as_view(),
        name="career-path-guess",
    ),
    path(
        "games/grid/<int:puzzle_id>/guess/",
        GridGuessView.as_view(),
        name="grid-guess",
    ),
    path(
        "games/wordle/<int:puzzle_id>/guess/",
        WordleGuessView.as_view(),
        name="wordle-guess",
    ),
    # Share
    path(
        "share/daily/<str:date_str>/",
        ShareDailyView.as_view(),
        name="share-daily",
    ),
    path(
        "share/career-path/<int:puzzle_id>/",
        ShareCareerPathView.as_view(),
        name="share-career-path",
    ),
    path(
        "share/grid/<int:puzzle_id>/",
        ShareGridView.as_view(),
        name="share-grid",
    ),
    path(
        "share/wordle/<int:puzzle_id>/",
        ShareWordleView.as_view(),
        name="share-wordle",
    ),
]

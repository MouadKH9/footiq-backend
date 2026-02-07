from django.urls import path

from apps.progress.views import UserHistoryView, UserStatsView

app_name = "progress"

urlpatterns = [
    path("me/", UserStatsView.as_view(), name="user-stats"),
    path("me/history/", UserHistoryView.as_view(), name="user-history"),
]

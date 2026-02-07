from django.urls import path

from apps.players.views import PlayerSearchView

app_name = "players"

urlpatterns = [
    path("search/", PlayerSearchView.as_view(), name="player-search"),
]

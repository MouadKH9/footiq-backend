from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("_nested_admin/", include("nested_admin.urls")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/players/", include("apps.players.urls")),
    path("api/v1/", include("apps.games.urls")),
    path("api/v1/stats/", include("apps.progress.urls")),
]

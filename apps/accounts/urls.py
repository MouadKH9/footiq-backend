from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import DeviceRegisterView, LoginView, UpgradeView

app_name = "accounts"

urlpatterns = [
    path("device/", DeviceRegisterView.as_view(), name="device-register"),
    path("upgrade/", UpgradeView.as_view(), name="upgrade"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]

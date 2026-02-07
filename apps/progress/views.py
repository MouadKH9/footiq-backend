from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.progress.models import UserDailyCompletion
from apps.progress.serializers import UserDailyCompletionSerializer
from apps.progress.services import get_user_stats


class UserStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stats = get_user_stats(request.user)
        return Response(stats)


class UserHistoryView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserDailyCompletionSerializer

    def get_queryset(self):
        return UserDailyCompletion.objects.filter(user=self.request.user)

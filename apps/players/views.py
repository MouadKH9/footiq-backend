from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.players.serializers import PlayerSearchSerializer
from apps.players.services import search_players


class PlayerSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response([])

        limit = min(int(request.query_params.get("limit", 10)), 20)
        players = search_players(query, limit=limit)
        serializer = PlayerSearchSerializer(players, many=True)
        return Response(serializer.data)

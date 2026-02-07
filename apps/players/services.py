"""
Player search and guess resolution service.
All player matching MUST go through these functions.
"""

from dataclasses import dataclass

from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q

from apps.players.models import Player, PlayerAlias, normalize_name


@dataclass
class GuessResult:
    status: str  # "exact", "ambiguous", "no_match"
    player: Player | None = None
    candidates: list | None = None


def resolve_guess(guess_text: str) -> GuessResult:
    """
    Resolve free-text guess to a player.
    Returns exact match, ambiguous candidates, or no_match.
    """
    normalized = normalize_name(guess_text)
    if not normalized:
        return GuessResult(status="no_match")

    # 1. Exact alias match
    exact_aliases = PlayerAlias.objects.filter(
        alias_normalized=normalized
    ).select_related("player")
    players_from_alias = {a.player_id: a.player for a in exact_aliases}
    if len(players_from_alias) == 1:
        player = list(players_from_alias.values())[0]
        return GuessResult(status="exact", player=player)

    # 2. Exact name_normalized match on Player
    exact_players = Player.objects.filter(name_normalized=normalized)
    if exact_players.count() == 1:
        return GuessResult(status="exact", player=exact_players.first())

    # Combine exact matches from both
    combined = set(players_from_alias.keys()) | set(
        exact_players.values_list("id", flat=True)
    )
    if len(combined) == 1:
        player = Player.objects.get(id=list(combined)[0])
        return GuessResult(status="exact", player=player)
    if len(combined) > 1:
        candidates = list(Player.objects.filter(id__in=combined)[:10])
        return GuessResult(status="ambiguous", candidates=candidates)

    # 3. Prefix match on aliases
    prefix_aliases = PlayerAlias.objects.filter(
        alias_normalized__startswith=normalized
    ).select_related("player")[:20]
    prefix_players = {a.player_id: a.player for a in prefix_aliases}
    if len(prefix_players) == 1:
        return GuessResult(
            status="exact", player=list(prefix_players.values())[0]
        )
    if len(prefix_players) > 1:
        return GuessResult(
            status="ambiguous",
            candidates=list(prefix_players.values())[:10],
        )

    # 4. Contains match on aliases
    contains_aliases = PlayerAlias.objects.filter(
        alias_normalized__contains=normalized
    ).select_related("player")[:20]
    contains_players = {a.player_id: a.player for a in contains_aliases}
    if len(contains_players) == 1:
        return GuessResult(
            status="exact", player=list(contains_players.values())[0]
        )
    if len(contains_players) > 1:
        return GuessResult(
            status="ambiguous",
            candidates=list(contains_players.values())[:10],
        )

    # 5. Trigram similarity via pg_trgm
    trigram_matches = (
        PlayerAlias.objects.annotate(
            similarity=TrigramSimilarity("alias_normalized", normalized)
        )
        .filter(similarity__gt=0.3)
        .order_by("-similarity")
        .select_related("player")[:10]
    )

    if trigram_matches:
        top = trigram_matches[0]
        if top.similarity >= 0.6:
            # High confidence — check if single player
            high_matches = [m for m in trigram_matches if m.similarity >= 0.6]
            player_ids = {m.player_id for m in high_matches}
            if len(player_ids) == 1:
                return GuessResult(status="exact", player=top.player)

        # Return as ambiguous
        seen = {}
        for m in trigram_matches:
            if m.player_id not in seen:
                seen[m.player_id] = m.player
        return GuessResult(
            status="ambiguous", candidates=list(seen.values())[:10]
        )

    return GuessResult(status="no_match")


def search_players(query: str, limit: int = 10) -> list[Player]:
    """
    Autocomplete player search. Uses normalized matching,
    prioritizing prefix matches.
    """
    normalized = normalize_name(query)
    if not normalized:
        return []

    # Prefix matches on alias_normalized (highest priority)
    prefix_alias_ids = set(
        PlayerAlias.objects.filter(
            alias_normalized__startswith=normalized
        ).values_list("player_id", flat=True)[:limit]
    )

    # Prefix on name_normalized
    prefix_name_ids = set(
        Player.objects.filter(
            name_normalized__startswith=normalized
        ).values_list("id", flat=True)[:limit]
    )

    player_ids = prefix_alias_ids | prefix_name_ids

    # If not enough, try contains
    if len(player_ids) < limit:
        contains_ids = set(
            PlayerAlias.objects.filter(
                alias_normalized__contains=normalized
            )
            .exclude(player_id__in=player_ids)
            .values_list("player_id", flat=True)[: limit - len(player_ids)]
        )
        player_ids |= contains_ids

    # If still not enough, try trigram
    if len(player_ids) < limit:
        trigram_ids = set(
            PlayerAlias.objects.annotate(
                similarity=TrigramSimilarity("alias_normalized", normalized)
            )
            .filter(similarity__gt=0.3)
            .exclude(player_id__in=player_ids)
            .order_by("-similarity")
            .values_list("player_id", flat=True)[: limit - len(player_ids)]
        )
        player_ids |= trigram_ids

    return list(
        Player.objects.filter(id__in=player_ids).select_related(
            "current_club"
        )[:limit]
    )

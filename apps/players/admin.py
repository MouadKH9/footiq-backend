from django.contrib import admin

from apps.players.models import Club, Player, PlayerAlias, PlayerClubHistory


class PlayerAliasInline(admin.TabularInline):
    model = PlayerAlias
    extra = 1
    fields = ("alias", "alias_normalized", "is_auto_generated")
    readonly_fields = ("alias_normalized",)


class PlayerClubHistoryInline(admin.TabularInline):
    model = PlayerClubHistory
    extra = 0
    fields = (
        "club",
        "season_start",
        "season_end",
        "appearances",
        "goals",
        "assists",
    )
    raw_id_fields = ("club",)


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("name", "position", "country_of_citizenship", "current_club")
    list_filter = ("position", "country_of_citizenship")
    search_fields = ("name", "last_name", "first_name", "aliases__alias")
    raw_id_fields = ("current_club",)
    inlines = [PlayerAliasInline, PlayerClubHistoryInline]

    def get_search_results(self, request, queryset, search_term):
        queryset, may_have_duplicates = super().get_search_results(
            request, queryset, search_term
        )
        return queryset.distinct(), may_have_duplicates


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ("name", "club_code", "domestic_competition_id")
    search_fields = ("name", "club_code")
    list_filter = ("domestic_competition_id",)


@admin.register(PlayerAlias)
class PlayerAliasAdmin(admin.ModelAdmin):
    list_display = ("alias", "player", "is_auto_generated")
    search_fields = ("alias", "player__name")
    raw_id_fields = ("player",)

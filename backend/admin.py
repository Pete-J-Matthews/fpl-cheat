from django.contrib import admin
from .models import Creator, Team, Player, TeamPlayer


@admin.register(Creator)
class CreatorAdmin(admin.ModelAdmin):
    list_display = ['name', 'team_id', 'created_at']
    search_fields = ['name']
    list_filter = ['created_at']


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['team_name', 'owner_name', 'team_id', 'created_at']
    search_fields = ['team_name', 'owner_name']
    list_filter = ['created_at']


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['name', 'position', 'team_code', 'price', 'created_at']
    search_fields = ['name']
    list_filter = ['position', 'team_code', 'created_at']


@admin.register(TeamPlayer)
class TeamPlayerAdmin(admin.ModelAdmin):
    list_display = ['team', 'player', 'is_captain', 'is_vice_captain']
    list_filter = ['is_captain', 'is_vice_captain', 'created_at']
    search_fields = ['team__team_name', 'player__name']

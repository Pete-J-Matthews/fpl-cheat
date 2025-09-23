from django.http import JsonResponse
from django.shortcuts import render
from .models import Creator, Team, Player


def healthcheck(request):
    """Health check endpoint"""
    return JsonResponse({"status": "ok", "message": "FPL Cheat API is running"})


def root(request):
    """Root endpoint"""
    return JsonResponse({"message": "FPL Cheat API", "status": "running"})


def creators_list(request):
    """List all creators"""
    creators = Creator.objects.all()
    data = [{"name": c.name, "team_id": c.team_id} for c in creators]
    return JsonResponse({"creators": data})


def teams_list(request):
    """List all teams"""
    teams = Team.objects.all()
    data = [{"team_name": t.team_name, "team_id": t.team_id, "owner_name": t.owner_name} for t in teams]
    return JsonResponse({"teams": data})

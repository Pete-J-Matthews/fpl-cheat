from django.db import models
from django.utils import timezone


class Creator(models.Model):
    """Content creator who has an FPL team"""
    name = models.CharField(max_length=100, unique=True)
    team_id = models.IntegerField(unique=True, help_text="FPL team ID")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} (Team ID: {self.team_id})"
    
    class Meta:
        ordering = ['name']


class Team(models.Model):
    """FPL team data"""
    team_id = models.IntegerField(unique=True, help_text="FPL team ID")
    team_name = models.CharField(max_length=100)
    owner_name = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.team_name} (ID: {self.team_id})"
    
    class Meta:
        ordering = ['team_name']


class Player(models.Model):
    """FPL player data"""
    player_id = models.IntegerField(unique=True, help_text="FPL player ID")
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=20, choices=[
        ('GK', 'Goalkeeper'),
        ('DEF', 'Defender'),
        ('MID', 'Midfielder'),
        ('FWD', 'Forward'),
    ])
    team_code = models.IntegerField(help_text="FPL team code")
    price = models.DecimalField(max_digits=5, decimal_places=1, help_text="Player price in millions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.position}) - {self.price}m"
    
    class Meta:
        ordering = ['name']


class TeamPlayer(models.Model):
    """Junction table for teams and their players"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='players')
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    is_captain = models.BooleanField(default=False)
    is_vice_captain = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        captain_status = " (C)" if self.is_captain else " (VC)" if self.is_vice_captain else ""
        return f"{self.team.team_name} - {self.player.name}{captain_status}"
    
    class Meta:
        unique_together = ['team', 'player']
        ordering = ['-is_captain', '-is_vice_captain', 'player__name']

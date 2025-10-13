from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    """Extended user profile with score for leaderboard"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    score = models.IntegerField(default=0)
    avatar_url = models.URLField(blank=True, null=True)
    
    class Meta:
        ordering = ['-score']  # Order by score descending
    
    def __str__(self):
        return f"{self.user.username} - {self.score} pts"

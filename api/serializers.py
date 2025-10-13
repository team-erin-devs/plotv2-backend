from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile

class LeaderboardSerializer(serializers.Serializer):
    """Serializer for leaderboard entries"""
    id = serializers.IntegerField(source='user.id')
    username = serializers.CharField(source='user.username')
    score = serializers.IntegerField()
    avatar_url = serializers.URLField(allow_null=True)
    rank = serializers.IntegerField()

from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import UserProfile
from .serializers import LeaderboardSerializer

@api_view(['GET'])
def leaderboard(request):
    """
    Get the top users ranked by score
    Query params:
    - limit: number of users to return (default: 10, max: 100)
    """
    limit = int(request.GET.get('limit', 10))
    limit = min(limit, 100)  # Cap at 100
    
    # Get top users ordered by score
    profiles = UserProfile.objects.select_related('user').all()[:limit]
    
    # Add rank to each profile
    leaderboard_data = []
    for rank, profile in enumerate(profiles, start=1):
        data = {
            'user': profile.user,
            'score': profile.score,
            'avatar_url': profile.avatar_url,
            'rank': rank
        }
        leaderboard_data.append(data)
    
    serializer = LeaderboardSerializer(leaderboard_data, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def health_check(request):
    """Simple health check endpoint"""
    return Response({"status": "ok", "message": "API is running"})

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for API endpoints
router = DefaultRouter()

urlpatterns = [
    # Challenge endpoints
    path('challenges/', views.ChallengeListView.as_view(), name='challenge-list'),
    path('challenges/<int:pk>/', views.ChallengeDetailView.as_view(), name='challenge-detail'),
    path('challenges/<int:challenge_id>/stats/', views.challenge_stats, name='challenge-stats'),
    
    # Proof upload endpoints
    path('challenges/<int:challenge_id>/upload/', views.ProofUploadView.as_view(), name='proof-upload'),
    path('proofs/', views.UserProofsListView.as_view(), name='user-proofs-list'),
    path('proofs/<int:pk>/', views.ProofDetailView.as_view(), name='proof-detail'),
    
    # Admin/Staff endpoints
    path('admin/proofs/', views.ProofReviewListView.as_view(), name='proof-review-list'),
    
    # Leaderboard and stats
    path('leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),
    path('user/stats/', views.user_stats, name='user-stats'),
    
    # Include router URLs
    path('', include(router.urls)),
]

from django.urls import path
from . import views
from .auth import register, login


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

    # Leaderboard and user stats
    path('leaderboard/', views.leaderboard, name='leaderboard'),  # <- function, no as_view()
    path('user/stats/', views.user_stats, name='user-stats'),

    # Optional health check
    path('health/', views.health_check, name='health-check'),

    # Auth endpoints
    path('auth/register/', register, name='register'),
    path('auth/login/', login, name='login'),
]

from django.urls import path
from . import views
from .auth import register, login, refresh_token, logout
from .views import (
    user_profile, send_friend_request, respond_friend_request, list_friends_and_requests,
    SidequestListCreateView, SidequestDetailView,
    join_sidequest, leave_sidequest, campus_board, my_sidequests, joined_sidequests,
    search_users, top_users, discover_feed, view_user_profile,
)


urlpatterns = [
    # Sidequest endpoints
    path('sidequests/', SidequestListCreateView.as_view(), name='sidequest-list-create'),
    path('sidequests/<int:pk>/', SidequestDetailView.as_view(), name='sidequest-detail'),
    path('sidequests/<int:pk>/join/', join_sidequest, name='sidequest-join'),
    path('sidequests/<int:pk>/leave/', leave_sidequest, name='sidequest-leave'),
    path('sidequests/campus/', campus_board, name='campus-board'),
    path('sidequests/mine/', my_sidequests, name='my-sidequests'),
    path('sidequests/joined/', joined_sidequests, name='joined-sidequests'),

    # User profile and stats
    path('user/stats/', views.user_stats, name='user-stats'),
    path('user/profile/', user_profile, name='user-profile'),
    path('user/profile/<int:user_id>/', view_user_profile, name='view-user-profile'),

    # Profile picture presign (kept active)
    path("profile-picture/presign/", views.ProfilePicturePresignView.as_view(), name="profile-picture-presign"),

    # Friend system endpoints
    path('friends/', list_friends_and_requests, name='list-friends'),
    path('friends/request/', send_friend_request, name='send-friend-request'),
    path('friends/request/<int:request_id>/respond/', respond_friend_request, name='respond-friend-request'),

    # Auth endpoints
    path('auth/register/', register, name='register'),
    path('auth/login/', login, name='login'),
    path('auth/refresh_token/', refresh_token, name='refresh-token'),
    path('auth/logout/', logout, name='logout'),

    # Search & discover
    path('search/users/', search_users, name='search-users'),
    path('search/top-users/', top_users, name='top-users'),
    path('search/discover/', discover_feed, name='discover-feed'),

    # Health check
    path('health/', views.health_check, name='health-check'),
]

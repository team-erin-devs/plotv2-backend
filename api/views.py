from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from .models import Sidequest, SidequestParticipant, UserProfile, FriendRequest
from .serializers import (
    SidequestSerializer, SidequestCreateSerializer, SidequestParticipantSerializer,
    UserProfileSerializer, FriendRequestSerializer
)

import os
import uuid
import mimetypes
import boto3
import botocore
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from urllib.parse import urlparse


# ============================================================================
# Sidequest Views
# ============================================================================

class SidequestListCreateView(generics.ListCreateAPIView):
    """
    GET: List sidequests from friends (friend board)
    POST: Create a new sidequest
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SidequestCreateSerializer
        return SidequestSerializer

    def get_queryset(self):
        """Return sidequests created by the user or their friends"""
        user = self.request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        friend_user_ids = profile.friends.values_list('user_id', flat=True)

        return Sidequest.objects.filter(
            Q(creator=user) | Q(creator_id__in=friend_user_ids)
        ).select_related('creator').prefetch_related('participants__user__profile').distinct()

    def perform_create(self, serializer):
        serializer.save()

    def create(self, request, *args, **kwargs):
        serializer = SidequestCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        sidequest = serializer.save()
        # Return the full serialized sidequest
        return Response(
            SidequestSerializer(sidequest, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class SidequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE a sidequest (edit/delete only by creator)"""
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return SidequestCreateSerializer
        return SidequestSerializer

    def get_queryset(self):
        return Sidequest.objects.select_related('creator').prefetch_related(
            'participants__user__profile'
        )

    def perform_update(self, serializer):
        if self.get_object().creator != self.request.user:
            raise permissions.PermissionDenied("Only the creator can edit this sidequest.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.creator != self.request.user:
            raise permissions.PermissionDenied("Only the creator can cancel this sidequest.")
        instance.status = 'cancelled'
        instance.save()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        if instance.creator != request.user:
            return Response(
                {"detail": "Only the creator can edit this sidequest."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(SidequestSerializer(instance, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def join_sidequest(request, pk):
    """Join a sidequest"""
    sidequest = get_object_or_404(Sidequest, pk=pk)

    if sidequest.creator == request.user:
        return Response({"detail": "You're already part of this sidequest as the creator."}, status=400)

    if sidequest.is_full:
        return Response({"detail": "This sidequest is full."}, status=400)

    if sidequest.status != 'upcoming':
        return Response({"detail": "This sidequest is no longer accepting participants."}, status=400)

    participant, created = SidequestParticipant.objects.get_or_create(
        sidequest=sidequest,
        user=request.user,
        defaults={'status': 'going'}
    )

    if not created:
        if participant.status == 'going':
            return Response({"detail": "You've already joined this sidequest."}, status=400)
        # Re-join if previously declined
        participant.status = 'going'
        participant.save()

    return Response(
        SidequestSerializer(sidequest, context={'request': request}).data,
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def leave_sidequest(request, pk):
    """Leave a sidequest"""
    sidequest = get_object_or_404(Sidequest, pk=pk)

    if sidequest.creator == request.user:
        return Response({"detail": "The creator can't leave. Cancel the sidequest instead."}, status=400)

    try:
        participant = SidequestParticipant.objects.get(sidequest=sidequest, user=request.user)
        participant.status = 'declined'
        participant.save()
        return Response(
            SidequestSerializer(sidequest, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )
    except SidequestParticipant.DoesNotExist:
        return Response({"detail": "You're not a participant."}, status=400)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def rate_sidequest(request, pk):
    """Rate a completed sidequest (1-5) as a participant."""
    sidequest = get_object_or_404(Sidequest, pk=pk)
    
    rating = request.data.get('rating')
    if rating not in [1, 2, 3, 4, 5]:
        return Response({"detail": "Rating must be an integer between 1 and 5"}, status=400)

    try:
        participant = SidequestParticipant.objects.get(sidequest=sidequest, user=request.user)
    except SidequestParticipant.DoesNotExist:
        return Response({"detail": "You must be a participant to rate this sidequest."}, status=403)

    # Allow rating if the event datetime has passed or status is completed
    if sidequest.status != 'completed' and sidequest.event_datetime > timezone.now():
        return Response({"detail": "You can only rate completed or past sidequests."}, status=400)

    participant.rating = rating
    participant.save()
    
    return Response({"detail": "Rating saved successfully.", "rating": rating}, status=200)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_sidequest_image(request, pk):
    """Add an image URL to a sidequest. Can be done by any participant."""
    sidequest = get_object_or_404(Sidequest, pk=pk)
    
    file_url = request.data.get('file_url')
    if not file_url:
        return Response({"detail": "file_url is required"}, status=400)

    is_creator = (sidequest.creator == request.user)
    is_participant = SidequestParticipant.objects.filter(sidequest=sidequest, user=request.user, status='going').exists()

    if not (is_creator or is_participant):
        return Response({"detail": "Only participants can upload images to a sidequest."}, status=403)

    # Append to images list
    current_images = list(sidequest.images) if sidequest.images else []
    current_images.append(file_url)
    sidequest.images = current_images
    sidequest.save()

    return Response({
        "detail": "Image added successfully", 
        "images": current_images
    }, status=200)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def campus_board(request):
    """List sidequests posted to the campus board"""
    sidequests = Sidequest.objects.filter(
        post_to_campus_board=True,
        status='upcoming',
    ).select_related('creator').prefetch_related('participants__user__profile')

    serializer = SidequestSerializer(sidequests, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_sidequests(request):
    """List sidequests I created"""
    sidequests = Sidequest.objects.filter(
        creator=request.user
    ).select_related('creator').prefetch_related('participants__user__profile')

    serializer = SidequestSerializer(sidequests, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def joined_sidequests(request):
    """List sidequests I'm actively participating in (not ones I created)"""
    sidequest_ids = SidequestParticipant.objects.filter(
        user=request.user,
        status='going',
    ).values_list('sidequest_id', flat=True)

    sidequests = Sidequest.objects.filter(
        id__in=sidequest_ids,
    ).select_related('creator').prefetch_related('participants__user__profile')

    serializer = SidequestSerializer(sidequests, many=True, context={'request': request})
    return Response(serializer.data)

# ============================================================================
# User Profile & Stats (kept, updated for sidequests)
# ============================================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_stats(request):
    """Get current user's sidequest statistics"""
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    stats = {
        'sidequests_created': user.created_sidequests.count(),
        'sidequests_joined': SidequestParticipant.objects.filter(
            user=user, status='going'
        ).count(),
        'sidequests_upcoming': Sidequest.objects.filter(
            Q(creator=user) | Q(participants__user=user, participants__status='going'),
            status='upcoming',
        ).distinct().count(),
        'friends_count': profile.friends.count(),
    }

    return Response(stats)


@api_view(['GET', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def user_profile(request):
    """Get or update current user's profile"""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'GET':
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)

    elif request.method == 'PATCH':
        allowed_fields = ['bio', 'major', 'class_year', 'profile_picture', 'university', 'display_name', 'interests']
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

        serializer = UserProfileSerializer(profile, data=update_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def view_user_profile(request, user_id):
    """Get another user's public profile, stats, and active sidequests"""
    target_user = get_object_or_404(User, id=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)

    # Check if current user is friends with target
    is_friend = profile.friends.filter(id=request.user.id).exists()

    # Check if there's a pending friend request
    pending_sent = FriendRequest.objects.filter(
        sender=request.user, receiver=target_user, status='pending'
    ).exists()
    pending_received_req = FriendRequest.objects.filter(
        sender=target_user, receiver=request.user, status='pending'
    ).first()
    pending_received_id = pending_received_req.id if pending_received_req else None

    # Stats
    stats = {
        'sidequests_created': target_user.created_sidequests.count(),
        'sidequests_joined': SidequestParticipant.objects.filter(
            user=target_user, status='going'
        ).count(),
        'friends_count': profile.friends.count(),
    }

    # Active sidequests (public ones + shared if friends)
    active_sqs = []
    sidequests = Sidequest.objects.filter(
        creator=target_user, status='upcoming'
    ).order_by('-event_datetime')[:5]
    for sq in sidequests:
        active_sqs.append({
            'id': sq.id,
            'title': sq.title,
            'description': sq.description,
            'vibe': sq.vibe,
            'event_datetime': sq.event_datetime.isoformat(),
            'creator': {'username': sq.creator.username},
        })

    # Past sidequests
    past_sqs = []
    past_sidequests_query = Sidequest.objects.filter(
        creator=target_user, event_datetime__lt=timezone.now()
    ).order_by('-event_datetime')[:5]
    for sq in past_sidequests_query:
        past_sqs.append({
            'id': sq.id,
            'title': sq.title,
            'description': sq.description,
            'vibe': sq.vibe,
            'event_datetime': sq.event_datetime.isoformat(),
            'creator': {'username': sq.creator.username},
            'images': sq.images,
        })

    return Response({
        'user': {
            'id': target_user.id,
            'username': target_user.username,
        },
        'display_name': profile.display_name or target_user.first_name or target_user.username,
        'profile_picture': profile.profile_picture or '',
        'bio': profile.bio or '',
        'interests': profile.interests or [],
        'stats': stats,
        'active_sidequests': active_sqs,
        'past_sidequests': past_sqs,
        'is_friend': is_friend,
        'pending_sent': pending_sent,
        'pending_received_id': pending_received_id,
    })


# ============================================================================
# Friend System (kept unchanged)
# ============================================================================

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_friend_request(request):
    """Send a friend request using a target username"""
    target_username = request.data.get('username')
    if not target_username:
        return Response({"error": "Username is required"}, status=400)
        
    try:
        receiver = User.objects.get(username=target_username)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    if request.user == receiver:
        return Response({"error": "You cannot add yourself"}, status=400)

    # Check if already friends
    if request.user.profile.friends.filter(id=receiver.profile.id).exists():
        return Response({"error": "Already friends"}, status=400)

    # Create or get pending request
    friend_request, created = FriendRequest.objects.get_or_create(
        sender=request.user,
        receiver=receiver,
        defaults={'status': 'pending'}
    )

    if not created and friend_request.status == 'pending':
        return Response({"message": "Request already sent"}, status=400)

    return Response({"message": "Friend request sent!"}, status=201)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def respond_friend_request(request, request_id):
    """Accept or reject a friend request"""
    action = request.data.get('action')

    try:
        friend_req = FriendRequest.objects.get(id=request_id, receiver=request.user, status='pending')
    except FriendRequest.DoesNotExist:
        return Response({"error": "Pending request not found"}, status=404)

    if action == 'accept':
        friend_req.status = 'accepted'
        friend_req.save()
        request.user.profile.friends.add(friend_req.sender.profile)
        return Response({"message": "Friend added!"})

    elif action == 'reject':
        friend_req.status = 'rejected'
        friend_req.save()
        return Response({"message": "Request rejected"})

    return Response({"error": "Invalid action"}, status=400)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_friends_and_requests(request):
    """Get my friends and pending incoming requests"""
    friends = request.user.profile.friends.all()
    friends_data = [{
        "username": profile.user.username,
        "avatar": profile.profile_picture,
    } for profile in friends]

    pending_requests = FriendRequest.objects.filter(receiver=request.user, status='pending')
    requests_data = FriendRequestSerializer(pending_requests, many=True).data

    return Response({
        "friends": friends_data,
        "pending_requests": requests_data
    })


# ============================================================================
# Health Check (kept)
# ============================================================================

@api_view(['GET'])
def health_check(request):
    """Simple health check endpoint"""
    return Response({"status": "ok", "message": "API is running"})


# ============================================================================
# KEPT: ProfilePicturePresignView (active, for profile picture uploads)
# ============================================================================

class ProfilePicturePresignView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        filename = request.data.get("filename")

        if not filename:
            return Response({"detail": "filename is required"}, status=400)

        required_env_vars = ['B2_KEY_ID', 'B2_APP_KEY', 'B2_ENDPOINT', 'B2_BUCKET']
        missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
        if missing_vars:
            return Response({
                "detail": f"Cloud storage not configured. Missing: {', '.join(missing_vars)}"
            }, status=503)

        ext = filename.split('.')[-1].lower()
        if ext not in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
            return Response({"detail": "Invalid file type. Use jpg, png, webp, or gif"}, status=400)

        key = f"profile-pictures/{request.user.id}/{uuid.uuid4().hex}.{ext}"

        session = boto3.session.Session()
        s3 = session.client(
            service_name="s3",
            aws_access_key_id=os.environ["B2_KEY_ID"],
            aws_secret_access_key=os.environ["B2_APP_KEY"],
            region_name=os.environ.get("B2_REGION"),
            endpoint_url=os.environ["B2_ENDPOINT"],
            config=botocore.client.Config(signature_version='s3v4')
        )

        presigned_url = s3.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': os.environ['B2_BUCKET'],
                'Key': key,
                'ContentType': f'image/{ext}',
            },
            ExpiresIn=3600
        )

        file_url = f"{os.environ['B2_ENDPOINT']}/{os.environ['B2_BUCKET']}/{key}"

        return Response({
            "file_url": file_url,
            "presigned_url": presigned_url
        })


class SidequestImagePresignView(APIView):
    """Generates a presigned URL to upload a sidequest image directly to B2"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        sidequest = get_object_or_404(Sidequest, pk=pk)
        filename = request.data.get("filename")

        if not filename:
            return Response({"detail": "filename is required"}, status=400)

        is_creator = (sidequest.creator == request.user)
        is_participant = SidequestParticipant.objects.filter(sidequest=sidequest, user=request.user, status='going').exists()

        if not (is_creator or is_participant):
            return Response({"detail": "Only participants can upload images to a sidequest."}, status=403)

        required_env_vars = ['B2_KEY_ID', 'B2_APP_KEY', 'B2_ENDPOINT', 'B2_BUCKET']
        missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
        if missing_vars:
            return Response({
                "detail": f"Cloud storage not configured. Missing: {', '.join(missing_vars)}"
            }, status=503)

        ext = filename.split('.')[-1].lower()
        if ext not in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
            return Response({"detail": "Invalid file type. Use jpg, png, webp, or gif"}, status=400)

        key = f"sidequest-images/{sidequest.id}/{uuid.uuid4().hex}.{ext}"
        import mimetypes
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

        s3 = boto3.client(
            's3',
            endpoint_url=os.environ['B2_ENDPOINT'],
            aws_access_key_id=os.environ["B2_KEY_ID"],
            aws_secret_access_key=os.environ["B2_APP_KEY"],
            config=boto3.session.Config(signature_version='s3v4')
        )

        presigned_url = s3.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': os.environ['B2_BUCKET'],
                'Key': key,
            },
            ExpiresIn=3600,
            HttpMethod='PUT'
        )

        file_url = f"{os.environ['B2_ENDPOINT']}/{os.environ['B2_BUCKET']}/{key}"

        return Response({
            "file_url": file_url,
            "presigned_url": presigned_url,
            "content_type": content_type
        })


# ============================================================================
# Search & Discover
# ============================================================================

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_users(request):
    """Search users by username. Query param: ?q=<search term>"""
    query = request.GET.get('q', '').strip()
    if not query:
        return Response([])

    users = User.objects.filter(
        username__icontains=query
    ).exclude(id=request.user.id)[:20]

    results = []
    
    # Pre-fetch current user's friends and pending requests for bulk lookup
    current_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    friend_ids = set(current_profile.friends.values_list('user__id', flat=True))
    
    pending_sent_ids = set(FriendRequest.objects.filter(
        sender=request.user, status='pending'
    ).values_list('receiver_id', flat=True))
    
    pending_received_map = {
        req['sender_id']: req['id'] 
        for req in FriendRequest.objects.filter(receiver=request.user, status='pending').values('sender_id', 'id')
    }

    for u in users:
        profile = UserProfile.objects.filter(user=u).first()
        results.append({
            'id': u.id,
            'username': u.username,
            'display_name': profile.display_name if profile else '',
            'profile_picture': profile.profile_picture if profile else None,
            'is_friend': u.id in friend_ids,
            'pending_sent': u.id in pending_sent_ids,
            'pending_received_id': pending_received_map.get(u.id),
        })
    return Response(results)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def top_users(request):
    """Get users who created the most sidequests (popular sidequest setters)"""
    limit = int(request.GET.get('limit', 10))
    limit = min(limit, 20)

    top = (
        User.objects
        .annotate(sidequest_count=Count('created_sidequests'))
        .filter(sidequest_count__gt=0)
        .order_by('-sidequest_count')[:limit]
    )

    results = []
    
    # Pre-fetch current user's friends and pending requests for bulk lookup
    current_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    friend_ids = set(current_profile.friends.values_list('user__id', flat=True))
    
    pending_sent_ids = set(FriendRequest.objects.filter(
        sender=request.user, status='pending'
    ).values_list('receiver_id', flat=True))
    
    pending_received_map = {
        req['sender_id']: req['id'] 
        for req in FriendRequest.objects.filter(receiver=request.user, status='pending').values('sender_id', 'id')
    }

    for u in top:
        profile = UserProfile.objects.filter(user=u).first()
        results.append({
            'id': u.id,
            'username': u.username,
            'display_name': profile.display_name if profile else '',
            'profile_picture': profile.profile_picture if profile else None,
            'sidequest_count': u.sidequest_count,
            'is_friend': u.id in friend_ids,
            'pending_sent': u.id in pending_sent_ids,
            'pending_received_id': pending_received_map.get(u.id),
        })
    return Response(results)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def discover_feed(request):
    """Get suggested sidequests and trending tags for the discover/search page"""
    # Suggested sidequests — upcoming public ones the user hasn't joined
    suggested_sqs = (
        Sidequest.objects
        .filter(
            post_to_campus_board=True,
            event_datetime__gte=timezone.now(),
            status='upcoming',
        )
        .exclude(creator=request.user)
        .order_by('?')[:10]
    )

    suggested = []
    for sq in suggested_sqs:
        suggested.append({
            'id': sq.id,
            'title': sq.title,
            'description': sq.description,
            'creator_username': sq.creator.username,
            'vibe': sq.vibe,
            'event_datetime': sq.event_datetime.isoformat(),
            'participant_count': sq.participants.filter(status='going').count(),
            'max_people': sq.max_people,
        })

    # Trending tags — vibes with counts
    vibe_counts = (
        Sidequest.objects
        .filter(event_datetime__gte=timezone.now())
        .values('vibe')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    trending = [{'tag': v['vibe'], 'count': v['count']} for v in vibe_counts]

    return Response({
        'suggested_sidequests': suggested,
        'trending_tags': trending,
    })

# def generate_presigned_upload_url(key, content_type):
#     s3 = boto3.client(
#         's3',
#         endpoint_url=os.environ['B2_ENDPOINT'],
#         aws_access_key_id=os.environ['B2_KEY_ID'],
#         aws_secret_access_key=os.environ['B2_APP_KEY'],
#         config=boto3.session.Config(signature_version='s3v4')
#     )
#     presigned_url = s3.generate_presigned_url(
#         ClientMethod='put_object',
#         Params={
#             'Bucket': os.environ['B2_BUCKET'],
#             'Key': key,
#         },
#         ExpiresIn=3600,
#         HttpMethod='PUT'
#     )
#     print("🔹 Presign generation details:")
#     print(f"Key: {key}")
#     print(f"Content-Type: {content_type}")
#     return presigned_url


# def extract_key_from_url(file_url):
#     """
#     Extract S3 key from full Backblaze URL
#     Example: https://s3.us-west-004.backblazeb2.com/bucket-name/users/123/challenges/456/file.jpg
#     Returns: users/123/challenges/456/file.jpg
#     """
#     parsed = urlparse(file_url)
#     path = parsed.path.lstrip('/')
#     bucket_name = os.environ['B2_BUCKET']
#     if path.startswith(f"{bucket_name}/"):
#         return path[len(bucket_name)+1:]
#     return path


# def delete_from_backblaze(key):
#     """Delete object from Backblaze B2 bucket"""
#     try:
#         s3 = boto3.client(
#             's3',
#             endpoint_url=os.environ['B2_ENDPOINT'],
#             aws_access_key_id=os.environ['B2_KEY_ID'],
#             aws_secret_access_key=os.environ['B2_APP_KEY']
#         )
#         s3.delete_object(Bucket=os.environ['B2_BUCKET'], Key=key)
#         return True
#     except Exception as e:
#         print(f"Error deleting file from Backblaze: {key} - {str(e)}")
#         return False


# ============================================================================
# COMMENTED OUT: Proof presign and create views — keep for future sidequest image uploads
# ============================================================================

# class ProofPresignView(APIView):
#     permission_classes = [permissions.IsAuthenticated]
#
#     def post(self, request):
#         challenge_id = request.data.get("challenge_id")
#         filename = request.data.get("filename")
#
#         if not challenge_id or not filename:
#             return Response({"detail": "challenge_id and filename are required"}, status=400)
#
#         try:
#             challenge = Challenge.objects.get(id=challenge_id)
#         except Challenge.DoesNotExist:
#             return Response({"detail": "Challenge not found"}, status=404)
#
#         ext = filename.split('.')[-1].lower()
#         key = f"users/{request.user.id}/challenges/{challenge.id}/proof.{ext}"
#         content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
#
#         presigned_url = generate_presigned_upload_url(key=key, content_type=content_type)
#         file_url = f"{os.environ['B2_ENDPOINT']}/{os.environ['B2_BUCKET']}/{key}"
#
#         return Response({
#             "file_url": file_url,
#             "presigned_url": presigned_url,
#             "content_type": content_type
#         })


# class ProofCreateView(APIView):
#     permission_classes = [IsAuthenticated]
#
#     def post(self, request):
#         serializer = ProofCreateSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         data = serializer.validated_data
#
#         try:
#             challenge = Challenge.objects.get(id=data['challenge_id'])
#         except Challenge.DoesNotExist:
#             return Response({"detail": "Challenge not found"}, status=404)
#
#         proof, created = Proof.objects.update_or_create(
#             user=request.user,
#             challenge=challenge,
#             defaults={
#                 'file': data['file_url'],
#                 'description': data.get('description', ''),
#                 'status': 'pending',
#             }
#         )
#
#         return Response({
#             "id": proof.id,
#             "file_url": proof.file,
#             "submitted_at": proof.submitted_at
#         }, status=201)


# ============================================================================
# COMMENTED OUT: Old challenge/proof/leaderboard/season views
# ============================================================================

# class ChallengeListView(generics.ListAPIView):
#     serializer_class = ChallengeWithProofsSerializer
#     permission_classes = [permissions.AllowAny]
#     def get_queryset(self):
#         return Challenge.objects.filter(
#             is_active=True,
#             start_datetime__lte=timezone.now(),
#             end_datetime__gte=timezone.now()
#         )

# class ChallengeDetailView(generics.RetrieveAPIView):
#     queryset = Challenge.objects.all()
#     serializer_class = ChallengeSerializer
#     permission_classes = [permissions.IsAuthenticated]

# class UserProofsListView(generics.ListAPIView):
#     serializer_class = ProofDetailSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     def get_queryset(self):
#         return Proof.objects.filter(user=self.request.user)

# class ProofDetailView(generics.RetrieveUpdateAPIView):
#     permission_classes = [permissions.IsAuthenticated]
#     def get_queryset(self):
#         if self.request.user.is_staff:
#             return Proof.objects.all()
#         return Proof.objects.filter(user=self.request.user)
#     def get_serializer_class(self):
#         if self.request.user.is_staff and self.request.method in ['PUT', 'PATCH']:
#             return ProofReviewSerializer
#         return ProofDetailSerializer

# class ProofReviewListView(generics.ListAPIView):
#     serializer_class = ProofDetailSerializer
#     permission_classes = [permissions.IsAdminUser]
#     def get_queryset(self):
#         status_filter = self.request.query_params.get('status', 'pending')
#         if status_filter in ['pending', 'approved', 'rejected']:
#             return Proof.objects.filter(status=status_filter)
#         return Proof.objects.all()

# class SeasonView(generics.RetrieveAPIView):
#     serializer_class = SeasonSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     def get_object(self):
#         now = timezone.now()
#         season = Season.objects.filter(start_date__lte=now, end_date__gte=now).first()
#         if not season:
#             raise NotFound("No active season found")
#         return season

# @api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated])
# def challenge_stats(request, challenge_id):
#     challenge = get_object_or_404(Challenge, id=challenge_id)
#     stats = {
#         'challenge': ChallengeSerializer(challenge).data,
#         'total_submissions': challenge.proofs.count(),
#         'pending_reviews': challenge.proofs.filter(status='pending').count(),
#         'approved_submissions': challenge.proofs.filter(status='approved').count(),
#     }
#     return Response(stats)

# @api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated])
# def leaderboard(request):
#     limit = int(request.GET.get('limit', 10))
#     limit = min(limit, 100)
#     for profile in UserProfile.objects.all():
#         profile.update_total_points()
#     profiles = UserProfile.objects.select_related('user').order_by('-total_points')[:limit]
#     leaderboard_data = [
#         {
#             'username': profile.user.username,
#             'total_points': profile.total_points,
#             'university': profile.university,
#             'rank': idx + 1
#         }
#         for idx, profile in enumerate(profiles)
#     ]
#     return Response(leaderboard_data)
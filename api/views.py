from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Challenge, Proof, UserProfile
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import (
    ChallengeSerializer, ChallengeWithProofsSerializer,
    ProofUploadSerializer, ProofDetailSerializer, ProofReviewSerializer,
    UserProfileSerializer, LeaderboardSerializer, ProofCreateSerializer
)

import os
import uuid
import mimetypes
import boto3
import botocore
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


class ChallengeListView(generics.ListAPIView):
    """List all active challenges for today"""
    serializer_class = ChallengeWithProofsSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        """Return active challenges for today's date"""
        today = timezone.now().date()
        return Challenge.objects.filter(
            is_active=True,
            start_datetime__lte=timezone.now(),  
            end_datetime__gte=timezone.now()      
        )
    
class UserProfileView(generics.RetrieveAPIView):
    """Get the profile of the current user"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """Return the profile of the current user"""
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

class ChallengeDetailView(generics.RetrieveAPIView):
    """Get details of a specific challenge"""
    queryset = Challenge.objects.all()
    serializer_class = ChallengeSerializer
    permission_classes = [permissions.IsAuthenticated]

class UserProofsListView(generics.ListAPIView):
    """List all proofs submitted by the current user"""
    serializer_class = ProofDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return user's proofs"""
        return Proof.objects.filter(user=self.request.user)


class ProofDetailView(generics.RetrieveUpdateAPIView):
    """Get or update a specific proof"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return user's proofs or all proofs if staff"""
        if self.request.user.is_staff:
            return Proof.objects.all()
        return Proof.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on user permissions"""
        if self.request.user.is_staff and self.request.method in ['PUT', 'PATCH']:
            return ProofReviewSerializer
        return ProofDetailSerializer


class ProofReviewListView(generics.ListAPIView):
    """List all proofs for review (staff only)"""
    serializer_class = ProofDetailSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        """Return proofs based on status filter"""
        status_filter = self.request.query_params.get('status', 'pending')
        if status_filter in ['pending', 'approved', 'rejected']:
            return Proof.objects.filter(status=status_filter)
        return Proof.objects.all()

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_stats(request):
    """Get current user's statistics"""
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    stats = {
        'total_points': profile.total_points,
        'total_proofs': user.proofs.count(),
        'approved_proofs': user.proofs.filter(status='approved').count(),
        'pending_proofs': user.proofs.filter(status='pending').count(),
        'rejected_proofs': user.proofs.filter(status='rejected').count(),
        'challenges_completed': user.proofs.filter(status='approved').count(),
        'leaderboard_position': UserProfile.objects.filter(
            total_points__gt=profile.total_points
        ).count() + 1,
    }
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def challenge_stats(request, challenge_id):
    """Get statistics for a specific challenge"""
    challenge = get_object_or_404(Challenge, id=challenge_id)
    
    stats = {
        'challenge': ChallengeSerializer(challenge).data,
        'total_submissions': challenge.proofs.count(),
        'pending_reviews': challenge.proofs.filter(status='pending').count(),
        'approved_submissions': challenge.proofs.filter(status='approved').count(),
        'rejection_rate': (
            challenge.proofs.filter(status='rejected').count() / 
            max(challenge.proofs.count(), 1) * 100
        ),
    }
    
    return Response(stats)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def leaderboard(request):
    """
    Get top users ranked by total_points
    Query params:
    - limit: number of users to return (default: 10, max: 100)
    """
    limit = int(request.GET.get('limit', 10))
    limit = min(limit, 100)

    for profile in UserProfile.objects.all():
        profile.update_total_points()

    profiles = UserProfile.objects.select_related('user').order_by('-total_points')[:limit]

    leaderboard_data = [
        {
            'username': profile.user.username,
            'total_points': profile.total_points,
            'university': profile.university,
            'rank': idx + 1
        }
        for idx, profile in enumerate(profiles)
    ]

    return Response(leaderboard_data)



@api_view(['GET'])
def health_check(request):
    """Simple health check endpoint"""
    return Response({"status": "ok", "message": "API is running"})

def generate_presigned_upload_url(key, content_type):
    s3 = boto3.client(
        's3',
        endpoint_url=os.environ['B2_ENDPOINT'],
        aws_access_key_id=os.environ['B2_KEY_ID'],
        aws_secret_access_key=os.environ['B2_APP_KEY'],
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

    print("🔹 Presign generation details:")
    print(f"Key: {key}")
    print(f"Content-Type: {content_type}")

    return presigned_url



class ProofPresignView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        challenge_id = request.data.get("challenge_id")
        filename = request.data.get("filename")

        if not challenge_id or not filename:
            return Response({"detail": "challenge_id and filename are required"}, status=400)

        try:
            challenge = Challenge.objects.get(id=challenge_id)
        except Challenge.DoesNotExist:
            return Response({"detail": "Challenge not found"}, status=404)

        ext = filename.split('.')[-1].lower()
        key = f"proofs/{challenge.id}/{uuid.uuid4().hex}.{ext}"
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

        presigned_url = generate_presigned_upload_url(key=key, content_type=content_type)

        file_url = f"{os.environ['B2_ENDPOINT']}/{os.environ['B2_BUCKET']}/{key}"

        return Response({
            "file_url": file_url,
            "presigned_url": presigned_url,
            "content_type": content_type
        })




class ProofCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProofCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            challenge = Challenge.objects.get(id=data['challenge_id'])
        except Challenge.DoesNotExist:
            return Response({"detail": "Challenge not found"}, status=404)

        proof, created = Proof.objects.update_or_create(
            user=request.user,
            challenge=challenge,
            defaults={
                'file': data['file_url'],
                'description': data.get('description', ''),
                'status': 'pending', 
            }
        )

        return Response({
            "id": proof.id,
            "file_url": proof.file,
            "submitted_at": proof.submitted_at
        }, status=201)
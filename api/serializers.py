from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Sidequest, SidequestParticipant, UserProfile, FriendRequest


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'username']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'user', 'university', 'display_name',
            'bio', 'major', 'class_year', 'profile_picture', 'interests',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class FriendRequestSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_avatar = serializers.URLField(source='sender.profile.profile_picture', read_only=True)
    receiver_username = serializers.CharField(source='receiver.username', read_only=True)

    class Meta:
        model = FriendRequest
        fields = ['id', 'sender_username', 'sender_avatar', 'receiver_username', 'status', 'created_at']


# ============================================================================
# NEW: Sidequest serializers
# ============================================================================

class SidequestParticipantSerializer(serializers.ModelSerializer):
    """Participant details for a sidequest"""
    user = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()

    class Meta:
        model = SidequestParticipant
        fields = ['id', 'user', 'profile', 'status', 'joined_at', 'rating']
        read_only_fields = ['id', 'joined_at']

    def get_user(self, obj):
        return UserSerializer(obj.user).data

    def get_profile(self, obj):
        return UserProfileSerializer(obj.user.profile).data


class SidequestSerializer(serializers.ModelSerializer):
    """Full sidequest serializer for reading"""
    creator = UserSerializer(read_only=True)
    participants = SidequestParticipantSerializer(many=True, read_only=True)
    participant_count = serializers.ReadOnlyField()
    spots_left = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    user_status = serializers.SerializerMethodField()

    class Meta:
        model = Sidequest
        fields = [
            'id', 'title', 'description', 'creator',
            'event_datetime', 'end_datetime', 'location',
            'vibe', 'max_people', 'post_to_campus_board',
            'status', 'participant_count', 'spots_left', 'is_full',
            'participants', 'user_status', 'images',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at']

    def get_user_status(self, obj):
        """Get the current user's participation status for this sidequest"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            participation = obj.participants.filter(user=request.user).first()
            if participation:
                return participation.status
            if obj.creator == request.user:
                return 'creator'
        return None


class SidequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/editing sidequests"""

    class Meta:
        model = Sidequest
        fields = [
            'title', 'description',
            'event_datetime', 'end_datetime', 'location',
            'vibe', 'max_people', 'post_to_campus_board',
        ]

    def create(self, validated_data):
        validated_data['creator'] = self.context['request'].user
        sidequest = super().create(validated_data)
        # Auto-add creator as a participant with 'going' status
        SidequestParticipant.objects.create(
            sidequest=sidequest,
            user=self.context['request'].user,
            status='going',
        )
        return sidequest


# ============================================================================
# COMMENTED OUT: Old proof/challenge serializers — keep for future image uploads
# ============================================================================
# class ChallengeSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Challenge
#         fields = [
#             'id', 'title', 'description', 'points',
#             'start_datetime', 'end_datetime',
#             'is_active', 'allowed_file_types', 'max_file_size_mb',
#             'created_at', 'updated_at'
#         ]
#         read_only_fields = ['id', 'created_at', 'updated_at']
#
# class ChallengeWithProofsSerializer(serializers.ModelSerializer):
#     user_proof = serializers.SerializerMethodField()
#     total_submissions = serializers.SerializerMethodField()
#     class Meta:
#         model = Challenge
#         fields = [
#             'id', 'title', 'description', 'points',
#             'start_datetime', 'end_datetime',
#             'is_active', 'allowed_file_types', 'max_file_size_mb',
#             'created_at', 'user_proof', 'total_submissions'
#         ]
#     def get_user_proof(self, obj):
#         request = self.context.get('request')
#         if request and request.user.is_authenticated:
#             try:
#                 proof = obj.proofs.get(user=request.user)
#                 return ProofDetailSerializer(proof, context=self.context).data
#             except Proof.DoesNotExist:
#                 return None
#         return None
#     def get_total_submissions(self, obj):
#         return obj.proofs.count()
#
# class ProofUploadSerializer(serializers.ModelSerializer):
#     file_size_mb = serializers.ReadOnlyField()
#     file_extension = serializers.ReadOnlyField()
#     user = UserSerializer(read_only=True)
#     challenge = ChallengeSerializer(read_only=True)
#     class Meta:
#         model = Proof
#         fields = [
#             'id', 'user', 'challenge', 'file', 'description',
#             'status', 'submitted_at', 'file_size_mb', 'file_extension'
#         ]
#         read_only_fields = ['id', 'user', 'status', 'submitted_at', 'file_size_mb', 'file_extension']
#     def validate_file(self, value):
#         if not value:
#             raise serializers.ValidationError("No file provided.")
#         max_size = 50 * 1024 * 1024
#         if value.size > max_size:
#             raise serializers.ValidationError(
#                 f"File size cannot exceed 50MB. Your file is {round(value.size / (1024 * 1024), 2)}MB."
#             )
#         allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi', 'pdf']
#         file_extension = value.name.split('.')[-1].lower()
#         if file_extension not in allowed_extensions:
#             raise serializers.ValidationError(
#                 f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
#             )
#         return value
#     def create(self, validated_data):
#         validated_data['user'] = self.context['request'].user
#         return super().create(validated_data)
#
# class ProofDetailSerializer(serializers.ModelSerializer):
#     user = UserSerializer(read_only=True)
#     challenge = ChallengeSerializer(read_only=True)
#     file_size_mb = serializers.ReadOnlyField()
#     file_extension = serializers.ReadOnlyField()
#     reviewed_by = UserSerializer(read_only=True)
#     class Meta:
#         model = Proof
#         fields = [
#             'id', 'user', 'challenge', 'file', 'description',
#             'status', 'submitted_at', 'reviewed_at', 'reviewed_by',
#             'rejection_reason', 'points_awarded', 'file_size_mb', 'file_extension'
#         ]
#         read_only_fields = [
#             'id', 'user', 'challenge', 'file', 'description',
#             'submitted_at', 'reviewed_at', 'reviewed_by', 'file_size_mb', 'file_extension'
#         ]
#
# class ProofReviewSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Proof
#         fields = ['status', 'rejection_reason', 'points_awarded']
#     def validate(self, data):
#         status = data.get('status')
#         rejection_reason = data.get('rejection_reason', '')
#         points_awarded = data.get('points_awarded', 0)
#         if status == 'rejected' and not rejection_reason:
#             raise serializers.ValidationError("Rejection reason is required.")
#         if status == 'approved' and points_awarded <= 0:
#             raise serializers.ValidationError("Points must be greater than 0 when approving.")
#         if status == 'rejected' and points_awarded > 0:
#             raise serializers.ValidationError("Points should be 0 when rejecting.")
#         return data
#     def update(self, instance, validated_data):
#         from django.utils import timezone
#         validated_data['reviewed_at'] = timezone.now()
#         validated_data['reviewed_by'] = self.context['request'].user
#         if validated_data.get('status') == 'approved':
#             instance.user.profile.update_total_points()
#         return super().update(instance, validated_data)
#
# class LeaderboardSerializer(serializers.Serializer):
#     id = serializers.IntegerField(source='user.id')
#     username = serializers.CharField(source='user.username')
#     score = serializers.IntegerField()
#     avatar_url = serializers.URLField(allow_null=True)
#     rank = serializers.IntegerField()
#
# class SeasonSerializer(serializers.ModelSerializer):
#     is_active = serializers.SerializerMethodField()
#     time_remaining = serializers.SerializerMethodField()
#     class Meta:
#         model = Season
#         fields = ["id", "name", "start_date", "end_date", "is_active", "time_remaining"]
#     def get_is_active(self, obj):
#         return obj.is_active()
#     def get_time_remaining(self, obj):
#         return obj.time_remaining().total_seconds()
#
# class ProofCreateSerializer(serializers.Serializer):
#     challenge_id = serializers.IntegerField()
#     file_url = serializers.URLField()
#     description = serializers.CharField(required=False, allow_blank=True)
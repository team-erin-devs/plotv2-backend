from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Challenge, Proof, UserProfile


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
        fields = ['user', 'total_points', 'university', 'student_id', 'created_at']
        read_only_fields = ['total_points', 'created_at']


class ChallengeSerializer(serializers.ModelSerializer):
    """Serializer for Challenge model"""
    class Meta:
        model = Challenge
        fields = [
            'id', 'title', 'description', 'points', 
            'start_date', 'end_date',
            'is_active', 'allowed_file_types', 'max_file_size_mb',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProofUploadSerializer(serializers.ModelSerializer):
    """Serializer for proof upload"""
    file_size_mb = serializers.ReadOnlyField()
    file_extension = serializers.ReadOnlyField()
    user = UserSerializer(read_only=True)
    challenge = ChallengeSerializer(read_only=True)
    
    class Meta:
        model = Proof
        fields = [
            'id', 'user', 'challenge', 'file', 'description', 
            'status', 'submitted_at', 'file_size_mb', 'file_extension'
        ]
        read_only_fields = ['id', 'user', 'status', 'submitted_at', 'file_size_mb', 'file_extension']
    
    def validate_file(self, value):
        """Validate uploaded file"""
        if not value:
            raise serializers.ValidationError("No file provided.")
        
        # Check file size (50MB default limit)
        max_size = 50 * 1024 * 1024  # 50MB in bytes
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size cannot exceed 50MB. Your file is {round(value.size / (1024 * 1024), 2)}MB."
            )
        
        # Check file extension
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'avi', 'pdf']
        file_extension = value.name.split('.')[-1].lower()
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        return value
    
    def create(self, validated_data):
        """Create proof with current user"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ProofDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for proof retrieval"""
    user = UserSerializer(read_only=True)
    challenge = ChallengeSerializer(read_only=True)
    file_size_mb = serializers.ReadOnlyField()
    file_extension = serializers.ReadOnlyField()
    reviewed_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Proof
        fields = [
            'id', 'user', 'challenge', 'file', 'description', 
            'status', 'submitted_at', 'reviewed_at', 'reviewed_by',
            'rejection_reason', 'points_awarded', 'file_size_mb', 'file_extension'
        ]
        read_only_fields = [
            'id', 'user', 'challenge', 'file', 'description', 
            'submitted_at', 'reviewed_at', 'reviewed_by', 'file_size_mb', 'file_extension'
        ]


class ProofReviewSerializer(serializers.ModelSerializer):
    """Serializer for reviewing proofs (admin/staff only)"""
    class Meta:
        model = Proof
        fields = ['status', 'rejection_reason', 'points_awarded']
    
    def validate(self, data):
        """Validate review data"""
        status = data.get('status')
        rejection_reason = data.get('rejection_reason', '')
        points_awarded = data.get('points_awarded', 0)
        
        if status == 'rejected' and not rejection_reason:
            raise serializers.ValidationError(
                "Rejection reason is required when rejecting a proof."
            )
        
        if status == 'approved' and points_awarded <= 0:
            raise serializers.ValidationError(
                "Points must be greater than 0 when approving a proof."
            )
        
        if status == 'rejected' and points_awarded > 0:
            raise serializers.ValidationError(
                "Points should be 0 when rejecting a proof."
            )
        
        return data
    
    def update(self, instance, validated_data):
        """Update proof with review information"""
        from django.utils import timezone
        
        validated_data['reviewed_at'] = timezone.now()
        validated_data['reviewed_by'] = self.context['request'].user
        
        # Update user's total points if approved
        if validated_data.get('status') == 'approved':
            instance.user.profile.update_total_points()
        
        return super().update(instance, validated_data)


class ChallengeWithProofsSerializer(serializers.ModelSerializer):
    """Serializer for challenges with user's proof status"""
    user_proof = serializers.SerializerMethodField()
    total_submissions = serializers.SerializerMethodField()
    
    class Meta:
        model = Challenge
        fields = [
            'id', 'title', 'description', 'points', 
            'start_date', 'end_date',  
            'is_active', 'allowed_file_types', 'max_file_size_mb',
            'created_at', 'user_proof', 'total_submissions'
        ]
    
    def get_user_proof(self, obj):
        """Get user's proof for this challenge if exists"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                proof = obj.proofs.get(user=request.user)
                return ProofDetailSerializer(proof, context=self.context).data
            except Proof.DoesNotExist:
                return None
        return None
    
    def get_total_submissions(self, obj):
        """Get total number of submissions for this challenge"""
        return obj.proofs.count()
from .models import UserProfile

class LeaderboardSerializer(serializers.Serializer):
    """Serializer for leaderboard entries"""
    id = serializers.IntegerField(source='user.id')
    username = serializers.CharField(source='user.username')
    score = serializers.IntegerField()
    avatar_url = serializers.URLField(allow_null=True)
    rank = serializers.IntegerField()

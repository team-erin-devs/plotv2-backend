from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
import os
import uuid
from django.utils import timezone
import pytz

def proof_upload_path(instance, filename):
    """Generate upload path for proof files"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('proofs', str(instance.challenge.id), filename)

def default_allowed_file_types():
    """Default list of allowed image/video file types"""
    return [
        # Common image formats
        'jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif', 'bmp',

        # Common video formats
        'mp4', 'mov', 'avi', 'mkv', 'webm',
    ]


class Challenge(models.Model):
    """Weekly challenges that users can complete"""

    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    points = models.PositiveIntegerField(default=10)

    start_datetime = models.DateTimeField(default=timezone.now)
    end_datetime = models.DateTimeField(null=True, blank=True)

    difficulty = models.CharField(
        max_length=10,
        choices=DIFFICULTY_CHOICES,
        default='medium'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # File requirements for proof submission
    allowed_file_types = models.JSONField(
        default=default_allowed_file_types,
        help_text="List of allowed file extensions (e.g., images or short videos)"
    )
    max_file_size_mb = models.PositiveIntegerField(
        default=50,
        help_text="Maximum file size in MB"
    )

    class Meta:
        ordering = ['-start_datetime', '-created_at']

    def __str__(self):
        est = pytz.timezone('America/New_York')
        local_time = self.start_datetime.astimezone(est)
        return f"{local_time.strftime('%Y-%m-%d %I:%M %p %Z')} - {self.title}"



class Proof(models.Model):
    """Proof submissions from users for challenges"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='proofs')
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='proofs')
    file = models.URLField(max_length=500)
    description = models.TextField(blank=True, help_text="Optional description of the proof")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reviewed_proofs'
    )
    rejection_reason = models.TextField(blank=True, help_text="Reason for rejection if applicable")
    points_awarded = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-submitted_at']
        unique_together = ['user', 'challenge']  # One proof per user per challenge
    
    def __str__(self):
        return f"{self.user.username} - {self.challenge.title} ({self.status})"
    
    @property
    def file_size_mb(self):
        """Get file size in MB"""
        if self.file:
            return round(self.file.size / (1024 * 1024), 2)
        return 0
    
    @property
    def file_extension(self):
        """Get file extension"""
        if self.file:
            return os.path.splitext(self.file.name)[1].lower().lstrip('.')
        return None


class UserProfile(models.Model):
    """Extended user profile for challenge app"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    total_points = models.PositiveIntegerField(default=0)
    university = models.CharField(max_length=200, blank=True)
    student_id = models.CharField(max_length=50, blank=True)
    
    # Profile details
    bio = models.TextField(blank=True, max_length=500, help_text="User bio/description")
    major = models.CharField(max_length=100, blank=True, help_text="Major/field of study")
    class_year = models.CharField(max_length=50, blank=True, help_text="Class year (e.g., 'Class of '27')")
    profile_picture = models.URLField(blank=True, max_length=500, help_text="URL to profile picture")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def update_total_points(self):
        """Update total points from approved proofs"""
        self.total_points = sum(
            proof.points_awarded 
            for proof in self.user.proofs.filter(status='approved')
        )
        self.save()


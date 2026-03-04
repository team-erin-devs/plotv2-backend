from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
import os
import uuid
from django.utils import timezone
from datetime import timedelta
import pytz

# ============================================================================
# COMMENTED OUT: Proof upload utilities — keep for future sidequest image logs
# ============================================================================
# def proof_upload_path(instance, filename):
#     """Generate upload path for proof files"""
#     ext = filename.split('.')[-1]
#     filename = f"{uuid.uuid4()}.{ext}"
#     return os.path.join('proofs', str(instance.challenge.id), filename)
#
# def default_allowed_file_types():
#     """Default list of allowed image/video file types"""
#     return [
#         # Common image formats
#         'jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif', 'bmp',
#         # Common video formats
#         'mp4', 'mov', 'avi', 'mkv', 'webm',
#     ]


# ============================================================================
# COMMENTED OUT: Challenge model — replaced by Sidequest
# ============================================================================
# class Challenge(models.Model):
#     """Weekly challenges that users can complete"""
#     DIFFICULTY_CHOICES = [
#         ('easy', 'Easy'),
#         ('medium', 'Medium'),
#         ('hard', 'Hard'),
#     ]
#     title = models.CharField(max_length=200)
#     description = models.TextField()
#     points = models.PositiveIntegerField(default=10)
#     start_datetime = models.DateTimeField(default=timezone.now)
#     end_datetime = models.DateTimeField(null=True, blank=True)
#     difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     allowed_file_types = models.JSONField(
#         default=default_allowed_file_types,
#         help_text="List of allowed file extensions"
#     )
#     max_file_size_mb = models.PositiveIntegerField(default=50)
#     class Meta:
#         ordering = ['-start_datetime', '-created_at']
#     def __str__(self):
#         est = pytz.timezone('America/New_York')
#         local_time = self.start_datetime.astimezone(est)
#         return f"{local_time.strftime('%Y-%m-%d %I:%M %p %Z')} - {self.title}"

# ============================================================================
# COMMENTED OUT: Season model — not needed for sidequests
# ============================================================================
# class Season(models.Model):
#     name = models.CharField(max_length=100, unique=True)
#     start_date = models.DateTimeField()
#     end_date = models.DateTimeField()
#     def is_active(self):
#         now = timezone.now()
#         return self.start_date <= now <= self.end_date
#     def time_remaining(self):
#         now = timezone.now()
#         remaining = self.end_date - now
#         return max(remaining, timezone.timedelta(seconds=0))
#     def __str__(self):
#         return self.name

# ============================================================================
# COMMENTED OUT: Proof model — keep for future sidequest image log feature
# ============================================================================
# class Proof(models.Model):
#     """Proof submissions from users for challenges"""
#     STATUS_CHOICES = [
#         ('pending', 'Pending Review'),
#         ('approved', 'Approved'),
#         ('rejected', 'Rejected'),
#     ]
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='proofs')
#     challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='proofs')
#     file = models.URLField(max_length=500)
#     description = models.TextField(blank=True)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
#     submitted_at = models.DateTimeField(auto_now_add=True)
#     reviewed_at = models.DateTimeField(null=True, blank=True)
#     reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_proofs')
#     rejection_reason = models.TextField(blank=True)
#     points_awarded = models.PositiveIntegerField(default=0)
#     class Meta:
#         ordering = ['-submitted_at']
#         unique_together = ['user', 'challenge']
#     def __str__(self):
#         return f"{self.user.username} - {self.challenge.title} ({self.status})"
#     @property
#     def file_size_mb(self):
#         if self.file:
#             return round(self.file.size / (1024 * 1024), 2)
#         return 0
#     @property
#     def file_extension(self):
#         if self.file:
#             return os.path.splitext(self.file.name)[1].lower().lstrip('.')
#         return None


# ============================================================================
# NEW: Sidequest model
# ============================================================================
class Sidequest(models.Model):
    """A spontaneous hangout/activity that friends can join"""

    VIBE_CHOICES = [
        ('chill', 'Chill'),
        ('active', 'Active'),
        ('social', 'Social'),
        ('fun', 'Fun'),
        ('productive', 'Productive'),
    ]

    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_sidequests')

    event_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)

    vibe = models.CharField(max_length=20, choices=VIBE_CHOICES, default='chill')
    max_people = models.PositiveIntegerField(default=5)
    post_to_campus_board = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    
    # Store URLs to uploaded images for this sidequest
    images = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-event_datetime']

    def __str__(self):
        est = pytz.timezone('America/New_York')
        local_time = self.event_datetime.astimezone(est)
        return f"{self.title} — {local_time.strftime('%b %d, %I:%M %p')}"

    @property
    def participant_count(self):
        return self.participants.filter(status='going').count()

    @property
    def is_full(self):
        return self.participant_count >= self.max_people

    @property
    def spots_left(self):
        return max(0, self.max_people - self.participant_count)


# ============================================================================
# NEW: SidequestParticipant model
# ============================================================================
class SidequestParticipant(models.Model):
    """Tracks who has joined a sidequest"""

    STATUS_CHOICES = [
        ('invited', 'Invited'),
        ('going', 'Going'),
        ('declined', 'Declined'),
    ]

    sidequest = models.ForeignKey(Sidequest, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sidequest_participations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='going')
    joined_at = models.DateTimeField(auto_now_add=True)
    
    # Rating 1-5 for completed sidequests
    rating = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ['sidequest', 'user']
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.user.username} → {self.sidequest.title} ({self.status})"


# ============================================================================
# KEPT: FriendRequest model (unchanged)
# ============================================================================
class FriendRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_friend_requests')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_friend_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['sender', 'receiver'] # Prevent duplicate requests

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username} ({self.status})"


# ============================================================================
# KEPT: UserProfile model (removed total_points and student_id)
# ============================================================================
class UserProfile(models.Model):
    """Extended user profile"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    university = models.CharField(max_length=200, blank=True)
    display_name = models.CharField(max_length=100, blank=True, help_text="Display name shown on profile (e.g. 'Noah')")
    
    # Profile details
    bio = models.TextField(blank=True, max_length=500, help_text="User bio/description")
    major = models.CharField(max_length=100, blank=True, help_text="Major/field of study")
    class_year = models.CharField(max_length=50, blank=True, help_text="Class year (e.g., 'Class of '27')")
    profile_picture = models.URLField(blank=True, max_length=500, help_text="URL to profile picture")
    interests = models.JSONField(default=list, blank=True, help_text="List of user interests (e.g., [{'emoji': '🏀', 'label': 'basketball'}])")

    friends = models.ManyToManyField('self', blank=True, symmetrical=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

import boto3
import os
from django.utils.html import format_html
from django.contrib import admin
from .models import Sidequest, SidequestParticipant, UserProfile, FriendRequest


# ============================================================================
# COMMENTED OUT: Presigned URL helper — keep for future sidequest image viewing
# ============================================================================
# def generate_presigned_download_url(file_url, expires_in=300):
#     """Generate a temporary presigned URL for viewing/downloading"""
#     from botocore.config import Config
#     s3 = boto3.client(
#         's3',
#         endpoint_url=os.environ['B2_ENDPOINT'],
#         aws_access_key_id=os.environ['B2_KEY_ID'],
#         aws_secret_access_key=os.environ['B2_APP_KEY'],
#         config=Config(signature_version='s3v4')
#     )
#     if file_url.startswith('http'):
#         parts = file_url.split('/')
#         key = '/'.join(parts[4:])
#     else:
#         key = file_url
#     bucket_name = os.environ['B2_BUCKET']
#     try:
#         presigned_url = s3.generate_presigned_url(
#             'get_object',
#             Params={'Bucket': bucket_name, 'Key': key},
#             ExpiresIn=expires_in
#         )
#         return presigned_url
#     except Exception as e:
#         print(f"Error generating presigned URL: {e}")
#         raise


# ============================================================================
# NEW: Sidequest Admin
# ============================================================================

class SidequestParticipantInline(admin.TabularInline):
    model = SidequestParticipant
    extra = 0
    readonly_fields = ['joined_at']
    fields = ['user', 'status', 'joined_at']


@admin.register(Sidequest)
class SidequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'creator', 'event_datetime', 'vibe', 'participant_count_display',
                    'max_people', 'post_to_campus_board', 'status', 'created_at']
    list_filter = ['status', 'vibe', 'post_to_campus_board', 'event_datetime']
    search_fields = ['title', 'description', 'creator__username']
    ordering = ['-event_datetime']
    inlines = [SidequestParticipantInline]

    fieldsets = (
        ('Sidequest Info', {
            'fields': ('title', 'description', 'creator', 'vibe', 'status')
        }),
        ('When & Where', {
            'fields': ('event_datetime', 'location')
        }),
        ('Capacity & Visibility', {
            'fields': ('max_people', 'post_to_campus_board'),
        }),
    )

    def participant_count_display(self, obj):
        count = obj.participant_count
        return f"{count}/{obj.max_people}"
    participant_count_display.short_description = 'Participants'


# ============================================================================
# COMMENTED OUT: Old ChallengeAdmin, ProofAdmin, SeasonAdmin
# ============================================================================

# @admin.register(Challenge)
# class ChallengeAdmin(admin.ModelAdmin):
#     list_display = ['title', 'start_datetime', 'end_datetime', 'points', 'difficulty', 'is_active', 'created_at']
#     list_filter = ['is_active', 'difficulty', 'start_datetime', 'created_at']
#     search_fields = ['title', 'description']
#     ordering = ['-start_datetime', '-created_at']
#     fieldsets = (
#         ('Basic Information', {
#             'fields': ('title', 'description', 'points', 'difficulty', 'is_active')
#         }),
#         ('Schedule', {
#             'fields': ('start_datetime', 'end_datetime'),
#         }),
#         ('File Requirements', {
#             'fields': ('allowed_file_types', 'max_file_size_mb'),
#         }),
#     )

# @admin.register(Season)
# class SeasonAdmin(admin.ModelAdmin):
#     list_display = ("name", "start_date", "end_date", "is_active", "time_remaining_display")
#     fields = ("name", "start_date", "end_date")
#     def time_remaining_display(self, obj):
#         return obj.time_remaining()
#     time_remaining_display.short_description = "Time Remaining"

# @admin.register(Proof)
# class ProofAdmin(admin.ModelAdmin):
#     list_display = ['user', 'challenge', 'status', 'points_awarded', 'submitted_at', 'reviewed_by', 'view_proof_button']
#     list_filter = ['status', 'submitted_at', 'reviewed_at', 'challenge__start_datetime']
#     search_fields = ['user__username', 'user__email', 'challenge__title']
#     readonly_fields = ['submitted_at', 'file_size_mb', 'file_extension', 'proof_preview']
#     ordering = ['-submitted_at']
#     fieldsets = (
#         ('Submission Details', {
#             'fields': ('user', 'challenge', 'file', 'proof_preview', 'description', 'submitted_at'),
#         }),
#         ('Review Information', {
#             'fields': ('status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 'points_awarded'),
#         }),
#         ('File Information', {
#             'fields': ('file_size_mb', 'file_extension'),
#             'classes': ('collapse',)
#         }),
#     )
#     def view_proof_button(self, obj):
#         try:
#             url = generate_presigned_download_url(obj.file)
#             return format_html(
#                 '<a href="{}" target="_blank" class="button" style="padding: 5px 10px; background-color: #417690; color: white; text-decoration: none; border-radius: 4px;">View Proof</a>',
#                 url
#             )
#         except Exception as e:
#             return format_html('<span style="color: red;">Error: {}</span>', str(e))
#     view_proof_button.short_description = 'Proof'
#     def proof_preview(self, obj):
#         try:
#             url = generate_presigned_download_url(obj.file, expires_in=600)
#             return format_html(
#                 '<a href="{}" target="_blank">🔗 Click here to view proof file</a><br><small>Link expires in 10 minutes</small>',
#                 url
#             )
#         except Exception as e:
#             return format_html('<span style="color: red;">Error: {}</span>', str(e))
#     proof_preview.short_description = 'View Proof File'
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related('user', 'challenge', 'reviewed_by')
#     def save_model(self, request, obj, form, change):
#         if change:
#             previous = Proof.objects.get(pk=obj.pk)
#             if obj.status == 'approved' and previous.status != 'approved':
#                 profile, _ = UserProfile.objects.get_or_create(user=obj.user)
#                 points_to_award = obj.challenge.points if hasattr(obj.challenge, 'points') else 1
#                 profile.total_points += points_to_award
#                 profile.save()
#                 obj.points_awarded = points_to_award
#         super().save_model(request, obj, form, change)


# ============================================================================
# KEPT: UserProfile Admin (simplified, removed points)
# ============================================================================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'university', 'major', 'class_year', 'created_at']
    list_filter = ['university', 'created_at']
    search_fields = ['user__username', 'user__email', 'university']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'university', 'bio', 'major', 'class_year', 'profile_picture')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ['sender', 'receiver', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['sender__username', 'receiver__username']

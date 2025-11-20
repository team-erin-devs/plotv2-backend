import boto3
import os
from django.utils.html import format_html
from django.contrib import admin
from .models import Challenge, Proof, UserProfile

def generate_presigned_download_url(file_url, expires_in=300):
    """Generate a temporary presigned URL for viewing/downloading"""
    import boto3
    from botocore.config import Config
    
    s3 = boto3.client(
        's3',
        endpoint_url=os.environ['B2_ENDPOINT'],
        aws_access_key_id=os.environ['B2_KEY_ID'],
        aws_secret_access_key=os.environ['B2_APP_KEY'],
        config=Config(signature_version='s3v4')  # Force S3v4 signature
    )
    
    # Extract the key from the full URL
    if file_url.startswith('http'):
        # From: https://s3.us-east-005.backblazeb2.com/plotd-bucket/proofs/5/file.png
        # To: proofs/5/file.png
        parts = file_url.split('/')
        key = '/'.join(parts[4:])  # Skip https:, '', domain, bucket
    else:
        key = file_url
    
    bucket_name = os.environ['B2_BUCKET']
    
    try:
        presigned_url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': key,
            },
            ExpiresIn=expires_in
        )
        return presigned_url
    except Exception as e:
        print(f"Error generating presigned URL: {e}")
        raise

@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_datetime', 'end_datetime', 'points', 'difficulty', 'is_active', 'created_at']
    list_filter = ['is_active', 'difficulty', 'start_datetime', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['-start_datetime', '-created_at']
   
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'points', 'difficulty', 'is_active')
        }),
        ('Schedule', {
            'fields': ('start_datetime', 'end_datetime'),
            'description': 'Set when this challenge is active. Leave end_datetime blank for single-day challenges.'
        }),
        ('File Requirements', {
            'fields': ('allowed_file_types', 'max_file_size_mb'),
            'description': 'Configure what types of files users can upload for this challenge'
        }),
    )


@admin.register(Proof)
class ProofAdmin(admin.ModelAdmin):
    list_display = ['user', 'challenge', 'status', 'points_awarded', 'submitted_at', 'reviewed_by', 'view_proof_button']
    list_filter = ['status', 'submitted_at', 'reviewed_at', 'challenge__start_datetime']
    search_fields = ['user__username', 'user__email', 'challenge__title']
    readonly_fields = ['submitted_at', 'file_size_mb', 'file_extension', 'proof_preview']
    ordering = ['-submitted_at']
    
    fieldsets = (
        ('Submission Details', {
            'fields': ('user', 'challenge', 'file', 'proof_preview', 'description', 'submitted_at'),
            'description': 'proof'
        }),
        ('Review Information', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 'points_awarded'),
            'description': 'Only staff members can review and approve/reject proofs'
        }),
        ('File Information', {
            'fields': ('file_size_mb', 'file_extension'),
            'classes': ('collapse',)
        }),
    )
    
    def view_proof_button(self, obj):
        """Button in list view to open proof in new tab"""
        try:
            url = generate_presigned_download_url(obj.file)
            return format_html(
                '<a href="{}" target="_blank" class="button" style="padding: 5px 10px; background-color: #417690; color: white; text-decoration: none; border-radius: 4px; display: inline-block;">View Proof</a>',
                url
            )
        except Exception as e:
            return format_html('<span style="color: red;">Error: {}</span>', str(e))

    view_proof_button.short_description = 'Proof'
    
    def proof_preview(self, obj):
        """Show clickable link in the detail view"""
        try:
            url = generate_presigned_download_url(obj.file, expires_in=600)  # 10 min for detail view
            return format_html(
                '<a href="{}" target="_blank" style="font-size: 14px; color: #417690;">🔗 Click here to view proof file</a><br><small style="color: #666;">Link expires in 10 minutes</small>',
                url
            )
        except Exception as e:
            return format_html('<span style="color: red;">Error generating preview: {}</span>', str(e))
    
    proof_preview.short_description = 'View Proof File'
    
    def get_queryset(self, request):
        """Optimize queries for admin list view"""
        return super().get_queryset(request).select_related('user', 'challenge', 'reviewed_by')
    
    def save_model(self, request, obj, form, change):
        """Automatically award points if proof is approved"""
        if change:  # only if updating an existing proof
            previous = Proof.objects.get(pk=obj.pk)
            # Only award points if status changed to 'approved' and points haven't been given yet
            if obj.status == 'approved' and previous.status != 'approved':
                # Award points to user
                profile, _ = UserProfile.objects.get_or_create(user=obj.user)
                points_to_award = obj.challenge.points if hasattr(obj.challenge, 'points') else 1
                profile.total_points += points_to_award
                profile.save()
                
                # Store awarded points in the proof record
                obj.points_awarded = points_to_award

        super().save_model(request, obj, form, change)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_points', 'university', 'student_id', 'created_at']
    list_filter = ['university', 'created_at']
    search_fields = ['user__username', 'user__email', 'university', 'student_id']
    ordering = ['-total_points']
    readonly_fields = ['created_at', 'total_points']
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'university', 'student_id')
        }),
    )
   
    def get_queryset(self, request):
        """Optimize queries for admin list view"""
        return super().get_queryset(request).select_related('user')
    

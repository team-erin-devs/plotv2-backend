from django.contrib import admin
from .models import Challenge, Proof, UserProfile


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ['title', 'week_number', 'points', 'is_active', 'created_at']
    list_filter = ['is_active', 'week_number', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['-week_number', '-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'points', 'week_number', 'is_active')
        }),
        ('File Requirements', {
            'fields': ('allowed_file_types', 'max_file_size_mb'),
            'description': 'Configure what types of files users can upload for this challenge'
        }),
    )


@admin.register(Proof)
class ProofAdmin(admin.ModelAdmin):
    list_display = ['user', 'challenge', 'status', 'points_awarded', 'submitted_at', 'reviewed_by']
    list_filter = ['status', 'submitted_at', 'reviewed_at', 'challenge__week_number']
    search_fields = ['user__username', 'user__email', 'challenge__title']
    readonly_fields = ['submitted_at', 'file_size_mb', 'file_extension']
    ordering = ['-submitted_at']
    
    fieldsets = (
        ('Submission Details', {
            'fields': ('user', 'challenge', 'file', 'description', 'submitted_at')
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
    
    def get_queryset(self, request):
        """Optimize queries for admin list view"""
        return super().get_queryset(request).select_related('user', 'challenge', 'reviewed_by')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_points', 'university', 'student_id', 'created_at']
    list_filter = ['university', 'created_at']
    search_fields = ['user__username', 'user__email', 'university', 'student_id']
    ordering = ['-total_points']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'university', 'student_id')
        }),
        ('Stats', {
            'fields': ('total_points', 'created_at'),
            'description': 'Total points are automatically calculated from approved proofs'
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries for admin list view"""
        return super().get_queryset(request).select_related('user')

from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'score', 'avatar_url')
    list_filter = ('score',)
    search_fields = ('user__username',)
    ordering = ('-score',)

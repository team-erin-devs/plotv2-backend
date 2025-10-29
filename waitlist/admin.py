from django.contrib import admin
from .models import WaitlistEntry

@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at')  # columns to show
    search_fields = ('name', 'email')  # searchable by name/email
    ordering = ('-created_at',)  # newest entries first

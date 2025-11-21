from django.shortcuts import render
from rest_framework import generics, permissions
from .models import WaitlistEntry
from .serializers import WaitlistEntrySerializer

class WaitlistCreateView(generics.CreateAPIView):
    queryset = WaitlistEntry.objects.all()
    serializer_class = WaitlistEntrySerializer
    permission_classes = [permissions.IsAuthenticated]  # require token
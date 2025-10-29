from django.urls import path
from .views import WaitlistCreateView

urlpatterns = [
    path('waitlist/', WaitlistCreateView.as_view(), name='waitlist-create'),
]

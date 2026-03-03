import os
import django
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from api.models import User, Sidequest

# Get or create a couple users
u1, _ = User.objects.get_or_create(username='moonmoon', email='moon@test.com', defaults={'first_name': 'Moon', 'password': 'test'})
u2, _ = User.objects.get_or_create(username='erinzhangg', email='erin@test.com', defaults={'first_name': 'Erin', 'password': 'test'})
u3, _ = User.objects.get_or_create(username='steven', email='steven@test.com', defaults={'first_name': 'Steven', 'password': 'test'})

now = timezone.now()
today = now.replace(hour=14, minute=0, second=0, microsecond=0)
tomorrow = today + timedelta(days=1)
yesterday = today - timedelta(days=1)

# Yesterday quest
Sidequest.objects.create(
    title="late night ramen",
    description="Getting ramen after studying.",
    creator=u1,
    vibe="chill",
    event_datetime=yesterday + timedelta(hours=6),
    end_datetime=yesterday + timedelta(hours=8),
    location="Ramen Isshin, downtown",
    max_people=4,
    post_to_campus_board=True
)

# Today quests
Sidequest.objects.create(
    title="coffee run and study session",
    description="Need to grind some leetcode. Join me!",
    creator=u1,
    vibe="productive",
    event_datetime=today - timedelta(hours=1), # If they want to see it now
    end_datetime=today + timedelta(hours=2),
    location="De mello, downtown kingston",
    max_people=5,
    post_to_campus_board=True
)

Sidequest.objects.create(
    title="gym sesh (push day)",
    description="Hitting chest and triceps. Beginners welcome.",
    creator=u2,
    vibe="active",
    event_datetime=today + timedelta(hours=4),
    end_datetime=today + timedelta(hours=5),
    location="ARC",
    max_people=3,
    post_to_campus_board=True
)

# Tomorrow quests
Sidequest.objects.create(
    title="thrift shopping",
    description="Looking for some vintage stuff.",
    creator=u3,
    vibe="social",
    event_datetime=tomorrow + timedelta(hours=2),
    end_datetime=tomorrow + timedelta(hours=5),
    location="Value Village",
    max_people=4,
    post_to_campus_board=True
)

print('Successfully populated dummy sidequests!')

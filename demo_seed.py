import os
import django
import sys
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from django.contrib.auth.models import User
from api.models import UserProfile, Sidequest, SidequestParticipant, FriendRequest

def seed_demo():
    print("Clearing database...")
    User.objects.filter(is_superuser=False).delete()
    
    print("Creating users...")
    users_data = [
        {"username": "erinthepm", "first_name": "Erin", "password": "password123", "display": "Erin", "bio": "do it for the plot", "interests": [{"emoji": "🍽️", "label": "food"}, {"emoji": "✈️", "label": "travelling"}, {"emoji": "🐶", "label": "dogs"}]},
        {"username": "lucas", "first_name": "Lucas", "password": "password123", "display": "Lucas", "bio": "outdoorsy", "interests": [{"emoji": "🏔️", "label": "hiking"}]},
        {"username": "jina", "first_name": "Jina", "password": "password123", "display": "Jina", "bio": "coffee enthusiast", "interests": [{"emoji": "☕", "label": "coffee"}]},
        {"username": "jessica", "first_name": "Jessica", "password": "password123", "display": "Jessica", "bio": "designer", "interests": [{"emoji": "�", "label": "art"}]},
    ]

    user_objs = {}
    for data in users_data:
        u = User.objects.create_user(
            username=data["username"],
            first_name=data["first_name"],
            password=data["password"]
        )
        
        try:
            profile = u.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=u)

        profile.display_name = data["display"]
        profile.bio = data["bio"]
        profile.interests = data["interests"]
        profile.profile_picture = f"images/profiles/{data['first_name'].lower()}.png"
        profile.save()
        user_objs[data["username"]] = u
        print(f"Created user: {data['username']} / {data['password']}")

    erin = user_objs["erinthepm"]
    lucas = user_objs["lucas"]
    jina = user_objs["jina"]
    jessica = user_objs["jessica"]

    print("Setting up friendships...")
    # Erin is not friends with everyone now
    erin.profile.friends.add(jina.profile)
    erin.profile.friends.add(lucas.profile)

    lucas.profile.friends.add(jessica.profile)
    jessica.profile.friends.add(jina.profile)

    now = timezone.now()

    print("Creating past sidequests...")
    past_sqs = [
        {
            "title": "shawarma dubai social",
            "creator": lucas,
            "event_date": now - timedelta(days=5),
            "vibe": "social",
            "images": ["images/past/shawarma.png"],
            "participants": [erin, lucas, jessica]
        },
        {
            "title": "coffee run and study session",
            "creator": lucas,
            "event_date": now - timedelta(days=8),
            "vibe": "productive",
            "images": [], # Sticky Note style empty array
            "participants": [erin, lucas]
        },
        {
            "title": "pitch your friend night",
            "creator": jessica,
            "event_date": now - timedelta(days=10),
            "vibe": "fun",
            "images": ["images/past/pitch.png"],
            "participants": [erin, jessica, jina]
        },
        {
            "title": "late night mcdonalds run",
            "creator": lucas,
            "event_date": now - timedelta(days=12),
            "vibe": "social",
            "images": [], # Sticky Note style empty array
            "participants": [erin, jessica, lucas]
        },
        {
            "title": "team social!",
            "creator": jina,
            "event_date": now - timedelta(days=15),
            "vibe": "chill",
            "images": ["images/past/whoaaa.png"],
            "participants": [erin, jina, lucas]
        },
        {
            "title": "pho pho pho",
            "creator": erin,
            "event_date": now - timedelta(days=2),
            "vibe": "social", 
            "images": ["images/past/pho.png"],
            "participants": [erin, jina, lucas]
        }
    ]

    for sq_data in past_sqs:
        vibe_val = sq_data['vibe'] if sq_data['vibe'] in dict(Sidequest.VIBE_CHOICES) else 'social'
        sq = Sidequest.objects.create(
            title=sq_data["title"],
            description="A great time was had by all.",
            creator=sq_data["creator"],
            event_datetime=sq_data["event_date"],
            end_datetime=sq_data["event_date"] + timedelta(hours=2),
            location="Campus",
            vibe=vibe_val,
            max_people=10,
            status='completed',
            images=sq_data["images"]
        )
        for p in sq_data["participants"]:
            # Make sure Erin hasn't rated past sidequests yet
            rating = None if p == erin else 4
            SidequestParticipant.objects.create(
                sidequest=sq, user=p, status='going', rating=rating
            )

    print("Creating future sidequests...")

    # We use simple timedeltas from `base_now` so they are guaranteed to format correctly
    # on the frontend's local device without UTC crossover issues.
    base_now = timezone.now()
    
    # Needs to be today, so within the next 2-4 hours. 
    today_sq_1 = base_now + timedelta(minutes=30)
    today_sq_2 = base_now + timedelta(hours=2)
    
    tomorrow_sq_1 = base_now + timedelta(days=1, hours=1)
    tomorrow_sq_2 = base_now + timedelta(days=1, hours=4)

    future_sqs = [
        {
            "title": "Movie Night: Dune 2",
            "creator": lucas,
            "event_date": today_sq_1,
            "vibe": "chill",
            "location": "Lucas's Place",
            "post_to_campus_board": False,
            "participants": [lucas, erin, jina] # Erin joined this one
        },
        {
            "title": "Hackathon Brainstorm",
            "creator": jina,
            "event_date": today_sq_2,
            "vibe": "productive",
            "location": "Library",
            "post_to_campus_board": True, # Public
            "participants": [jina, jessica] # Erin is NOT in this one (CAN JOIN TODAY)
        },
        {
            "title": "Morning Run",
            "creator": jessica,
            "event_date": tomorrow_sq_1,
            "vibe": "active",
            "location": "Track",
            "post_to_campus_board": True, # Public
            "participants": [jessica, lucas] # Erin is NOT in this one (CAN JOIN TOMORROW)
        },
        {
            "title": "Boba Run",
            "creator": jina,
            "event_date": tomorrow_sq_2,
            "vibe": "social",
            "location": "Downtown",
            "post_to_campus_board": False,
            "participants": [jina, lucas] # Erin is NOT in this one (CAN JOIN TOMORROW)
        }
    ]

    for sq_data in future_sqs:
        sq = Sidequest.objects.create(
            title=sq_data["title"],
            description="Let's do this!",
            creator=sq_data["creator"],
            event_datetime=sq_data["event_date"],
            end_datetime=sq_data["event_date"] + timedelta(hours=2),
            location=sq_data["location"],
            vibe=sq_data["vibe"],
            max_people=10,
            post_to_campus_board=sq_data.get("post_to_campus_board", False),
            status='upcoming'
        )
        for p in sq_data["participants"]:
            SidequestParticipant.objects.create(
                sidequest=sq, user=p, status='going'
            )

    print("Done! Demo database seeded.")

if __name__ == "__main__":
    seed_demo()
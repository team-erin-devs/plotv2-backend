from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import UserProfile

class Command(BaseCommand):
    help = 'Seed database with sample leaderboard data'

    def handle(self, *args, **kwargs):
        # Sample users with scores
        users_data = [
            ('AlexRunner', 2500),
            ('SarahFit', 2350),
            ('MikeChallenger', 2100),
            ('EmilyActive', 1950),
            ('DavidWarrior', 1800),
            ('LisaChamp', 1650),
            ('JohnHero', 1500),
            ('MaryStrong', 1350),
            ('TomBrave', 1200),
            ('JaneQuick', 1050),
        ]

        self.stdout.write('Creating sample users...')
        
        for username, score in users_data:
            # Create user if doesn't exist
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': f'{username.lower()}@example.com'}
            )
            
            if created:
                user.set_password('password123')  # Default password
                user.save()
            
            # Create or update profile
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'score': score}
            )
            
            if not created:
                profile.score = score
                profile.save()
            
            action = 'Created' if created else 'Updated'
            self.stdout.write(
                self.style.SUCCESS(f'{action} {username} with score {score}')
            )
        
        self.stdout.write(self.style.SUCCESS('✅ Database seeded successfully!'))

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import Season, Challenge
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Sets up sample season and challenges for testing'

    def handle(self, *args, **kwargs):
        # Create a season
        now = timezone.now()
        season, created = Season.objects.get_or_create(
            name="Fall 2025",
            defaults={
                'start_date': now - timedelta(days=30),
                'end_date': now + timedelta(days=60)
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created season: {season.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'Season already exists: {season.name}'))

        # Create sample challenges
        challenges_data = [
            {
                'title': 'Morning Workout',
                'description': 'Complete a 30-minute workout before 9 AM',
                'points': 10,
                'difficulty': 'easy'
            },
            {
                'title': 'Healthy Meal',
                'description': 'Cook and photograph a healthy meal',
                'points': 15,
                'difficulty': 'medium'
            },
            {
                'title': 'Study Session',
                'description': 'Study for at least 2 hours',
                'points': 20,
                'difficulty': 'hard'
            }
        ]

        for challenge_data in challenges_data:
            challenge, created = Challenge.objects.get_or_create(
                title=challenge_data['title'],
                defaults={
                    'description': challenge_data['description'],
                    'points': challenge_data['points'],
                    'difficulty': challenge_data['difficulty'],
                    'start_datetime': now - timedelta(hours=1),
                    'end_datetime': now + timedelta(days=1),
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created challenge: {challenge.title}'))
            else:
                self.stdout.write(self.style.WARNING(f'Challenge already exists: {challenge.title}'))

        self.stdout.write(self.style.SUCCESS('\n✅ Sample data setup complete!'))

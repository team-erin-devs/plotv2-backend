from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from api.models import Challenge, UserProfile


class Command(BaseCommand):
    help = 'Create sample challenges and users for testing'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Create sample challenges with dates
        challenges_data = [
            {
                'title': 'Morning Workout',
                'description': 'Complete a 30-minute morning workout and share a photo or video of yourself exercising.',
                'points': 15,
                'start_date': today,
                'end_date': today,
                'allowed_file_types': ['jpg', 'jpeg', 'png', 'mp4', 'mov'],
                'max_file_size_mb': 25
            },
            {
                'title': 'Healthy Meal Prep',
                'description': 'Prepare a healthy meal for the week and share a photo of your meal prep.',
                'points': 10,
                'start_date': today,
                'end_date': today + timedelta(days=2),
                'allowed_file_types': ['jpg', 'jpeg', 'png'],
                'max_file_size_mb': 10
            },
            {
                'title': 'Study Session',
                'description': 'Complete a 2-hour focused study session and share proof of your study materials.',
                'points': 20,
                'start_date': today - timedelta(days=1),
                'end_date': today + timedelta(days=1),
                'allowed_file_types': ['jpg', 'jpeg', 'png', 'pdf'],
                'max_file_size_mb': 15
            },
            {
                'title': 'Random Act of Kindness',
                'description': 'Perform a random act of kindness for someone and share a brief description with optional photo.',
                'points': 25,
                'start_date': today + timedelta(days=1),
                'end_date': today + timedelta(days=3),
                'allowed_file_types': ['jpg', 'jpeg', 'png'],
                'max_file_size_mb': 10
            },
            {
                'title': 'Learn Something New',
                'description': 'Learn a new skill or concept and share a video or document explaining what you learned.',
                'points': 30,
                'start_date': today - timedelta(days=2),
                'end_date': today - timedelta(days=1),
                'allowed_file_types': ['mp4', 'mov', 'avi', 'pdf'],
                'max_file_size_mb': 50
            }
        ]

        created_challenges = []
        for challenge_data in challenges_data:
            challenge, created = Challenge.objects.get_or_create(
                title=challenge_data['title'],
                defaults=challenge_data
            )
            if created:
                created_challenges.append(challenge)
                self.stdout.write(
                    self.style.SUCCESS(f'Created challenge: {challenge.title} ({challenge.start_date} to {challenge.end_date})')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Challenge already exists: {challenge.title}')
                )

        # Create sample admin user if it doesn't exist
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@challengeapp.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(
                self.style.SUCCESS('Created admin user (username: admin, password: admin123)')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Admin user already exists')
            )

        # Create sample regular user if it doesn't exist
        regular_user, created = User.objects.get_or_create(
            username='student1',
            defaults={
                'email': 'student1@university.edu',
                'first_name': 'John',
                'last_name': 'Doe'
            }
        )
        if created:
            regular_user.set_password('student123')
            regular_user.save()
            
            # Create user profile
            UserProfile.objects.get_or_create(
                user=regular_user,
                defaults={
                    'university': 'Sample University',
                    'student_id': 'STU001'
                }
            )
            
            self.stdout.write(
                self.style.SUCCESS('Created sample student user (username: student1, password: student123)')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Sample student user already exists')
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSetup complete! Created {len(created_challenges)} new challenges.\n'
                'You can now:\n'
                '1. Run "python manage.py runserver" to start the development server\n'
                '2. Visit /admin/ to manage challenges and review proofs\n'
                '3. Use the API endpoints to upload proofs and view challenges\n'
                f'4. Today\'s active challenges: {Challenge.objects.filter(start_date__lte=today, end_date__gte=today, is_active=True).count()}'
            )
        )
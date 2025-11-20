from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import Proof, Challenge

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate database with test users and their points'

    def handle(self, *args, **kwargs):
        test_users = [
            {'username': 'testuser', 'email': 'testuser@example.com', 'points': 0},
            {'username': 'student1', 'email': 'student1@example.com', 'points': 0},
            {'username': 'test123', 'email': 'test123@example.com', 'points': 0},
            {'username': 'jina', 'email': 'jina@example.com', 'points': 123},
            {'username': 'noah', 'email': 'noah@example.com', 'points': 89},
            {'username': 'renee', 'email': 'renee@example.com', 'points': 119},
            {'username': 'alex', 'email': 'alex@example.com', 'points': 95},
            {'username': 'sarah', 'email': 'sarah@example.com', 'points': 78},
            {'username': 'mike', 'email': 'mike@example.com', 'points': 65},
            {'username': 'emma', 'email': 'emma@example.com', 'points': 102},
            {'username': 'lucas', 'email': 'lucas@example.com', 'points': 88},
            {'username': 'olivia', 'email': 'olivia@example.com', 'points': 110},
            {'username': 'ethan', 'email': 'ethan@example.com', 'points': 73},
        ]

        created_count = 0
        updated_count = 0

        for user_data in test_users:
            username = user_data['username']
            email = user_data['email']

            # Create or get user
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': username.capitalize(),
                }
            )

            if created:
                user.set_password('password123')  # Default password
                user.save()
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created user: {username}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'User already exists: {username}'))

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Created {created_count} new users, found {updated_count} existing users.'
        ))
        self.stdout.write(self.style.SUCCESS(
            'Note: Points will be calculated from approved proofs.'
        ))

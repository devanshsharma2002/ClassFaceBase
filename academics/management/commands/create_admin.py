from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

class Command(BaseCommand):
    help = 'Creates an admin user if not exists'

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('DJANGO_ADMIN_USER', 'admin')
        email = os.environ.get('DJANGO_ADMIN_EMAIL', 'admin@example.com')
        password = os.environ.get('DJANGO_ADMIN_PASS', 'temporary123')

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {username}'))
        else:
            self.stdout.write(self.style.WARNING(f'Admin user {username} already exists.'))
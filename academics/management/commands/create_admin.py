from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os


class Command(BaseCommand):
    help = "Creates an admin user if it does not already exist"

    def handle(self, *args, **options):
        User = get_user_model()

        email = os.environ.get("DJANGO_ADMIN_EMAIL", "admin@example.com")
        password = os.environ.get("DJANGO_ADMIN_PASS", "temporary123")
        first_name = os.environ.get("DJANGO_ADMIN_FIRST_NAME", "Admin")
        last_name = os.environ.get("DJANGO_ADMIN_LAST_NAME", "User")

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f"Admin user already exists: {email}"))
            return

        User.objects.create_superuser(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )

        self.stdout.write(self.style.SUCCESS(f"Created admin user: {email}"))
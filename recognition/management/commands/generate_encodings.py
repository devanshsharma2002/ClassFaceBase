from django.core.management.base import BaseCommand
from recognition.services import generate_student_embeddings


class Command(BaseCommand):
    help = 'Generate face embeddings for all student face images'

    def handle(self, *args, **options):
        result = generate_student_embeddings()
        self.stdout.write(
            self.style.SUCCESS(result)
        )
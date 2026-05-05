from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StudentFaceImage


@receiver(post_save, sender=StudentFaceImage)
def generate_embedding_on_upload(sender, instance, created, **kwargs):
    if instance.image and not instance.embedding_data:
        from recognition.services import store_embedding_for_image
        store_embedding_for_image(instance)
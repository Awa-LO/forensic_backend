from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import CollectedData
import os
from django.conf import settings
import logging
logger = logging.getLogger(__name__)

@receiver(pre_delete, sender=CollectedData)
def delete_data_file(sender, instance, **kwargs):
    """Supprime le fichier physique quand l'objet est supprimé"""
    if instance.file:
        file_path = os.path.join(settings.MEDIA_ROOT, instance.file.name)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Erreur suppression fichier {file_path}: {str(e)}")
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from care.emr.models.patient import Patient


logger = logging.getLogger(__name__)

@receiver(post_save, sender=Patient)
def hook_patient_created(sender, instance, created, **kwargs):
    if created:
        logger.info(f"Patient created with ID: {instance.id}")
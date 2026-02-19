import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from care.emr.models.patient import Patient

from care_quick_assign.tasks import create_quick_assignment


logger = logging.getLogger(__name__)

@receiver(post_save, sender=Patient)
def hook_patient_created(sender, instance, created, **kwargs):
    if not created:
        return

    logger.info("Quick Auto Assignment: Signal received for patient creation")
    logger.info("Proceeding with quick auto assignment for patient")

    transaction.on_commit(
        lambda: create_quick_assignment.delay(instance.external_id)
    )
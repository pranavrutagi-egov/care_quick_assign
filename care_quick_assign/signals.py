from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict

from care.emr.models.patient import Patient

from care_quick_assign.models.auto_assignment_config import AutoAssignmentConfig
from care_quick_assign.tasks import create_quick_assignment

import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Patient)
def hook_patient_created(sender, instance, created, **kwargs):
    if not created:
        return

    auto_assignment_config = AutoAssignmentConfig.objects.first()

    if not auto_assignment_config:
        logger.info("Auto-assignment config is missing")
        return

    if not auto_assignment_config.enabled:
        logger.info("Quick auto-assignment feature is disabled")
        return

    config_snapshot = model_to_dict(auto_assignment_config, exclude=["enabled"])
    logger.info(config_snapshot)

    transaction.on_commit(
        lambda: create_quick_assignment.delay(instance.external_id, config_snapshot)
    )

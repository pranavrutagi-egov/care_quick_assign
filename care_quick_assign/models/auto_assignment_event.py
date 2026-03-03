from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint

from care.utils.models.base import BaseModel
from care.emr.models.patient import Patient
from care.users.models import User

from care.utils.time_util import care_now



class AutoAssignmentEventStatus(models.TextChoices):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class AutoAssignmentEvent(BaseModel):

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)

    status = models.CharField(
        max_length=20,
        choices=AutoAssignmentEventStatus.choices,
        default=AutoAssignmentEventStatus.PENDING,
    )

    failure_reason = models.TextField(null=True, blank=True)
    assigned_staff = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    execution_time_ms = models.PositiveIntegerField(null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    triggered_at = models.DateTimeField(default=care_now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            CheckConstraint(
                condition=(
                    Q(
                        status=AutoAssignmentEventStatus.PENDING,
                        failure_reason__isnull=True,
                        assigned_staff__isnull=True,
                        completed_at__isnull=True
                    ) |
                    Q(
                        status=AutoAssignmentEventStatus.FAILED,
                        failure_reason__isnull=False,
                        assigned_staff__isnull=True,
                        completed_at__isnull=False
                    ) |
                    Q(
                        status=AutoAssignmentEventStatus.SUCCESS,
                        assigned_staff__isnull=False,
                        failure_reason__isnull=True,
                        completed_at__isnull=False
                    )
                ),
                name="valid_status_consistency"
            ),
            UniqueConstraint(fields=["patient"], name="unique_auto_assignment_per_patient")
        ]
        indexes = [
            models.Index(fields=["status"]),
        ]



    def _finalize_assignment_log(self, status, reason=None, assigned_staff=None):
        self.status = status
        now = care_now()
        self.failure_reason = reason
        self.assigned_staff = assigned_staff

        self.execution_time_ms = int((now - self.triggered_at).total_seconds() * 1000)
        self.completed_at = now
        self.save()


    def reinitialize_for_retry(self):
        self.status = AutoAssignmentEventStatus.PENDING
        self.failure_reason = None
        self.assigned_staff = None
        self.execution_time_ms = None
        self.completed_at = None
        self.triggered_at = care_now()
        self.retry_count += 1
        self.save()


    def log_failure(self, reason):
        if not reason:
            raise ValueError("Failure reason must be provided for failed assignment.")
        self._finalize_assignment_log(status=AutoAssignmentEventStatus.FAILED, reason=reason)


    def log_success(self, assigned_staff):
        if not assigned_staff:
            raise ValueError("Assigned staff must be provided for successful assignment.")
        self._finalize_assignment_log(status=AutoAssignmentEventStatus.SUCCESS, assigned_staff=assigned_staff)

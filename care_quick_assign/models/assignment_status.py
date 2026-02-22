from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint

from care.emr.models import EMRBaseModel
from care.emr.models.patient import Patient
from care.users.models import User

from care.utils.time_util import care_now



class AutoAssignmentStatus(models.IntegerChoices):
    PENDING = 1, "PENDING"
    SUCCESS = 2, "SUCCESS"
    FAILED = 3, "FAILED"


class AutoAssignmentEvent(EMRBaseModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)

    status = models.SmallIntegerField(
        choices=AutoAssignmentStatus.choices,
        default=AutoAssignmentStatus.PENDING
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
    triggered_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # db_table = "auto_assignment_event"
        constraints = [
            CheckConstraint(
                condition=(
                    Q(status=AutoAssignmentStatus.PENDING) |
                    Q(status=AutoAssignmentStatus.FAILED, failure_reason__isnull=False) |
                    Q(status=AutoAssignmentStatus.SUCCESS, assigned_staff__isnull=False)
                ),
                name="valid_status_and_reason_or_staff"
            ),
            UniqueConstraint(fields=["patient"], name="unique_auto_assignment_per_patient")
        ]
        indexes = [
            models.Index(fields=["status"]),
        ]


    def log_failure(self, reason):
        self.status = AutoAssignmentStatus.FAILED
        self.failure_reason = reason
        self.execution_time_ms = (care_now() - self.triggered_at).total_seconds() * 1000
        self.completed_at = care_now()
        self.save()


    def log_success(self, assigned_staff=None):
        self.status = AutoAssignmentStatus.SUCCESS
        self.assigned_staff = assigned_staff
        self.execution_time_ms = (care_now() - self.triggered_at).total_seconds() * 1000
        self.completed_at = care_now()
        self.save()

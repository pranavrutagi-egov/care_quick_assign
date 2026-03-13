from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from care.utils.models.base import BaseModel
from care.facility.models import Facility


class AutoAssignmentConfig(BaseModel):
    facility = models.OneToOneField(
        Facility,
        on_delete=models.CASCADE
    )
    enabled = models.BooleanField(default=False)
    max_patients_per_staff = models.PositiveIntegerField(null=True, blank=True)
    max_patients_in_total = models.PositiveIntegerField(null=True, blank=True)
    retry_attempts = models.PositiveIntegerField(default=1)
    window_size = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )
    skill_weight = models.PositiveIntegerField(
        default=1,
        validators=[
            MinValueValidator(0), MaxValueValidator(5)
        ]
    )
    workload_weight = models.PositiveIntegerField(
        default=1,
        validators=[
            MinValueValidator(0), MaxValueValidator(5)
        ]
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(skill_weight__gte=0, skill_weight__lte=5)
                ),
                name="skill_weight_range_0_5",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(workload_weight__gte=0, workload_weight__lte=5)
                ),
                name="workload_weight_range_0_5",
            ),
        ]

    def __str__(self):
        state = "enabled" if self.enabled else "disabled"
        return f"AutoAssignmentConfig for {self.facility.name} ({state})"

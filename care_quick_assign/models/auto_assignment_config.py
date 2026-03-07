from django.db import models
from django.core.validators import MinValueValidator

from care.utils.models.base import BaseModel


class AutoAssignmentConfig(BaseModel):
    enabled = models.BooleanField(default=False)
    max_patients_per_staff = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    skill_weight = models.PositiveIntegerField(default=1)
    workload_weight = models.PositiveIntegerField(default=1)
    acuity_weight = models.PositiveIntegerField(default=1)
    location_weight = models.PositiveIntegerField(default=1)
    retry_attempts = models.PositiveIntegerField(default=1)
    window_size = models.PositiveIntegerField(default=1)

    def __str__(self):
        state = "enabled" if self.enabled else "disabled"
        return f"AutoAssignmentConfig ({state})"

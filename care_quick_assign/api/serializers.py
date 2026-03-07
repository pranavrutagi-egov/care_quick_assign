from rest_framework import serializers

from care_quick_assign.models.auto_assignment_event import AutoAssignmentEvent
from care_quick_assign.models.auto_assignment_config import AutoAssignmentConfig


class AssignmentEventSerializer(serializers.ModelSerializer):
    patient = serializers.CharField(source="patient.external_id")

    class Meta:
        model = AutoAssignmentEvent
        fields = ["patient", "failure_reason", "retry_count"]




class AutoAssignmentConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoAssignmentConfig
        fields = [
            "enabled",
            "max_patients_per_staff",
            "skill_weight",
            "workload_weight",
            "acuity_weight",
            "location_weight",
            "retry_attempts",
            "window_size"
        ]

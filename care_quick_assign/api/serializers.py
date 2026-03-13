from rest_framework import serializers

from care.facility.models.facility import Facility

from care_quick_assign.models.auto_assignment_event import AutoAssignmentEvent
from care_quick_assign.models.auto_assignment_config import AutoAssignmentConfig


class AssignmentEventSerializer(serializers.ModelSerializer):
    patient = serializers.CharField(source="patient.external_id")

    class Meta:
        model = AutoAssignmentEvent
        fields = ["patient", "failure_reason", "retry_count"]




class AutoAssignmentConfigSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="external_id", read_only=True)
    facility_id = serializers.UUIDField(
        source="facility.external_id",
        required=True
    )

    class Meta:
        model = AutoAssignmentConfig
        fields = [
            "id",
            "facility_id",
            "enabled",
            "max_patients_per_staff",
            "max_patients_in_total",
            "skill_weight",
            "workload_weight",
            "retry_attempts",
            "window_size",
        ]

    def validate_facility_id(self, value):
        facility = Facility.objects.filter(external_id=value).first()
        if not facility:
            raise serializers.ValidationError("Facility not found.")
        return facility

    def create(self, validated_data):
        facility_data = validated_data.pop("facility")
        validated_data["facility"] = facility_data["external_id"]
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("facility", None)
        return super().update(instance, validated_data)

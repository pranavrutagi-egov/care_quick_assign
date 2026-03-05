from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


from care.utils.shortcuts import get_object_or_404

from care_quick_assign.settings import plugin_settings
from care_quick_assign.models.auto_assignment_event import AutoAssignmentEvent, AutoAssignmentEventStatus
from care_quick_assign.api.serializers import AssignmentEventSerializer
from care_quick_assign.tasks import create_quick_assignment


class AssignmentViewSet(GenericViewSet):
    serializer_class = AssignmentEventSerializer
    permission_classes = [IsAuthenticated]


    @action(detail=False, methods=["get"])
    def unassigned(self, request, *args, **kwargs):
        failed_assignments = AutoAssignmentEvent.objects.filter(
            status=AutoAssignmentEventStatus.FAILED
        ).select_related("patient")

        serializer = self.get_serializer(failed_assignments, many=True)
        return Response(serializer.data)


    @action(detail=False, methods=["post"], url_path=r"unassigned/(?P<patient_id>[^/.]+)/retry")
    def retry(self, request, *args, **kwargs):
        patient_id = kwargs.get("patient_id")
        assignment_event_log = get_object_or_404(AutoAssignmentEvent, patient__external_id=patient_id)

        if assignment_event_log.retry_count >= plugin_settings.CARE_QUICK_AUTO_ASSIGN_MAX_RETRIES:
            return Response({"error": "Max retry attempts reached for this patient."}, status=400)

        assignment_event_log.reinitialize_for_retry()
        create_quick_assignment.delay(patient_external_id=patient_id)
        return Response({"message": "Auto-assignment retry initiated successfully."})

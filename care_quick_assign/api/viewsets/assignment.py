from rest_framework.viewsets import GenericViewSet
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from rest_framework.decorators import action
from rest_framework.response import Response

from care.utils.shortcuts import get_object_or_404
from care.emr.models.patient import Patient

from care_quick_assign.models.auto_assignment_event import AutoAssignmentEvent, AutoAssignmentEventStatus

from care_quick_assign.tasks import create_quick_assignment



class FailedAssignmentSerializer(ModelSerializer):
    patient = serializers.CharField(source="patient.external_id")

    class Meta:
        model = AutoAssignmentEvent
        fields = ["patient", "failure_reason", "retry_count"]



class AssignmentViewSet(GenericViewSet):

    @action(detail=False, methods=["get"])
    def unassigned(self, request):
        failed_assignments = AutoAssignmentEvent.objects.filter(status=AutoAssignmentEventStatus.FAILED).select_related("patient")
        serializer = FailedAssignmentSerializer(failed_assignments, many=True)
        return Response(serializer.data)



    @action(detail=False, methods=["post"], url_path=r"(?P<patient_id>[^/.]+)/retry")
    def retry(self, request, *args, **kwargs):

        patient_id = kwargs.get("patient_id")
        assignment_event_log = get_object_or_404(AutoAssignmentEvent, patient__external_id=patient_id)

        try:
            assignment_event_log.reinitialize_for_retry()

            create_quick_assignment.delay(patient_external_id=patient_id, is_manual_retry=True)

            return Response({"message": "Auto-assignment retry initiated successfully."})

        except Patient.DoesNotExist:
            return Response({"error": "Patient not found."}, status=404)

        except AutoAssignmentEvent.DoesNotExist:
            return Response({"error": "No failed auto-assignment found for the given patient."}, status=404)

        except ValueError as ve:
            return Response({"error": str(ve)}, status=400)

        except Exception as e:
            return Response({"error": str(e)}, status=500)

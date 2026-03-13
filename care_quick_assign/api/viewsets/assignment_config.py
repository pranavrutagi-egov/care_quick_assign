from rest_framework import status
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from care.utils.shortcuts import get_object_or_404
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController

from care_quick_assign.models.auto_assignment_config import AutoAssignmentConfig
from care_quick_assign.api.serializers import AutoAssignmentConfigSerializer


class AutoAssignmentConfigViewSet(GenericViewSet):
    serializer_class = AutoAssignmentConfigSerializer
    permission_classes = [IsAuthenticated]

    def authorize_update(self, model_instance):
        if not AuthorizationController.call(
            "can_update_facility_obj", self.request.user, model_instance
        ):
            raise PermissionDenied("You do not have permission to set configuration")


    @action(detail=False, methods=["get"], url_path="config")
    def get_config(self, request):
        facility_id = request.query_params.get("facility_id")
        if not facility_id:
            return Response(
                {"detail": "facility_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        facility = get_object_or_404(Facility, external_id=facility_id)
        config = get_object_or_404(AutoAssignmentConfig, facility=facility)
        return Response(self.get_serializer(config).data)


    @action(detail=False, methods=["post"], url_path="config/save")
    def save_config(self, request):
        facility_id = request.data.get("facility_id")
        if not facility_id:
            return Response(
                {"detail": "facility_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        facility = get_object_or_404(Facility, external_id=facility_id)

        self.authorize_update(facility)

        config = AutoAssignmentConfig.objects.filter(facility=facility).first()

        if config:
            serializer = self.get_serializer(config, data=request.data)
        else:
            serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK if config else status.HTTP_201_CREATED,
        )

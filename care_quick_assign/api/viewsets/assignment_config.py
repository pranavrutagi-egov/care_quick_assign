from rest_framework import status
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from care_quick_assign.models.auto_assignment_config import AutoAssignmentConfig
from care_quick_assign.api.serializers import AutoAssignmentConfigSerializer


class AutoAssignmentConfigViewSet(GenericViewSet):
    serializer_class = AutoAssignmentConfigSerializer
    permission_classes = [IsAuthenticated]

    def _get_config(self, request):
        config = AutoAssignmentConfig.objects.first()
        if config is None:
            return Response({"config": "Auto-assignment configuration not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(config).data)


    def _upsert_config(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        config, created = AutoAssignmentConfig.objects.update_or_create(
            defaults=serializer.validated_data
        )

        return Response(
            self.get_serializer(config).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


    @action(detail=False, methods=["get", "post"])
    def config(self, request, *args, **kwargs):
        if request.method == "GET":
            return self._get_config(request)
        return self._upsert_config(request)

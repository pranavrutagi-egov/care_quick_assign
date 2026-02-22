from rest_framework.viewsets import GenericViewSet
from rest_framework.serializers import ModelSerializer
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin

from care_quick_assign.models.assignment_status import AutoAssignmentEvent


class AutoAssignmentEventSerializer(ModelSerializer):
    class Meta:
        model = AutoAssignmentEvent
        fields = "__all__"



class AutoAssignmentEventViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    GenericViewSet
):
    queryset = AutoAssignmentEvent.objects.all()
    serializer_class = AutoAssignmentEventSerializer

from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from care_quick_assign.api.viewsets import AutoAssignmentEventViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("auto-assignment-event", AutoAssignmentEventViewSet, basename="auto_assignment_event")

urlpatterns = router.urls

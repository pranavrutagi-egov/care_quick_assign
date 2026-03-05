from django.conf import settings

from rest_framework.routers import DefaultRouter, SimpleRouter

from care_quick_assign.api.viewsets.assignment_config import AutoAssignmentConfigViewSet
from care_quick_assign.api.viewsets.assignment import AssignmentViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("assignments", AssignmentViewSet, basename="assignments")

router.register("auto-assignment", AutoAssignmentConfigViewSet, basename="config")

urlpatterns = router.urls

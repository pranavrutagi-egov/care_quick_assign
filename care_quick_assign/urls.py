from django.conf import settings

from rest_framework.routers import DefaultRouter, SimpleRouter

from care_quick_assign.api.viewsets.assignment import AssignmentViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("assignments", AssignmentViewSet, basename="assignments")

urlpatterns = router.urls

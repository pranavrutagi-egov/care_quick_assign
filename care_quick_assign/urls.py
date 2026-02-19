from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from care_quick_assign.api.viewsets import QuickAutoAssignViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("", QuickAutoAssignViewSet, basename="care_quick_assign")

urlpatterns = router.urls

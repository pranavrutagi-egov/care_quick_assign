from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
import logging

PLUGIN_NAME = "care_quick_assign"
logger = logging.getLogger(__name__)


class CareQuickAssignConfig(AppConfig):
    name = PLUGIN_NAME
    verbose_name = _("Care quick assign")

    def ready(self):
        import care_quick_assign.signals  # noqa F401

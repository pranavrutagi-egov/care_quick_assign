from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from care_quick_assign.constants import PLUGIN_NAME
from care_quick_assign.settings import plugin_settings as settings

import logging


logger = logging.getLogger(__name__)


class CareQuickAssignConfig(AppConfig):
    name = PLUGIN_NAME
    verbose_name = _("Care quick assign")

    def ready(self):
        if settings.CARE_QUICK_AUTO_ASSIGN_ENABLED == "True":
            import care_quick_assign.signals.signals  # noqa F401

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from care_quick_assign.constants import PLUGIN_NAME
from care_quick_assign.settings import plugin_settings as settings


class CareQuickAssignConfig(AppConfig):
    name = PLUGIN_NAME
    verbose_name = _("Care quick assign")

    def ready(self):
        import care_quick_assign.signals  # noqa F401

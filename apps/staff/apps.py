from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class StaffConfig(AppConfig):
    """The people who work at the workshop (docs/rules/staff-list.md)."""

    name = "apps.staff"
    verbose_name = _("Staff")

    def ready(self):
        # Hands staff's own modules and permissions to the two lists, as every
        # app does from its ready() (ADR-0026).
        from apps.accounts.roles import add_permissions
        from apps.staff import modules, permissions
        from apps.workshops.modules import add_modules

        add_modules(*modules.MODULES)
        add_permissions(self.label, permissions.PERMISSIONS)

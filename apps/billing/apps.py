from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BillingConfig(AppConfig):
    """A job card's bill, and settling it (docs/rules/settle-bill.md)."""

    name = "apps.billing"
    verbose_name = _("Billing")

    def ready(self):
        # Hands billing's own modules and permissions to the two lists, as every app does
        # from its ready() (ADR-0026).
        from apps.accounts.roles import add_permissions
        from apps.billing import modules, permissions
        from apps.workshops.modules import add_modules

        add_modules(*modules.MODULES)
        add_permissions(self.label, permissions.PERMISSIONS)

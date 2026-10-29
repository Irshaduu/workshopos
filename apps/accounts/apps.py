from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AccountsConfig(AppConfig):
    """Who signs in, and what each person may do (ADR-0007)."""

    name = "apps.accounts"
    verbose_name = _("Accounts")

    def ready(self):
        # Hands accounts' own modules and permissions to the two lists, as
        # every app does from its ready() (ADR-0026).
        from apps.accounts import modules, permissions
        from apps.accounts.roles import add_permissions
        from apps.workshops.modules import add_modules

        add_modules(*modules.MODULES)
        add_permissions(self.label, permissions.PERMISSIONS)

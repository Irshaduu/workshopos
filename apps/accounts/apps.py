from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AccountsConfig(AppConfig):
    """Who signs in, and what each person may do (ADR-0007)."""

    name = "apps.accounts"
    verbose_name = _("Accounts")

    def ready(self):
        # Hands accounts' own modules to the list, as every app does from its
        # ready() (ADR-0026). Its permissions come with its first page that asks
        # for one, Staff logins (Phase 6).
        from apps.accounts import modules
        from apps.workshops.modules import add_modules

        add_modules(*modules.MODULES)

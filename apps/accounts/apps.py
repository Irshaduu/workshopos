from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AccountsConfig(AppConfig):
    """Who signs in, and what each person may do (ADR-0007)."""

    name = "apps.accounts"
    verbose_name = _("Accounts")

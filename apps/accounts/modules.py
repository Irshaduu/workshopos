"""The modules of accounts (docs/MODULES.md), for the module list (ADR-0011)."""

from django.utils.translation import gettext_lazy as _

from apps.workshops.modules import Module

MODULES = (
    Module("sign_in", _("Sign-in"), core=True),
    # The tab bar and the menu, and the home page until the live board
    # takes its address (Phase 6).
    Module("roles", _("Roles"), core=True),
)

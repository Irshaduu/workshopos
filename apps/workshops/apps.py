from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class WorkshopsConfig(AppConfig):
    """The tenant: each workshop, its branches, and whether it may work (ADR-0023)."""

    name = "apps.workshops"
    verbose_name = _("Workshops")

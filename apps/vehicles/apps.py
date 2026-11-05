from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class VehiclesConfig(AppConfig):
    """Cars and customers, each one record in a workshop (ADR-0030)."""

    name = "apps.vehicles"
    verbose_name = _("Cars and customers")

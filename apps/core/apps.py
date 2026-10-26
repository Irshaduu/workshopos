from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Shared tools for every app. No business rules (docs/ARCHITECTURE.md)."""

    name = "apps.core"

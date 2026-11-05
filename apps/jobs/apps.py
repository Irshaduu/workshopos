from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class JobsConfig(AppConfig):
    """One visit of one car: the job card and its rows (docs/rules/job-card.md)."""

    name = "apps.jobs"
    verbose_name = _("Jobs")

    def ready(self):
        # Hands jobs' own modules and permissions to the two lists, as every app does
        # from its ready() (ADR-0026).
        from apps.accounts.roles import add_permissions
        from apps.jobs import modules, permissions
        from apps.workshops.modules import add_modules

        add_modules(*modules.MODULES)
        add_permissions(self.label, permissions.PERMISSIONS)

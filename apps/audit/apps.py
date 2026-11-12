from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AuditConfig(AppConfig):
    """Money after it was recorded: who may date it back or change it, and what is kept
    (docs/rules/change-history.md)."""

    name = "apps.audit"
    verbose_name = _("Change history")

    def ready(self):
        # Hands audit's own permissions to the list, as every app does from its ready()
        # (ADR-0026). It has no page yet, so no module: Change history's page comes in
        # Phase 6.
        from apps.accounts.roles import add_permissions
        from apps.audit import permissions

        add_permissions(self.label, permissions.PERMISSIONS)

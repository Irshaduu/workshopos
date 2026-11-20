"""The modules of billing (docs/MODULES.md), for the module list (ADR-0011)."""

from django.utils.translation import gettext_lazy as _

from apps.workshops.modules import Module

MODULES = (
    # The bill page belongs here until Printed bill comes (Phase 6).
    Module("settle_bill", _("Settle bill")),
    # Its first, plain Paid bills now (SETTLE-53); the rest of it in Phase 6.
    Module("pending_and_paid_bills", _("Pending and paid bills")),
)

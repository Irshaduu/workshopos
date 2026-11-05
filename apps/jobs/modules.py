"""The modules of jobs (docs/MODULES.md), for the module list (ADR-0011)."""

from django.utils.translation import gettext_lazy as _

from apps.workshops.modules import Module

MODULES = (
    Module("live_board", _("Live board")),
    Module("job_card", _("Job card")),
)

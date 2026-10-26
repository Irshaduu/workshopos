"""Reads for workshops: rules that read data, never change it (ADR-0005)."""

from apps.workshops.models import WorkshopStatus


def may_work(workshop):
    """May this workshop's members work now? The one place that decides it (ADR-0023).

    Every request asks it once memberships give each request its workshop.
    A suspended workshop is blocked, except for signing out. The
    subscription rule (docs/MODULES.md) plugs in here.
    """
    return workshop.status == WorkshopStatus.ACTIVE

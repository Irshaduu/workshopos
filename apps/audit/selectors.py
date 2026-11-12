"""Reads for audit: what a person may do with a money date (docs/rules/change-history.md)."""

from datetime import timedelta

from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from apps.audit.models import AuditSettings


def limits(workshop):
    """The workshop's own limits, or v1's when it never chose its own (CHANGE-18). Reading
    never writes: the answer for a workshop with no row is a row that is never saved."""
    return AuditSettings.objects.for_workshop(workshop).first() or AuditSettings(workshop=workshop)


def earliest_money_date(workshop, user, today=None):
    """The earliest day this person may date money: the back-date limit before today, India
    time, so for Office on the 22nd with 3 days, the 19th; None for someone who may date it
    any day (CHANGE-13, CHANGE-15, CHANGE-16). A date box shows it, but only
    money_date_problem() decides."""
    if user.has_perm("audit.date_money_any_day"):
        return None
    return _back_date(workshop, today)[1]


def money_date_problem(workshop, user, day, today=None):
    """Why this person may not date money on this day, in plain words; None when they may
    (CHANGE-13 to CHANGE-16).

    A day in the future is refused for everyone, never moved to today: it is a mistyped
    year far more often than a plan. A day further back than the limit is refused to anyone
    without date_money_any_day, and the refusal names the earliest day and who can do it.
    """
    today = today or timezone.localdate()
    if day > today:
        return _("This day is in the future. Check the year.")
    if user.has_perm("audit.date_money_any_day"):
        return None
    days, earliest = _back_date(workshop, today)
    if day >= earliest:
        return None
    return ngettext(
        "Office can date money only up to %(days)d day back: %(earliest)s at the earliest. "
        "Ask an owner to record an older one.",
        "Office can date money only up to %(days)d days back: %(earliest)s at the earliest. "
        "Ask an owner to record an older one.",
        days,
    ) % {"days": days, "earliest": date_format(earliest)}


def _back_date(workshop, today):
    """The workshop's back-date limit in days, and the earliest day it allows."""
    today = today or timezone.localdate()
    days = limits(workshop).back_date_days
    return days, today - timedelta(days=days)

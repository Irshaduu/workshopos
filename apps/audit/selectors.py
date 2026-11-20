"""Reads for audit: what a person may do with a money date, and with money already recorded
(docs/rules/change-history.md)."""

from datetime import timedelta

from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from apps.audit.models import AuditSettings, Change


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


def money_change_refusal(workshop, user, recorded_at, *, happened, now=None):
    """Why this person may not change money recorded at that moment, in plain words; None
    when they may (CHANGE-9 to CHANGE-12).

    The window counts from the moment the money was typed in, never from its money date
    (CHANGE-10). An owner, who may change money any time, is never refused (CHANGE-11). The
    refusal says how long ago, the rule, and who can do it, and `happened` is the record's
    own first words, like "Settled %(ago)s.", so a bill and a payment to a shop each say
    theirs (CHANGE-12).
    """
    if user.has_perm("audit.money_change_any_time"):
        return None
    hours = limits(workshop).edit_window_hours
    age = (now or timezone.now()) - recorded_at
    if age <= timedelta(hours=hours):
        return None
    rule = ngettext(
        "Office can change money only within %(hours)d hour.",
        "Office can change money only within %(hours)d hours.",
        hours,
    ) % {"hours": hours}
    return " ".join((happened % {"ago": how_long_ago(age)}, rule, _("Ask an owner.")))


def kept_change(workshop, branch, key):
    """The change kept under this key; None when none is. A change box asks this first,
    because a double tap sends its key again (SETTLE-52)."""
    return Change.objects.for_workshop(workshop).for_branch(branch).filter(pk=key).first()


def how_long_ago(age):
    """How long ago, in words: in hours for two days, then in days, like "30 hours ago" or
    "5 days ago" (CHANGE-12, v1's _how_long_ago)."""
    hours = int(age.total_seconds() // 3600)
    if hours < 48:
        return ngettext("%(count)d hour ago", "%(count)d hours ago", hours) % {"count": hours}
    days = hours // 24
    return ngettext("%(count)d day ago", "%(count)d days ago", days) % {"count": days}

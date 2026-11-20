"""The edit window: how long Office may change money after it was recorded
(docs/rules/change-history.md, CHANGE-9 to CHANGE-12 and CHANGE-18), at
money_change_refusal(). That the window counts from the moment typed, never the money date
(CHANGE-10), is tested where a bill is changed (apps/billing/tests/test_change_payments.py)."""

from datetime import datetime, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy

from apps.accounts.models import Role
from apps.accounts.tests.factories import MembershipFactory
from apps.audit.models import EDIT_WINDOW_HOURS, AuditSettings
from apps.audit.selectors import limits, money_change_refusal
from apps.audit.tests.factories import AuditSettingsFactory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 18, 18, 0, tzinfo=timezone.get_current_timezone())
SETTLED = gettext_lazy("Settled %(ago)s.")


def refusal(member, ago):
    """What this member is told about money recorded that long before NOW."""
    return money_change_refusal(member.workshop, member.user, NOW - ago, happened=SETTLED, now=NOW)


@pytest.fixture
def office():
    return MembershipFactory(role=Role.OFFICE)


def test_change_9_office_may_change_money_for_24_hours(office):
    assert refusal(office, timedelta(minutes=5)) is None
    assert refusal(office, timedelta(hours=24)) is None


def test_change_9_12_after_24_hours_office_is_refused_saying_how_long_ago_and_who_can(office):
    assert refusal(office, timedelta(hours=30)) == (
        "Settled 30 hours ago. Office can change money only within 24 hours. Ask an owner."
    )


def test_change_9_a_minute_past_the_window_is_past_it(office):
    assert refusal(office, timedelta(hours=24, minutes=1)) == (
        "Settled 24 hours ago. Office can change money only within 24 hours. Ask an owner."
    )


@pytest.mark.parametrize(
    ("ago", "words"),
    [
        pytest.param(timedelta(hours=47, minutes=59), "47 hours ago", id="hours for two days"),
        pytest.param(timedelta(hours=48), "2 days ago", id="then days"),
        pytest.param(timedelta(days=5, hours=23), "5 days ago", id="whole days"),
    ],
)
def test_change_12_it_counts_in_hours_for_two_days_then_in_days(office, ago, words):
    assert f"Settled {words}." in refusal(office, ago)


def test_change_12_one_hour_reads_as_one_hour(office):
    AuditSettingsFactory(workshop=office.workshop, edit_window_hours=1)

    assert refusal(office, timedelta(hours=1, minutes=30)) == (
        "Settled 1 hour ago. Office can change money only within 1 hour. Ask an owner."
    )


def test_change_11_an_owner_is_never_refused():
    owner = MembershipFactory(role=Role.OWNER)

    assert refusal(owner, timedelta(days=400)) is None


def test_change_9_floor_is_held_to_the_window_too():
    floor = MembershipFactory(role=Role.FLOOR)

    assert refusal(floor, timedelta(hours=25))


def test_change_18_a_workshop_that_never_chose_uses_v1s_24_hours_and_saves_nothing(office):
    assert limits(office.workshop).edit_window_hours == EDIT_WINDOW_HOURS == 24
    assert not AuditSettings.objects.exists()


def test_change_18_a_workshops_own_window_is_used(office):
    AuditSettingsFactory(workshop=office.workshop, edit_window_hours=48)

    assert refusal(office, timedelta(hours=47)) is None
    assert "within 48 hours" in refusal(office, timedelta(hours=49))


def test_change_18_another_workshops_window_is_never_used(office):
    AuditSettingsFactory(edit_window_hours=168)

    assert refusal(office, timedelta(hours=25))


@pytest.mark.parametrize("hours", [0, 169])
def test_change_18_a_window_is_an_hour_to_a_week(hours):
    with pytest.raises(ValidationError):
        AuditSettingsFactory.build(edit_window_hours=hours).full_clean(exclude={"workshop"})

    saved = AuditSettingsFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        AuditSettings.objects.filter(pk=saved.pk).update(edit_window_hours=hours)

"""Money dates and the back-date limit (docs/rules/change-history.md, CHANGE-13 to CHANGE-18)."""

from datetime import date, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import Role
from apps.accounts.tests.factories import MembershipFactory
from apps.audit import selectors
from apps.audit.models import BACK_DATE_DAYS, AuditSettings
from apps.audit.selectors import earliest_money_date, limits, money_date_problem
from apps.audit.tests.factories import AuditSettingsFactory

pytestmark = pytest.mark.django_db

#: A Sunday, so "3 days back" crosses into the week before.
TODAY = date(2026, 11, 22)
FUTURE = "This day is in the future. Check the year."


def days_back(count):
    return TODAY - timedelta(days=count)


@pytest.mark.parametrize("role", [Role.OWNER, Role.OFFICE])
def test_change_13_today_is_fine_for_every_role(role):
    member = MembershipFactory(role=role)

    assert money_date_problem(member.workshop, member.user, TODAY, today=TODAY) is None


def test_change_13_today_is_today_in_india(monkeypatch):
    member = MembershipFactory(role=Role.OFFICE)
    monkeypatch.setattr(selectors.timezone, "localdate", lambda: TODAY)

    assert money_date_problem(member.workshop, member.user, TODAY) is None
    assert money_date_problem(member.workshop, member.user, TODAY + timedelta(days=1)) == FUTURE
    assert earliest_money_date(member.workshop, member.user) == date(2026, 11, 19)


@pytest.mark.parametrize("role", [Role.OWNER, Role.OFFICE])
def test_change_14_a_day_in_the_future_is_refused_for_everyone(role):
    member = MembershipFactory(role=role)
    tomorrow = TODAY + timedelta(days=1)

    assert money_date_problem(member.workshop, member.user, tomorrow, today=TODAY) == FUTURE


def test_change_15_office_may_date_money_three_days_back_and_no_further():
    member = MembershipFactory(role=Role.OFFICE)

    assert money_date_problem(member.workshop, member.user, days_back(3), today=TODAY) is None
    assert money_date_problem(member.workshop, member.user, days_back(4), today=TODAY) == (
        "Office can date money only up to 3 days back: 19 Nov 2026 at the earliest. "
        "Ask an owner to record an older one."
    )


def test_change_15_the_date_box_gets_the_earliest_day():
    member = MembershipFactory(role=Role.OFFICE)

    assert earliest_money_date(member.workshop, member.user, TODAY) == date(2026, 11, 19)


def test_change_15_one_day_reads_as_one_day():
    member = MembershipFactory(role=Role.OFFICE)
    AuditSettingsFactory(workshop=member.workshop, back_date_days=1)

    assert money_date_problem(member.workshop, member.user, days_back(2), today=TODAY) == (
        "Office can date money only up to 1 day back: 21 Nov 2026 at the earliest. "
        "Ask an owner to record an older one."
    )


def test_change_15_floor_is_held_to_the_limit_too():
    member = MembershipFactory(role=Role.FLOOR)

    assert money_date_problem(member.workshop, member.user, days_back(4), today=TODAY)


def test_change_16_an_owner_may_date_money_any_day():
    member = MembershipFactory(role=Role.OWNER)

    assert money_date_problem(member.workshop, member.user, days_back(400), today=TODAY) is None
    # So the owner's date box has no earliest day from the limit.
    assert earliest_money_date(member.workshop, member.user, TODAY) is None


def test_change_18_a_workshop_that_never_chose_uses_v1s_three_days_and_saves_nothing():
    member = MembershipFactory(role=Role.OFFICE)

    assert limits(member.workshop).back_date_days == BACK_DATE_DAYS == 3
    assert not AuditSettings.objects.exists()


def test_change_18_a_workshops_own_limit_is_used():
    member = MembershipFactory(role=Role.OFFICE)
    AuditSettingsFactory(workshop=member.workshop, back_date_days=5)

    assert money_date_problem(member.workshop, member.user, days_back(5), today=TODAY) is None
    assert "up to 5 days back" in money_date_problem(
        member.workshop, member.user, days_back(6), today=TODAY
    )


def test_change_18_another_workshops_limit_is_never_used():
    member = MembershipFactory(role=Role.OFFICE)
    AuditSettingsFactory(back_date_days=10)

    assert money_date_problem(member.workshop, member.user, days_back(4), today=TODAY)


def test_change_18_one_row_for_each_workshop_by_postgresql():
    settings = AuditSettingsFactory()

    with pytest.raises(IntegrityError), transaction.atomic():
        AuditSettingsFactory(workshop=settings.workshop)


def test_change_18_a_limit_longer_than_a_month_is_refused():
    with pytest.raises(ValidationError):
        AuditSettingsFactory.build(back_date_days=32).full_clean(exclude={"workshop"})

    saved = AuditSettingsFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        AuditSettings.objects.filter(pk=saved.pk).update(back_date_days=32)

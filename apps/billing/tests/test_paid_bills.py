"""Paid bills, the first plain list of settled bills (SETTLE-53): its rules at the selector,
then the page's wiring. Who may open it is in tests/test_permissions.py."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import EDIT_WINDOW_HOURS_MOST
from apps.billing.models import PaymentMethod
from apps.billing.selectors import OFFICE_PAID_BILLS_DAYS, paid_bills_for
from apps.billing.tests.factories import BillFactory, PaymentFactory
from apps.workshops.tests.factories import BranchFactory

pytestmark = pytest.mark.django_db

#: A Wednesday. India time, as every money date is.
TODAY = date(2026, 11, 18)


def at(day, hour=10, minute=0):
    """A moment on that day, India time."""
    return datetime(
        day.year, day.month, day.day, hour, minute, tzinfo=timezone.get_current_timezone()
    )


def bill_of(place, **more):
    """A settled bill of this place's branch."""
    return BillFactory(workshop=place.workshop, branch=place.branch, **more)


def listed(place, today=TODAY):
    return [row.bill for row in paid_bills_for(place.workshop, place.branch, place.by, today=today)]


def test_settle_53_office_sees_the_bills_settled_in_the_last_7_days(office):
    seventh_day = bill_of(office, settled_at=at(TODAY - timedelta(days=7)))
    eighth_day = bill_of(office, settled_at=at(TODAY - timedelta(days=8)))

    assert listed(office) == [seventh_day]
    assert eighth_day not in listed(office)


def test_settle_53_the_7_days_are_counted_in_india_time(office):
    # 00:30 in India is still the evening before in UTC.
    first_minutes = bill_of(office, settled_at=at(TODAY - timedelta(days=7), hour=0, minute=30))
    the_night_before = bill_of(office, settled_at=at(TODAY - timedelta(days=8), hour=23, minute=30))

    assert first_minutes in listed(office)
    assert the_night_before not in listed(office)


def test_settle_53_office_sees_at_least_the_longest_edit_window(db):
    # A workshop may choose up to EDIT_WINDOW_HOURS_MOST; Office must still find every bill it
    # may change, settled at any moment of the first day of the list (CHANGE-9).
    assert timedelta(days=OFFICE_PAID_BILLS_DAYS) >= timedelta(hours=EDIT_WINDOW_HOURS_MOST)


def test_settle_53_a_bill_dated_far_back_but_settled_today_is_on_offices_list(office):
    # An owner may date money any day (CHANGE-16), and Office may still change the bill
    # today (CHANGE-10), so it must find it.
    back_dated = bill_of(office, date=TODAY - timedelta(days=40), settled_at=at(TODAY))

    assert listed(office) == [back_dated]


def test_settle_53_owners_see_every_bill(owner):
    long_ago = TODAY - timedelta(days=400)
    old = bill_of(owner, date=long_ago, settled_at=at(long_ago))

    assert listed(owner) == [old]


def test_settle_53_newest_first_by_the_date_paid_then_the_moment_settled(owner):
    yesterday = bill_of(owner, date=TODAY - timedelta(days=1), settled_at=at(TODAY, hour=12))
    today_first = bill_of(owner, date=TODAY, settled_at=at(TODAY, hour=9))
    today_later = bill_of(owner, date=TODAY, settled_at=at(TODAY, hour=11))

    assert listed(owner) == [today_later, today_first, yesterday]


def test_settle_50_53_a_bill_of_another_branch_or_workshop_is_never_listed(owner):
    there = BranchFactory(workshop=owner.workshop)
    BillFactory(workshop=owner.workshop, branch=there)
    BillFactory()

    assert listed(owner) == []


def test_settle_53_each_row_has_its_total_net_and_payments_in_the_boxs_order(owner):
    bill = bill_of(owner, job_card__labour=Decimal("43000"), discount=Decimal("3000"))
    PaymentFactory(workshop=owner.workshop, bill=bill, method=PaymentMethod.UPI, amount="20000")
    PaymentFactory(workshop=owner.workshop, bill=bill, method=PaymentMethod.CASH, amount="20000")

    (row,) = paid_bills_for(owner.workshop, owner.branch, owner.by)

    assert (row.total, row.net) == (Decimal("43000.00"), Decimal("40000.00"))
    assert [payment.method for payment in row.payments] == ["cash", "upi"]


# The page's wiring.


@pytest.fixture
def signed_in(client):
    def sign_in(place):
        client.force_login(place.by)
        return client

    return sign_in


def test_settle_53_each_row_opens_its_bill(signed_in, office):
    card = office.card(plate="KL10AA1000", car__plate="KL10AA1000")
    bill = office.settle(card, cash="20000", upi="20000")

    html = signed_in(office).get(reverse("billing:paid_bills")).text

    assert f'href="{reverse("billing:bill", kwargs={"key": card.pk})}"' in html
    for shown in (bill.number, "KL10AA1000", "Total &#8377; 43,000", "Net &#8377; 40,000"):
        assert shown in html
    assert "Cash, UPI" in html


def test_settle_53_office_reads_that_it_sees_the_last_7_days(signed_in, office, owner):
    assert "Settled in the last 7 days" in signed_in(office).get(reverse("billing:paid_bills")).text
    assert "Settled in the last" not in signed_in(owner).get(reverse("billing:paid_bills")).text


def test_settle_53_an_empty_list_says_so(signed_in, office, owner):
    assert "No bills settled in the last 7 days" in (
        signed_in(office).get(reverse("billing:paid_bills")).text
    )
    assert "No paid bills yet" in signed_in(owner).get(reverse("billing:paid_bills")).text


def test_settle_53_a_settled_bills_page_goes_back_to_paid_bills(signed_in, office):
    settled, preview = office.card(), office.card()
    office.settle(settled)
    client = signed_in(office)

    settled_page = client.get(reverse("billing:bill", kwargs={"key": settled.pk})).text
    preview_page = client.get(reverse("billing:bill", kwargs={"key": preview.pk})).text

    assert f'<a class="back" href="{reverse("billing:paid_bills")}">Paid bills</a>' in settled_page
    edit = reverse("jobs:edit", kwargs={"key": preview.pk})
    assert f'<a class="back" href="{edit}">{preview.number}</a>' in preview_page

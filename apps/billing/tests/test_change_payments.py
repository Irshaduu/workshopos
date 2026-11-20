"""Change payments (docs/rules/settle-bill.md: SETTLE-38, SETTLE-39, SETTLE-41, SETTLE-42,
SETTLE-44 to SETTLE-48, SETTLE-52, SETTLE-54; and CHANGE-5, CHANGE-7, CHANGE-9 to CHANGE-11),
at its service (apps/billing/services.py). The page's wiring is in
test_change_payments_page.py; who may open the page is in tests/test_permissions.py."""

import threading
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import connection, transaction
from django.http import Http404
from django.utils import timezone

from apps.accounts.models import Role
from apps.audit import selectors as audit_selectors
from apps.audit.models import Change
from apps.billing.models import Bill
from apps.billing.selectors import BOXES, bill_figures
from apps.billing.services import (
    BillChanged,
    PastTheWindow,
    TotalChanged,
    change_payments,
)
from apps.billing.tests.conftest import (
    Place,
    changes,
    payments,
    refused,
    settled,
    settled_hours_ago,
)
from apps.billing.tests.factories import BillFactory
from apps.core.tests.postgresql import wait_for_a_lock
from apps.jobs.models import JobCard
from apps.workshops.tests.factories import BranchFactory

pytestmark = pytest.mark.django_db


def opened_on(place, card):
    """What a change box opened on this card's bill holds now, box by box."""
    saved = bill_figures(place.workshop, place.bill_of(card))
    return {box: saved[box] for box in BOXES}


def test_settle_39_the_discount_becomes_the_total_less_the_new_payments(office):
    card = settled(office, cash="40000")

    bill, change = office.change(card, cash="20000", upi="19000")

    bill.refresh_from_db()
    assert change.moved
    assert bill.discount == Decimal("4000.00")
    assert payments(bill) == {"cash": Decimal("20000.00"), "upi": Decimal("19000.00")}


def test_settle_39_a_method_left_empty_goes_and_a_new_one_comes(office):
    card = settled(office, cash="20000", upi="20000")

    bill, _change = office.change(card, upi="43000")

    bill.refresh_from_db()
    assert payments(bill) == {"upi": Decimal("43000.00")}
    assert bill.discount == Decimal("0.00")


def test_settle_41_the_change_is_kept_with_what_moved_who_and_why(office):
    card = settled(office, cash="40000")
    bill = office.bill_of(card)
    key = uuid.uuid7()

    office.change(card, key=key, reason="Part was UPI", cash="20000", upi="19000")

    (change,) = changes(office)
    assert change.pk == key
    assert change.figures == [
        {"figure": "cash", "kind": "money", "before": "40000.00", "after": "20000.00"},
        {"figure": "upi", "kind": "money", "before": None, "after": "19000.00"},
        {"figure": "discount", "kind": "money", "before": "3000.00", "after": "4000.00"},
    ]
    assert (change.what, change.record_key, change.branch) == ("bill", bill.pk, bill.branch)
    assert change.label == f"{bill.number}, {card.plate}"
    assert (change.by, change.reason) == (office.by, "Part was UPI")


def test_settle_41_a_change_of_method_keeps_both_methods_and_no_discount(office):
    card = settled(office, cash="40000")

    office.change(card, upi="40000")

    (change,) = changes(office)
    assert [figure["figure"] for figure in change.figures] == ["cash", "upi"]


def test_settle_41_52_a_send_that_moves_nothing_saves_nothing_and_keeps_nothing(office):
    card = settled(office, cash="40000")

    bill, change = office.change(card, cash="40000")

    assert change.moved is False
    assert not changes(office).exists()
    assert payments(bill) == {"cash": Decimal("40000.00")}


def test_change_5_a_send_that_moves_nothing_needs_no_reason(office):
    card = settled(office, cash="40000")

    _bill, change = office.change(card, reason="", cash="40000")

    assert change.moved is False


@pytest.mark.parametrize("reason", ["", "   "])
def test_change_5_a_change_with_no_reason_moves_nothing(office, reason):
    card = settled(office)

    words = refused(lambda: office.change(card, reason=reason, cash="39000"))

    assert words == {"reason": ["Type why you are changing this bill."]}
    assert payments(office.bill_of(card)) == {"cash": Decimal("40000.00")}
    assert office.bill_of(card).discount == Decimal("3000.00")


def test_change_7_a_first_settle_keeps_no_change_and_a_change_of_it_does(office):
    card = settled(office)

    assert not changes(office).exists()
    office.change(card, cash="39000")
    assert changes(office).count() == 1


def test_settle_42_a_change_keeps_the_moment_the_bill_was_settled_and_by_whom(office):
    card = settled(office)
    before = office.bill_of(card)
    owner = Place(Role.OWNER, workshop=office.workshop)

    owner.change(card, cash="39000")

    after = office.bill_of(card)
    assert (after.settled_at, after.settled_by) == (before.settled_at, office.by)
    assert after.number == before.number


def test_settle_54_a_date_left_as_it_was_is_never_judged_again(office):
    # Dated 3 days back yesterday, as Office may: today it is 4 days back.
    card = settled(office)
    Bill.objects.filter(job_card=card).update(date=timezone.localdate() - timedelta(days=4))
    JobCard.objects.filter(pk=card.pk).update(admitted_date=date(2026, 1, 1))

    bill, change = office.change(card, cash="39000")

    assert change.moved
    assert bill.date == timezone.localdate() - timedelta(days=4)


def test_settle_54_a_changed_date_is_judged_on_the_day_it_is_changed(office, monkeypatch):
    # A day well inside one financial year, so 3 days back never crosses 1 April.
    today = date(2026, 11, 18)
    monkeypatch.setattr(audit_selectors.timezone, "localdate", lambda: today)
    card = office.card(labour="43000", admitted_date=date(2026, 11, 1))
    office.settle(card, paid_on=today)

    words = refused(lambda: office.change(card, paid_on=today - timedelta(days=4), cash="40000"))
    assert list(words) == ["paid_on"]
    assert "Ask an owner" in words["paid_on"][0]
    words = refused(lambda: office.change(card, paid_on=today + timedelta(days=1), cash="40000"))
    assert words == {"paid_on": ["This day is in the future. Check the year."]}

    bill, _change = office.change(card, paid_on=today - timedelta(days=3), cash="40000")
    assert bill.date == today - timedelta(days=3)
    (change,) = changes(office)
    assert change.figures == [
        {"figure": "paid_on", "kind": "date", "before": "2026-11-18", "after": "2026-11-15"}
    ]


def test_settle_54_a_changed_date_is_never_before_the_car_came_in(owner):
    card = owner.card(labour="43000", admitted_date=date(2026, 6, 10))
    owner.settle(card, paid_on=date(2026, 6, 12))

    words = refused(lambda: owner.change(card, paid_on=date(2026, 6, 9), cash="40000"))

    assert words == {"paid_on": ["The date paid cannot be before the car came in, on 10 Jun 2026."]}


def test_settle_44_a_change_never_moves_a_bill_into_another_financial_year(owner):
    card = owner.card(labour="43000", admitted_date=date(2026, 3, 30))
    owner.settle(card, paid_on=date(2026, 3, 31))

    words = refused(lambda: owner.change(card, paid_on=date(2026, 4, 1), cash="40000"))

    assert words == {
        "paid_on": [
            "The date paid must stay in the bill's financial year, because its number "
            "INV-25-26-0001 belongs to that year."
        ]
    }
    assert owner.bill_of(card).date == date(2026, 3, 31)


def test_settle_16_17_a_change_keeps_the_rules_of_the_payments(office):
    card = settled(office)

    assert refused(lambda: office.change(card, cash="25000", upi="20000")) == {
        "__all__": ["The payments come to 45,000.00, more than the total of 43,000.00."]
    }
    assert refused(lambda: office.change(card)) == {
        "__all__": ["Type what the customer paid, in at least one box."]
    }
    assert payments(office.bill_of(card)) == {"cash": Decimal("40000.00")}
    assert not changes(office).exists()


def test_settle_26_a_total_that_moved_since_it_was_shown_is_refused_in_the_change_boxs_words(
    office,
):
    card = settled(office)

    with pytest.raises(TotalChanged) as moved:
        office.change(card, total_seen="45000", cash="39000")

    assert moved.value.messages == [
        "The bill changed while you had this box open: its total is now 43,000.00. Check the "
        "payments, then change them again."
    ]
    assert not changes(office).exists()


def test_settle_52_a_change_sent_after_someone_else_changed_the_bill_is_refused_whole(office):
    card = settled(office, cash="40000")
    opened = opened_on(office, card)
    Place(Role.OWNER, workshop=office.workshop).change(card, cash="39000")

    with pytest.raises(BillChanged):
        office.change(card, opening=opened, cash="40000", upi="2000")

    assert payments(office.bill_of(card)) == {"cash": Decimal("39000.00")}
    assert changes(office).count() == 1


def test_settle_52_a_send_that_finds_someone_elses_same_change_is_refused_too(office):
    # Not a repeat of this send: someone else changed the bill to what this box now says, so
    # the box opens again as the bill is, and nothing is kept in this person's name.
    card = settled(office, cash="40000")
    opened = opened_on(office, card)
    Place(Role.OWNER, workshop=office.workshop).change(card, reason="Owner's fix", cash="39000")

    with pytest.raises(BillChanged):
        office.change(card, opening=opened, reason="Office's fix", cash="39000")

    assert [change.reason for change in changes(office)] == ["Owner's fix"]


def test_settle_52_a_send_that_does_not_say_what_its_box_opened_with_is_refused(office):
    card = settled(office, cash="40000")

    with pytest.raises(BillChanged):
        office.change(card, opening={}, cash="39000")

    assert not changes(office).exists()


def test_settle_52_a_double_tap_keeps_one_change_and_answers_as_a_repeat(office):
    card = settled(office, cash="40000")
    opened = opened_on(office, card)
    key = uuid.uuid7()
    office.change(card, key=key, opening=opened, cash="39000")

    _bill, again = office.change(card, key=key, opening=opened, cash="39000")

    assert again is None
    assert changes(office).count() == 1


def test_settle_52_a_double_tap_just_past_the_window_still_answers_as_a_repeat(office):
    card = settled(office, cash="40000")
    opened = opened_on(office, card)
    key = uuid.uuid7()
    office.change(card, key=key, opening=opened, cash="39000")
    settled_hours_ago(card, 25)

    _bill, again = office.change(card, key=key, opening=opened, cash="39000")

    assert again is None


def test_settle_52_a_change_key_of_another_bill_is_not_found(office):
    first, second = settled(office), settled(office)
    key = uuid.uuid7()
    office.change(first, key=key, cash="39000")

    with pytest.raises(Http404):
        office.change(second, key=key, cash="39000")
    assert payments(office.bill_of(second)) == {"cash": Decimal("40000.00")}


def test_change_9_12_office_past_the_edit_window_is_refused_saying_why(office):
    card = settled(office)
    settled_hours_ago(card, 25)

    with pytest.raises(PastTheWindow) as late:
        office.change(card, cash="39000")

    assert late.value.words == (
        "Settled 25 hours ago. Office can change money only within 24 hours. Ask an owner."
    )
    assert payments(office.bill_of(card)) == {"cash": Decimal("40000.00")}


def test_change_10_the_window_counts_from_the_moment_settled_never_the_date_paid(office):
    today = timezone.localdate()
    card = office.card(labour="43000", admitted_date=today - timedelta(days=5))
    office.settle(card, paid_on=today - timedelta(days=3))

    _bill, change = office.change(card, cash="39000")

    assert change.moved


def test_change_11_settle_48_an_owner_past_the_window_changes_the_bill_and_it_is_kept(owner):
    card = settled(owner)
    settled_hours_ago(card, 24 * 400)

    owner.change(card, cash="39000")

    assert payments(owner.bill_of(card)) == {"cash": Decimal("39000.00")}
    assert changes(owner).count() == 1


def test_settle_50_a_bill_of_another_branch_or_workshop_is_never_changed(office):
    theirs = BillFactory()
    there = BillFactory(workshop=office.workshop, branch=BranchFactory(workshop=office.workshop))

    for bill in (theirs, there):
        with pytest.raises(Http404):
            change_payments(
                office.workshop,
                office.branch,
                bill.job_card_id,
                uuid.uuid7(),
                office.by,
                paid_on=bill.date,
                payments={"cash": Decimal("1")},
                opening={box: None for box in BOXES} | {"paid_on": bill.date},
                reason="Not ours",
                total_seen=Decimal("0"),
            )
        assert not payments(bill)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("first", "second", "answers"),
    [
        pytest.param("39000", "38000", ["BillChanged", "tuple"], id="two changes, two keys"),
        pytest.param("39000", "39000", ["tuple", "tuple"], id="a double tap, one key"),
    ],
)
def test_settle_45_52_two_sends_from_one_box_at_one_moment_keep_one_change(first, second, answers):
    place = Place(Role.OFFICE)
    card = settled(place)
    opened = opened_on(place, card)
    # Two boxes opened on one bill have two keys; a double tap sends one key twice.
    keys = [uuid.uuid7(), uuid.uuid7()] if first != second else [uuid.uuid7()] * 2
    found = []

    def send(cash, key):
        try:
            found.append(place.change(card, key=key, opening=opened, cash=cash))
        except BillChanged as changed:
            found.append(changed)
        finally:
            connection.close()

    threads = [
        threading.Thread(target=send, args=(cash, key))
        for cash, key in zip((first, second), keys, strict=True)
    ]
    with transaction.atomic():
        # The test holds the bill's card, so both sends read the bill before either saves.
        JobCard.objects.select_for_update().get(pk=card.pk)
        for thread in threads:
            thread.start()
        wait_for_a_lock(2)
    for thread in threads:
        thread.join()

    assert sorted(type(answer).__name__ for answer in found) == sorted(answers)
    assert Change.objects.for_workshop(place.workshop).count() == 1

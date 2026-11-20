"""Settling a bill (docs/rules/settle-bill.md), at its service (apps/billing/services.py)."""

import threading
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import connection, transaction
from django.http import Http404
from django.utils import timezone

from apps.accounts.models import Role
from apps.billing.models import Bill, BillCounter, number_from
from apps.billing.selectors import bill_sheet, financial_year_of
from apps.billing.services import NotOpen, TotalChanged, settle_bill
from apps.billing.tests.conftest import Place, payments, refused
from apps.billing.tests.factories import BillCounterFactory
from apps.core.tests.postgresql import wait_for_a_lock
from apps.jobs.models import JobCard, JobCardStatus, JobCardStep, StepKind
from apps.jobs.services import cancel_job_card
from apps.vehicles.models import CarBrand, CarModel, Customer
from apps.workshops.tests.factories import BranchFactory

pytestmark = pytest.mark.django_db


def bills(place):
    return Bill.objects.for_workshop(place.workshop)


def this_year_number(count):
    return number_from(financial_year_of(timezone.localdate()), count)


def test_settle_14_19_the_rest_of_the_bill_is_the_discount(office):
    card = office.card(labour="43000")

    bill = office.settle(card, cash="40000")

    assert bill.discount == Decimal("3000.00")
    assert payments(bill) == {"cash": Decimal("40000.00")}
    card.refresh_from_db()
    assert bill_sheet(office.workshop, office.branch, card).net == Decimal("40000.00")


def test_settle_19_a_bill_paid_in_full_has_no_discount(office):
    card = office.card(labour="43000")

    assert office.settle(card, upi="43000").discount == Decimal("0")


def test_settle_15_two_methods_are_two_payments(office):
    card = office.card(labour="43000")

    bill = office.settle(card, cash="20000", upi="20000")

    assert payments(bill) == {"cash": Decimal("20000.00"), "upi": Decimal("20000.00")}
    assert bill.discount == Decimal("3000.00")


def test_settle_15_every_method_may_be_used_once(office):
    card = office.card(labour="43000")

    bill = office.settle(card, cash="1000", upi="2000", card="3000", bank_transfer="4000")

    assert set(payments(bill)) == {"cash", "upi", "card", "bank_transfer"}
    assert bill.discount == Decimal("33000.00")


def test_settle_23_settling_ends_the_job_card_with_its_step(office):
    card = office.card()

    office.settle(card)

    card.refresh_from_db()
    assert card.status == JobCardStatus.SETTLED
    step = JobCardStep.objects.get(job_card=card, kind=StepKind.SETTLED)
    assert step.by == office.by
    assert step.mechanic == card.lead_mechanic


def test_settle_23_its_car_is_free_for_a_new_card_at_once(office):
    card = office.card()
    office.settle(card)

    office.card(car=card.car)

    assert JobCard.objects.filter(car=card.car, status=JobCardStatus.OPEN).count() == 1


def test_settle_22_the_bill_is_dated_the_date_paid(owner):
    card = owner.card(admitted_date=date(2026, 6, 1))

    bill = owner.settle(card, paid_on=date(2026, 6, 4))

    assert bill.date == date(2026, 6, 4)


def test_settle_22_the_bill_keeps_who_settled_it_and_the_moment_beside_its_date(office):
    today = timezone.localdate()
    card = office.card(admitted_date=today - timedelta(days=5))
    before = timezone.now()

    bill = office.settle(card, paid_on=today - timedelta(days=2))

    bill.refresh_from_db()
    assert bill.settled_by == office.by
    assert before <= bill.settled_at <= timezone.now()
    # A back-dated bill keeps nothing more: the day it is dated and the moment it was typed
    # (CHANGE-17).
    assert bill.date == today - timedelta(days=2)


def test_settle_3_the_total_is_worked_out_from_the_card_each_time_and_never_stored(office):
    card = office.card(labour="43000")
    JobCard.objects.filter(pk=card.pk).update(labour=Decimal("45000"))
    card.refresh_from_db()

    assert bill_sheet(office.workshop, office.branch, card).total == Decimal("45000.00")
    assert "total" not in {field.name for field in Bill._meta.get_fields()}


def test_settle_16_a_bill_needs_at_least_one_payment(office):
    card = office.card()

    words = refused(
        lambda: settle_bill(
            office.workshop,
            office.branch,
            card.pk,
            uuid.uuid7(),
            office.by,
            paid_on=timezone.localdate(),
            payments={},
            total_seen=card.labour,
        )
    )

    assert words == {"__all__": ["Type what the customer paid, in at least one box."]}
    assert not bills(office).exists()


@pytest.mark.parametrize("amount", ["0", "-5"])
def test_settle_16_a_payment_is_above_zero(office, amount):
    card = office.card()

    words = refused(lambda: office.settle(card, cash=amount))

    assert words == {"__all__": ["Type an amount above zero."]}


def test_settle_17_payments_above_the_total_are_refused_naming_the_total(office):
    card = office.card(labour="43000")

    words = refused(lambda: office.settle(card, cash="25000", upi="20000"))

    assert words == {
        "__all__": ["The payments come to 45,000.00, more than the total of 43,000.00."]
    }
    card.refresh_from_db()
    assert card.status == JobCardStatus.OPEN


def test_settle_18_a_bill_of_zero_is_never_settled(office):
    card = office.card(labour="0")

    words = refused(lambda: office.settle(card, cash="100"))

    assert words == [
        "This bill comes to 0.00, so there is nothing to settle. Add the labour charge, or "
        "cancel the job card with its reason."
    ]


def test_settle_21_a_date_paid_in_the_future_is_refused(owner):
    card = owner.card()

    words = refused(lambda: owner.settle(card, paid_on=timezone.localdate() + timedelta(days=1)))

    assert words == {"paid_on": ["This day is in the future. Check the year."]}


def test_settle_21_office_may_date_it_three_days_back_and_no_further(office):
    today = timezone.localdate()
    card = office.card(admitted_date=today - timedelta(days=10))

    assert office.settle(card, paid_on=today - timedelta(days=3)).date == today - timedelta(days=3)
    second = office.card(admitted_date=today - timedelta(days=10))
    words = refused(lambda: office.settle(second, paid_on=today - timedelta(days=4)))
    assert list(words) == ["paid_on"]
    assert "Ask an owner" in words["paid_on"][0]


def test_settle_21_an_owner_may_date_it_any_day(owner):
    card = owner.card(admitted_date=date(2025, 1, 2))

    assert owner.settle(card, paid_on=date(2025, 1, 2)).date == date(2025, 1, 2)


def test_settle_21_the_date_paid_is_never_before_the_car_came_in(owner):
    card = owner.card(admitted_date=date(2026, 6, 10))

    words = refused(lambda: owner.settle(card, paid_on=date(2026, 6, 9)))

    assert words == {"paid_on": ["The date paid cannot be before the car came in, on 10 Jun 2026."]}


def test_settle_17_21_each_box_says_what_is_wrong_with_it_at_once(owner):
    card = owner.card(labour="1000", admitted_date=date(2026, 6, 10))

    words = refused(lambda: owner.settle(card, paid_on=date(2026, 6, 9), cash="2000"))

    assert set(words) == {"__all__", "paid_on"}


def test_settle_28_29_numbers_count_up_in_a_branch(office):
    first, second = office.card(), office.card()

    assert office.settle(first).number == this_year_number(1)
    assert office.settle(second).number == this_year_number(2)


def test_settle_29_30_the_count_starts_again_each_financial_year_from_the_bills_date(owner):
    march = owner.card(admitted_date=date(2026, 3, 30))
    april = owner.card(admitted_date=date(2026, 3, 30))
    late_march = owner.card(admitted_date=date(2026, 3, 30))

    assert owner.settle(march, paid_on=date(2026, 3, 31)).number == "INV-25-26-0001"
    assert owner.settle(april, paid_on=date(2026, 4, 1)).number == "INV-26-27-0001"
    # Dated 31 March and typed in April: the next number of the year that ended (SETTLE-30).
    assert owner.settle(late_march, paid_on=date(2026, 3, 31)).number == "INV-25-26-0002"


def test_settle_29_a_settle_that_fails_uses_no_number(office):
    card = office.card(labour="43000")
    refused(lambda: office.settle(card, cash="50000"))

    assert office.settle(card).number == this_year_number(1)


def test_settle_29_each_branch_has_its_own_counter(office):
    there = BranchFactory(workshop=office.workshop)
    office.settle(office.card())

    counters = BillCounter.objects.for_workshop(office.workshop)
    assert counters.count() == 1
    assert counters.get().branch == office.branch
    assert counters.get().branch != there


def test_settle_32_a_second_place_cannot_settle_before_it_has_its_own_letters(office):
    office.settle(office.card())
    there = BranchFactory(workshop=office.workshop)
    card_there = office.card(branch=there)

    words = refused(lambda: office.settle(card_there))

    assert "Another bill of this workshop has this number." in str(words)
    card_there.refresh_from_db()
    assert card_there.status == JobCardStatus.OPEN
    assert not BillCounter.objects.for_workshop(office.workshop).for_branch(there).exists()


def test_settle_25_a_double_tap_settles_once_and_shows_the_first_bill(office):
    card = office.card()
    key = uuid.uuid7()

    first = office.settle(card, key=key, cash="40000")
    again = office.settle(card, key=key, cash="1")

    assert again == first
    assert bills(office).count() == 1
    assert BillCounter.objects.for_workshop(office.workshop).get().last_number == 1
    assert payments(first) == {"cash": Decimal("40000.00")}


def test_settle_25_a_key_of_another_cards_bill_is_not_found(office):
    first = office.card()
    key = uuid.uuid7()
    office.settle(first, key=key)

    with pytest.raises(Http404):
        office.settle(office.card(), key=key)


def test_settle_25_a_key_of_another_workshops_bill_is_not_found(office):
    theirs = Place(Role.OFFICE)
    key = uuid.uuid7()
    theirs.settle(theirs.card(), key=key)

    with pytest.raises(Http404):
        office.settle(office.card(), key=key)


def test_settle_25_a_card_settled_from_another_page_is_refused(office):
    card = office.card()
    office.settle(card)

    with pytest.raises(NotOpen):
        office.settle(card)
    assert bills(office).count() == 1


def test_settle_4_a_cancelled_card_is_never_settled(office):
    card = office.card()
    cancel_job_card(office.workshop, office.branch, card.pk, office.by, "Customer took the car")

    with pytest.raises(NotOpen):
        office.settle(card)


def test_settle_26_a_total_that_moved_since_it_was_shown_is_refused(office):
    card = office.card(labour="45000")

    with pytest.raises(TotalChanged) as moved:
        office.settle(card, total_seen="43000")

    assert moved.value.total == Decimal("45000.00")
    assert not bills(office).exists()


def test_settle_34_35_the_bill_keeps_its_copy_whatever_the_records_do_later(office):
    customer = Customer.objects.create(workshop=office.workshop, name="Ravi Menon")
    card = office.card(customer=customer)
    bill = office.settle(card)
    model = card.car.car_model
    printed = ("Ravi Menon", model.brand.name, model.name)

    Customer.objects.filter(pk=customer.pk).update(name="Ravi M")
    CarModel.objects.filter(pk=model.pk).update(name="530d")
    CarBrand.objects.filter(pk=model.brand_id).update(name="Renamed")

    bill.refresh_from_db()
    assert (bill.customer_name, bill.brand, bill.car_model) == printed
    card = JobCard.objects.select_related("car__car_model__brand", "customer").get(pk=card.pk)
    sheet = bill_sheet(office.workshop, office.branch, card)
    assert (sheet.customer_name, sheet.brand, sheet.car_model) == printed


def test_settle_35_a_preview_reads_the_records_as_they_are_now(office):
    customer = Customer.objects.create(workshop=office.workshop, name="Ravi Menon")
    card = office.card(customer=customer)
    Customer.objects.filter(pk=customer.pk).update(name="Ravi M")

    card = JobCard.objects.select_related("car__car_model__brand", "customer").get(pk=card.pk)
    assert bill_sheet(office.workshop, office.branch, card).customer_name == "Ravi M"


@pytest.mark.django_db(transaction=True)
def test_settle_25_two_settles_of_one_card_at_one_moment_make_one_bill():
    place = Place(Role.OFFICE)
    card = place.card()
    answers = []

    def send():
        try:
            answers.append(place.settle(card, key=uuid.uuid7()))
        except NotOpen as ended:
            answers.append(ended)
        finally:
            connection.close()

    threads = [threading.Thread(target=send) for _ in range(2)]
    with transaction.atomic():
        # The test holds the card, so both settles start before either can end it.
        JobCard.objects.select_for_update().get(pk=card.pk)
        for thread in threads:
            thread.start()
        wait_for_a_lock(2)
    for thread in threads:
        thread.join()

    assert sorted(type(answer).__name__ for answer in answers) == ["Bill", "NotOpen"]
    assert Bill.objects.for_workshop(place.workshop).count() == 1


@pytest.mark.django_db(transaction=True)
def test_settle_29_two_cards_settled_at_one_moment_never_take_one_number():
    place = Place(Role.OFFICE)
    cards = [place.card(), place.card()]
    year = financial_year_of(timezone.localdate())
    BillCounterFactory(workshop=place.workshop, branch=place.branch, financial_year=year)

    def send(card):
        try:
            place.settle(card)
        finally:
            connection.close()

    threads = [threading.Thread(target=send, args=(card,)) for card in cards]
    with transaction.atomic():
        # The test holds the number's row, so both settles reach it before either takes one.
        BillCounter.objects.for_workshop(place.workshop).select_for_update().get()
        for thread in threads:
            thread.start()
        wait_for_a_lock(2)
    for thread in threads:
        thread.join()

    numbers = sorted(Bill.objects.for_workshop(place.workshop).values_list("number", flat=True))
    assert numbers == [this_year_number(1), this_year_number(2)]


@pytest.mark.django_db(transaction=True)
def test_settle_25_one_key_sent_for_two_cards_at_one_moment_settles_only_one():
    """A hand-made address sends one bill's key for two cards. Each settle locks its own card,
    so neither waits for the other, and neither finds the key saved yet: they meet at the
    number's lock. The second is not found, and nothing of it is saved."""
    place = Place(Role.OFFICE)
    cards = {"cash": place.card(), "upi": place.card()}
    year = financial_year_of(timezone.localdate())
    BillCounterFactory(workshop=place.workshop, branch=place.branch, financial_year=year)
    key = uuid.uuid7()
    answers = {}

    def send(method):
        try:
            answers[method] = place.settle(cards[method], key=key, **{method: "40000"})
        except Http404 as refused:
            answers[method] = refused
        finally:
            connection.close()

    threads = [threading.Thread(target=send, args=(method,)) for method in cards]
    with transaction.atomic():
        # The test holds the number's lock, so both settles get past the key's question first.
        BillCounter.objects.for_workshop(place.workshop).select_for_update().get()
        for thread in threads:
            thread.start()
        wait_for_a_lock(2)
    for thread in threads:
        thread.join()

    (bill,) = Bill.objects.for_workshop(place.workshop)
    (won,) = [method for method, answer in answers.items() if isinstance(answer, Bill)]
    (lost,) = [method for method, answer in answers.items() if isinstance(answer, Http404)]
    assert bill.job_card_id == cards[won].pk
    assert payments(bill) == {won: Decimal("40000.00")}
    cards[lost].refresh_from_db()
    assert cards[lost].status == JobCardStatus.OPEN
    # The second settle's number went back with it (SETTLE-29).
    assert BillCounter.objects.for_workshop(place.workshop).get().last_number == 1

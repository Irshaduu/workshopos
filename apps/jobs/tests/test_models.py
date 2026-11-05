"""What PostgreSQL itself holds for a job card and its rows (apps/jobs/models.py)."""

from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction

from apps.jobs.models import ConcernStatus, JobCardStatus, StepKind, number_from
from apps.jobs.tests.factories import (
    ConcernFactory,
    JobCardFactory,
    JobCardStepFactory,
    JobLineFactory,
    NumberCounterFactory,
)
from apps.staff.tests.factories import StaffMemberFactory
from apps.vehicles.tests.factories import CarFactory, CustomerFactory
from apps.workshops.tests.factories import BranchFactory, WorkshopFactory, first_branch

pytestmark = pytest.mark.django_db


def refused_by_postgresql(make):
    """Asks at once for the checks that wait for the end of the transaction, like a link's."""
    with pytest.raises(IntegrityError), transaction.atomic():
        make()
        connection.check_constraints()


def cancelled(**values):
    return JobCardFactory(status=JobCardStatus.CANCELLED, cancel_reason="No work done", **values)


# One open card per car.


def test_job_4_a_car_has_one_open_job_card():
    first = JobCardFactory()

    refused_by_postgresql(lambda: JobCardFactory(workshop=first.workshop, car=first.car))


def test_job_4_even_in_another_branch_of_its_workshop():
    first = JobCardFactory()
    there = BranchFactory(workshop=first.workshop)

    refused_by_postgresql(
        lambda: JobCardFactory(workshop=first.workshop, branch=there, car=first.car)
    )


def test_job_4_a_cancelled_card_does_not_count():
    gone = cancelled()

    assert JobCardFactory(workshop=gone.workshop, car=gone.car).is_open


# The number.


@pytest.mark.parametrize(
    ("count", "number"),
    [(1, "JC-0001"), (27, "JC-0027"), (9999, "JC-9999"), (10000, "JC-10000")],
)
def test_job_5_a_number_has_at_least_four_digits_and_grows(count, number):
    assert number_from(count) == number


def test_job_7_a_number_is_unique_in_its_branch():
    first = JobCardFactory(number="JC-0001")

    refused_by_postgresql(lambda: JobCardFactory(workshop=first.workshop, number="JC-0001"))


def test_job_9_each_branch_counts_on_its_own():
    first = JobCardFactory(number="JC-0001")
    there = BranchFactory(workshop=first.workshop)

    assert JobCardFactory(workshop=first.workshop, branch=there, number="JC-0001")


def test_job_6_one_counter_per_branch():
    counter = NumberCounterFactory()

    refused_by_postgresql(
        lambda: NumberCounterFactory(workshop=counter.workshop, branch=counter.branch)
    )


# What a visit holds.


@pytest.mark.parametrize("mileage", [0, 2_000_001])
def test_job_22_a_mileage_out_of_range_is_refused(mileage):
    refused_by_postgresql(lambda: JobCardFactory(mileage=mileage))


@pytest.mark.parametrize("mileage", [None, 1, 132022, 2_000_000])
def test_job_22_a_mileage_in_range_or_none_is_fine(mileage):
    assert JobCardFactory(mileage=mileage).mileage == mileage


def test_job_32_a_labour_charge_may_be_zero_and_is_never_negative():
    assert JobCardFactory(labour=Decimal("0")).labour == 0
    assert JobCardFactory().labour == 0

    # The column refuses it before PostgreSQL does (ADR-0029). tests/test_money.py checks that
    # PostgreSQL has its own check too.
    with pytest.raises(ValueError, match="cannot be negative"):
        JobCardFactory(labour=Decimal("-1"))


@pytest.mark.parametrize("plate", ["KL 10", "kl10", ""])
def test_job_13_a_visits_plate_has_the_one_spelling(plate):
    refused_by_postgresql(lambda: JobCardFactory(plate=plate))


def test_job_50_a_cancelled_card_has_a_reason_and_an_open_card_has_none():
    refused_by_postgresql(lambda: JobCardFactory(status=JobCardStatus.CANCELLED))
    refused_by_postgresql(lambda: JobCardFactory(status=JobCardStatus.CANCELLED, cancel_reason=" "))
    refused_by_postgresql(lambda: JobCardFactory(cancel_reason="No work done"))


def test_job_3_a_status_is_known():
    refused_by_postgresql(lambda: JobCardFactory(status="lost"))


# The links.


def test_a_card_never_links_to_another_workshops_records():
    ours = WorkshopFactory()

    refused_by_postgresql(lambda: JobCardFactory(workshop=ours, car=CarFactory()))
    refused_by_postgresql(lambda: JobCardFactory(workshop=ours, customer=CustomerFactory()))
    refused_by_postgresql(lambda: JobCardFactory(workshop=ours, lead_mechanic=StaffMemberFactory()))


def test_a_row_never_links_to_another_workshops_card():
    ours = WorkshopFactory()
    theirs = JobCardFactory()

    refused_by_postgresql(lambda: ConcernFactory(workshop=ours, job_card=theirs))
    refused_by_postgresql(lambda: JobLineFactory(workshop=ours, job_card=theirs))
    refused_by_postgresql(lambda: JobCardStepFactory(workshop=ours, job_card=theirs))


def test_job_2_a_card_knows_its_branch():
    card = JobCardFactory()

    assert card.branch == first_branch(card)


# The rows.


@pytest.mark.parametrize("factory", [ConcernFactory, JobLineFactory])
def test_job_37_the_same_words_twice_on_one_card_are_refused_whatever_the_capitals(factory):
    row = factory(text="Oil leak")

    refused_by_postgresql(
        lambda: factory(workshop=row.workshop, job_card=row.job_card, text="OIL LEAK")
    )


@pytest.mark.parametrize("factory", [ConcernFactory, JobLineFactory])
def test_job_37_the_same_words_on_another_card_are_fine(factory):
    row = factory(text="Oil leak")

    assert factory(workshop=row.workshop, text="Oil leak").job_card != row.job_card


@pytest.mark.parametrize("factory", [ConcernFactory, JobLineFactory])
def test_a_row_never_has_blank_words(factory):
    refused_by_postgresql(lambda: factory(text="  "))


def test_job_33_a_new_concern_is_pending_and_a_status_is_known():
    assert ConcernFactory().status == ConcernStatus.PENDING

    refused_by_postgresql(lambda: ConcernFactory(status="waiting"))


def test_job_38_rows_stay_in_the_order_they_were_added():
    card = JobCardFactory()
    words = ["Zebra noise", "Apple noise", "Mango noise"]
    for text in words:
        ConcernFactory(workshop=card.workshop, job_card=card, text=text)
        JobLineFactory(workshop=card.workshop, job_card=card, text=text)

    assert [row.text for row in card.concerns.all()] == words
    assert [row.text for row in card.job_lines.all()] == words


# The steps.


def test_job_39_a_step_about_a_concern_names_it_and_only_such_a_step_does():
    concern = ConcernFactory()
    card = concern.job_card

    refused_by_postgresql(
        lambda: JobCardStepFactory(
            workshop=card.workshop, job_card=card, kind=StepKind.CONCERN_FIXED
        )
    )
    refused_by_postgresql(
        lambda: JobCardStepFactory(
            workshop=card.workshop, job_card=card, kind=StepKind.CAR_IN, concern=concern
        )
    )
    assert JobCardStepFactory(
        workshop=card.workshop, job_card=card, kind=StepKind.CONCERN_FIXED, concern=concern
    )


def test_job_39_a_kind_is_known():
    refused_by_postgresql(lambda: JobCardStepFactory(kind="lost"))


def test_job_41_removing_a_concern_removes_its_steps():
    concern = ConcernFactory()
    card = concern.job_card
    JobCardStepFactory(workshop=card.workshop, job_card=card)
    JobCardStepFactory(
        workshop=card.workshop, job_card=card, kind=StepKind.CONCERN_FIXED, concern=concern
    )

    concern.delete()

    assert [step.kind for step in card.steps.all()] == [StepKind.CAR_IN]

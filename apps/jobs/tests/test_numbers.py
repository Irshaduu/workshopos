"""A job card's number (JOB-5 to JOB-9), from its locked counter (apps/jobs/services.py)."""

import threading
import uuid
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.jobs.models import JobCard, JobCardStatus, NumberCounter
from apps.jobs.services import cancel_job_card, change_job_card, make_job_card
from apps.vehicles.models import Car
from apps.workshops.models import Branch
from apps.workshops.tests.factories import BranchFactory, WorkshopFactory

pytestmark = pytest.mark.django_db


def typed(plate, **more):
    return {
        "plate": plate,
        "brand": "BMW",
        "car_model": "520d",
        "admitted_date": timezone.localdate(),
        **more,
    }


@pytest.fixture
def place():
    workshop = WorkshopFactory()
    return workshop, Branch.objects.for_workshop(workshop).first(), UserFactory()


def make(place, plate="KL10AA1000", key=None, **more):
    workshop, branch, by = place
    return make_job_card(workshop, branch, key or uuid.uuid7(), by, typed=typed(plate, **more))


def counter_of(place):
    workshop, branch, _by = place
    return NumberCounter.objects.for_workshop(workshop).for_branch(branch).get()


def test_job_5_the_first_card_is_one_and_the_next_follows(place):
    assert make(place, "KL10AA1000").number == "JC-0001"
    assert make(place, "KL10AA1001").number == "JC-0002"


def test_job_5_it_grows_past_four_digits(place):
    make(place, "KL10AA1000")
    NumberCounter.objects.filter(pk=counter_of(place).pk).update(last_number=9999)

    assert make(place, "KL10AA1001").number == "JC-10000"


def test_job_6_each_branch_counts_on_its_own(place):
    workshop, branch, by = place
    there = BranchFactory(workshop=workshop)

    make(place, "KL10AA1000")
    other = make_job_card(workshop, there, uuid.uuid7(), by, typed=typed("KL10AA1001"))

    assert other.number == "JC-0001"


def test_job_6_it_never_restarts_with_the_year(place):
    earlier = timezone.localdate() - timedelta(days=800)

    make(place, "KL10AA1000")

    assert make(place, "KL10AA1001", admitted_date=earlier).number == "JC-0002"


def test_job_6_a_save_that_fails_uses_no_number(place):
    make(place, "KL10AA1000")

    with pytest.raises(ValidationError):
        make(place, "KL10AA1000")
    with pytest.raises(ValidationError):
        make(place, "KL10AA1001", vin="WBA")

    assert make(place, "KL10AA1002").number == "JC-0002"


def test_job_6_a_refused_card_leaves_no_car_behind(place):
    workshop, _branch, _by = place

    with pytest.raises(ValidationError):
        make(place, "KL10AA1001", vin="WBA")

    assert not Car.objects.for_workshop(workshop).exists()


def test_job_6_a_double_tap_uses_no_number(place):
    key = uuid.uuid7()

    first = make(place, key=key)
    second = make(place, key=key)

    assert second == first
    assert counter_of(place).last_number == 1


def test_job_7_it_never_changes_when_the_admitted_date_moves(place):
    workshop, branch, by = place
    card = make(place)

    change_job_card(
        workshop,
        branch,
        card.pk,
        by,
        changes={"admitted_date": timezone.localdate() - timedelta(days=800)},
    )

    card.refresh_from_db()
    assert card.number == "JC-0001"


def test_job_7_a_cancelled_cards_number_stays_and_is_never_given_again(place):
    workshop, branch, by = place
    card = make(place, "KL10AA1000")

    cancel_job_card(workshop, branch, card.pk, by, "Customer left")

    card.refresh_from_db()
    assert (card.status, card.number) == (JobCardStatus.CANCELLED, "JC-0001")
    assert make(place, "KL10AA1001").number == "JC-0002"


@pytest.mark.django_db(transaction=True)
def test_job_6_two_cards_saved_at_one_moment_never_take_one_number():
    workshop = WorkshopFactory()
    branch = Branch.objects.for_workshop(workshop).first()
    by = UserFactory()
    barrier = threading.Barrier(2)

    def send(plate):
        barrier.wait()
        try:
            make_job_card(workshop, branch, uuid.uuid7(), by, typed=typed(plate))
        finally:
            connection.close()

    threads = [threading.Thread(target=send, args=(plate,)) for plate in ("KL10AA1", "KL10AA2")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    cards = JobCard.objects.for_workshop(workshop).for_branch(branch)
    assert sorted(card.number for card in cards) == ["JC-0001", "JC-0002"]


@pytest.mark.django_db(transaction=True)
def test_job_42_a_double_tap_at_one_moment_makes_one_card_and_uses_one_number():
    workshop = WorkshopFactory()
    branch = Branch.objects.for_workshop(workshop).first()
    by = UserFactory()
    key = uuid.uuid7()
    barrier = threading.Barrier(2)
    answers = []

    def send():
        barrier.wait()
        try:
            answers.append(make_job_card(workshop, branch, key, by, typed=typed("KL10AA1000")))
        finally:
            connection.close()

    threads = [threading.Thread(target=send) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert answers[0] == answers[1]
    assert JobCard.objects.for_workshop(workshop).count() == 1
    assert NumberCounter.objects.for_workshop(workshop).get().last_number == 1

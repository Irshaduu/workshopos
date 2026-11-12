"""A job card's end with its bill (SETTLE-10 to SETTLE-13, SETTLE-23, SETTLE-27, SETTLE-37):
what jobs gives billing, at its selectors and services. The bill itself is billing's."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.jobs.models import ConcernStatus, JobCardStatus, JobCardStep, StepKind
from apps.jobs.selectors import settled_step, unfilled
from apps.jobs.services import cancel_job_card, end_as_settled, lock_job_card
from apps.jobs.tests.cards import change
from apps.jobs.tests.factories import ConcernFactory, JobCardFactory, JobLineFactory
from apps.staff.tests.factories import StaffMemberFactory

pytestmark = pytest.mark.django_db


def filled_card(place, **values):
    """A card with everything filled: a mileage, a lead mechanic, a job and its charge."""
    workshop, branch, _by = place
    values.setdefault("mileage", 45230)
    values.setdefault("lead_mechanic", StaffMemberFactory(workshop=workshop))
    values.setdefault("labour", Decimal("1000"))
    card = JobCardFactory(workshop=workshop, branch=branch, **values)
    JobLineFactory(workshop=workshop, job_card=card)
    return card


def not_filled(place, card):
    return [(thing.kind, thing.missing, thing.name) for thing in unfilled(place[0], card)]


def settled(place, card):
    with transaction.atomic():
        end_as_settled(lock_job_card(place[0], place[1], card.pk), place[2])
    card.refresh_from_db()
    return card


def test_settle_10_a_filled_card_has_nothing_to_say(place):
    assert not_filled(place, filled_card(place)) == []


def test_settle_10_11_each_empty_box_of_the_card_is_one_short_phrase(place):
    card = filled_card(place, mileage=None, lead_mechanic=None, labour=Decimal("0"))

    assert not_filled(place, card) == [
        ("mileage", "no mileage", ""),
        ("mechanic", "no lead mechanic", ""),
        ("labour", "no labour charge", ""),
    ]


def test_settle_10_a_labour_charge_of_0_with_no_job_is_not_asked_for(place):
    workshop, branch, _by = place
    card = JobCardFactory(
        workshop=workshop,
        branch=branch,
        mileage=1,
        lead_mechanic=StaffMemberFactory(workshop=workshop),
        labour=Decimal("0"),
    )

    assert not_filled(place, card) == []


def test_settle_10_11_each_concern_not_fixed_is_named_by_its_own_words(place):
    card = filled_card(place)
    workshop = place[0]
    ConcernFactory(workshop=workshop, job_card=card, text="AC not cooling")
    ConcernFactory(workshop=workshop, job_card=card, text="Brake noise", status=ConcernStatus.FIXED)
    ConcernFactory(workshop=workshop, job_card=card, text="Oil leak", status=ConcernStatus.WORKING)

    assert not_filled(place, card) == [
        ("concern", "not fixed", "AC not cooling"),
        ("concern", "not fixed", "Oil leak"),
    ]


def test_settle_23_a_settled_card_has_its_step_with_who_and_the_mechanic(place):
    card = settled(place, filled_card(place))

    assert card.status == JobCardStatus.SETTLED
    step = settled_step(place[0], card)
    assert (step.kind, step.by, step.mechanic) == (StepKind.SETTLED, place[2], card.lead_mechanic)


def test_settle_23_only_an_open_card_is_settled(place):
    card = settled(place, filled_card(place))

    with pytest.raises(ValueError), transaction.atomic():
        end_as_settled(lock_job_card(place[0], place[1], card.pk), place[2])
    assert JobCardStep.objects.filter(job_card=card, kind=StepKind.SETTLED).count() == 1


def test_settle_27_a_change_that_reaches_a_settled_card_saves_nothing(place):
    card = settled(place, filled_card(place))

    with pytest.raises(ValidationError) as refused:
        change(place, card, changes={"labour": Decimal("5")})

    assert refused.value.messages == ["This job card is settled, so nothing was saved."]
    card.refresh_from_db()
    assert card.labour == Decimal("1000.00")


def test_settle_37_a_settled_card_is_never_cancelled(place):
    card = settled(place, filled_card(place))

    cancel_job_card(place[0], place[1], card.pk, place[2], "By mistake")

    card.refresh_from_db()
    assert (card.status, card.cancel_reason) == (JobCardStatus.SETTLED, "")

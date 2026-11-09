"""Making and changing job cards in tests, through their services (apps/jobs/services.py)."""

import uuid
from datetime import timedelta

from django.utils import timezone

from apps.jobs.models import JobCard, JobCardStatus
from apps.jobs.services import change_job_card, make_job_card
from apps.jobs.tests.factories import JobCardFactory


def typed(plate="KL10AA1000", **more):
    """What a new card's form sends, with a BMW 520d unless told otherwise."""
    return {
        "plate": plate,
        "brand": "BMW",
        "car_model": "520d",
        "admitted_date": timezone.localdate(),
        **more,
    }


def make(place, key=None, concerns=(), job_lines=(), answers=(), **more):
    workshop, branch, by = place
    return make_job_card(
        workshop,
        branch,
        key or uuid.uuid7(),
        by,
        typed=typed(**more),
        concerns=concerns,
        job_lines=job_lines,
        answers=answers,
    )


def change(place, card, **more):
    workshop, branch, by = place
    return change_job_card(workshop, branch, card.pk, by, changes=more.pop("changes", {}), **more)


def fresh(card):
    return JobCard.objects.get(pk=card.pk)


def said(question, answer, car):
    """What a question's button sends (KNOWN-13)."""
    return f"{question}:{answer}:{car.pk}"


def visit(workshop, car, plate=None, days_ago=30, **values):
    """An earlier visit of the car, closed, that came with this plate."""
    return JobCardFactory(
        workshop=workshop,
        car=car,
        plate=plate or car.plate,
        status=JobCardStatus.CANCELLED,
        cancel_reason="Finished before this test",
        admitted_date=timezone.localdate() - timedelta(days=days_ago),
        **values,
    )

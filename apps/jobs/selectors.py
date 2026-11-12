"""Reads for jobs: rules that read data, never change it (ADR-0005)."""

from dataclasses import dataclass

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from apps.jobs.models import (
    Concern,
    ConcernStatus,
    JobCard,
    JobCardStatus,
    JobCardStep,
    JobLine,
    StepKind,
)
from apps.vehicles.selectors import car_with_plate

#: What a job card's page and the live board's rows show, in one query.
CARD_LINKS = ("car__car_model__brand", "customer", "lead_mechanic")
#: A car's visits, newest first: by the day it came in, then by the order cards were made.
NEWEST_FIRST = ("-admitted_date", "-id")


def open_job_cards(workshop, branch):
    """Every open job card of this branch, newest first (JOB-61)."""
    return (
        JobCard.objects.for_workshop(workshop)
        .for_branch(branch)
        .filter(status=JobCardStatus.OPEN)
        .select_related(*CARD_LINKS)
        .order_by("-id")
    )


def job_card(workshop, branch, key):
    """The job card with this key. Any other record answers "not found" (JOB-2)."""
    return get_object_or_404(
        JobCard.objects.for_workshop(workshop).for_branch(branch).select_related(*CARD_LINKS),
        pk=key,
    )


def saved_job_card(workshop, branch, key):
    """The job card saved under this key; None when none is. A form that makes a new
    record asks this first (JOB-42)."""
    return JobCard.objects.for_workshop(workshop).for_branch(branch).filter(pk=key).first()


def open_card_of(workshop, car):
    """The car's open job card, in any branch of its workshop; None when it has none (JOB-4)."""
    # not for_branch: one open job card per car stays workshop-wide (ADR-0028).
    return JobCard.objects.for_workshop(workshop).filter(car=car, status=JobCardStatus.OPEN).first()


def cancelled_step(workshop, card):
    """Who cancelled this card, and when (JOB-51)."""
    return _step_of(workshop, card, StepKind.CANCELLED)


def settled_step(workshop, card):
    """Who settled this card's bill, and when (SETTLE-23, SETTLE-36)."""
    return _step_of(workshop, card, StepKind.SETTLED)


def _step_of(workshop, card, kind):
    """The newest step of this kind, so a step that comes again later is read as it is now."""
    return (
        JobCardStep.objects.for_workshop(workshop)
        .filter(job_card=card, kind=kind)
        .select_related("by")
        .order_by("-id")
        .first()
    )


@dataclass(frozen=True)
class Unfilled:
    """One thing still not filled on a job card (SETTLE-11): what kind of thing, what is
    missing, and for a concern its own words. The card's own boxes have no name."""

    kind: str
    missing: str
    name: str = ""


def unfilled(workshop, card):
    """What is still not filled on this job card, in the order someone would fix it
    (SETTLE-10 to SETTLE-13): its own boxes, then each concern not marked Fixed. The settle
    box reads this one list, and the live report will too (Phase 6), so the two never
    disagree.

    A labour charge of 0 is asked for only when jobs are listed: a card with no jobs is a
    parts-only bill, where 0 is right (v1)."""
    found = []
    if card.mileage is None:
        found.append(Unfilled("mileage", _("no mileage")))
    if card.lead_mechanic_id is None:
        found.append(Unfilled("mechanic", _("no lead mechanic")))
    if not card.labour and JobLine.objects.for_workshop(workshop).filter(job_card=card).exists():
        found.append(Unfilled("labour", _("no labour charge")))
    found += [
        Unfilled("concern", _("not fixed"), concern.text)
        for concern in Concern.objects.for_workshop(workshop)
        .filter(job_card=card)
        .exclude(status=ConcernStatus.FIXED)
        .order_by("id")
    ]
    return found


def _visits(workshop, car):
    # not for_branch: a car's visits span its workshop's branches (ADR-0006, ADR-0028).
    return JobCard.objects.for_workshop(workshop).filter(car=car).order_by(*NEWEST_FIRST)


def car_for_plate(workshop, plate):
    """The car a tidied plate names; None when it names none (KNOWN-1).

    The car that has it today comes first. A plate no car has today, but that a job card came
    with, is an old plate: it names the car of the newest such card, because a car keeps its
    history when its plate changes.
    """
    car = car_with_plate(workshop, plate)
    if car is not None:
        return car
    # not for_branch: a car's visits span its workshop's branches (ADR-0006, ADR-0028).
    newest = (
        JobCard.objects.for_workshop(workshop)
        .filter(plate=plate)
        .select_related("car__car_model__brand")
        .order_by(*NEWEST_FIRST)
        .first()
    )
    return newest.car if newest is not None else None


def newest_visit(workshop, car, besides=None):
    """The car's newest job card other than `besides`, in any branch; None when it has none."""
    visits = _visits(workshop, car)
    if besides is not None:
        visits = visits.exclude(pk=besides.pk)
    return visits.first()


def has_other_visits(workshop, car, card):
    """Whether the car has a job card other than this one, of any state (KNOWN-10, KNOWN-15)."""
    return newest_visit(workshop, car, besides=card) is not None


def last_customer(workshop, car):
    """A car's customer today: the one on its newest job card that has one (JOB-29). None when
    no card has one."""
    newest = _visits(workshop, car).filter(customer__isnull=False).select_related("customer")
    card = newest.first()
    return card.customer if card is not None else None


@dataclass(frozen=True)
class KnownCar:
    """What the workshop knows about a typed plate, for a new job card (KNOWN-4 to KNOWN-9)."""

    car: object
    old: bool
    open_card: object
    customer: object


def known_car(workshop, plate, *, with_customer):
    """What a new job card may be filled with for this tidied plate; None for a plate that
    names no car (KNOWN-1, KNOWN-4).

    The customer is read only for a role whose form has the customer, so Floor's answer
    holds nothing about them (KNOWN-8).
    """
    car = car_for_plate(workshop, plate)
    if car is None:
        return None
    return KnownCar(
        car=car,
        old=car.plate != plate,
        open_card=open_card_of(workshop, car),
        customer=last_customer(workshop, car) if with_customer else None,
    )

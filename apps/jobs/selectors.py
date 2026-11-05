"""Reads for jobs: rules that read data, never change it (ADR-0005)."""

from django.shortcuts import get_object_or_404

from apps.jobs.models import JobCard, JobCardStatus, JobCardStep, StepKind

#: What a job card's page and the live board's rows show, in one query.
CARD_LINKS = ("car__car_model__brand", "customer", "lead_mechanic")


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
    return (
        JobCardStep.objects.for_workshop(workshop)
        .filter(job_card=card, kind=StepKind.CANCELLED)
        .select_related("by")
        .first()
    )

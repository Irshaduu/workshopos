"""Test data for jobs (factory-boy, ADR-0013)."""

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.accounts.tests.factories import UserFactory
from apps.jobs.models import Concern, JobCard, JobCardStep, JobLine, NumberCounter, StepKind
from apps.vehicles.tests.factories import CarFactory
from apps.workshops.tests.factories import WorkshopFactory, first_branch


class NumberCounterFactory(DjangoModelFactory):
    class Meta:
        model = NumberCounter

    workshop = factory.SubFactory(WorkshopFactory)
    branch = factory.LazyAttribute(first_branch)


class JobCardFactory(DjangoModelFactory):
    """An open job card, with its own car. To choose the branch, give the workshop too."""

    class Meta:
        model = JobCard

    workshop = factory.SubFactory(WorkshopFactory)
    branch = factory.LazyAttribute(first_branch)
    number = factory.Sequence(lambda n: f"JC-{n:04d}")
    car = factory.SubFactory(CarFactory, workshop=factory.SelfAttribute("..workshop"))
    plate = factory.LazyAttribute(lambda card: card.car.plate)
    admitted_date = factory.LazyFunction(timezone.localdate)


class ConcernFactory(DjangoModelFactory):
    class Meta:
        model = Concern

    workshop = factory.SubFactory(WorkshopFactory)
    job_card = factory.SubFactory(JobCardFactory, workshop=factory.SelfAttribute("..workshop"))
    text = factory.Sequence(lambda n: f"Concern {n}")


class JobLineFactory(DjangoModelFactory):
    class Meta:
        model = JobLine

    workshop = factory.SubFactory(WorkshopFactory)
    job_card = factory.SubFactory(JobCardFactory, workshop=factory.SelfAttribute("..workshop"))
    text = factory.Sequence(lambda n: f"Job {n}")


class JobCardStepFactory(DjangoModelFactory):
    class Meta:
        model = JobCardStep

    workshop = factory.SubFactory(WorkshopFactory)
    job_card = factory.SubFactory(JobCardFactory, workshop=factory.SelfAttribute("..workshop"))
    kind = StepKind.CAR_IN
    by = factory.SubFactory(UserFactory)

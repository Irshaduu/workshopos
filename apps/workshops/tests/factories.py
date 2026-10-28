"""Test data for workshops (factory-boy, ADR-0013)."""

import factory
from factory.django import DjangoModelFactory

from apps.workshops.models import Branch, Workshop


class WorkshopFactory(DjangoModelFactory):
    class Meta:
        model = Workshop

    name = factory.Sequence(lambda n: f"Workshop {n}")
    short_code = factory.Sequence(lambda n: f"w{n}")


class BranchFactory(DjangoModelFactory):
    class Meta:
        model = Branch

    workshop = factory.SubFactory(WorkshopFactory)
    name = factory.Sequence(lambda n: f"Branch {n}")

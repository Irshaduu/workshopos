"""Test data for workshops (factory-boy, ADR-0013)."""

import factory
from factory.django import DjangoModelFactory

from apps.workshops.models import Branch, Workshop


class WorkshopFactory(DjangoModelFactory):
    """A workshop with its first branch, like a real one (ADR-0006)."""

    class Meta:
        model = Workshop
        # The first branch saves itself; the workshop needs no second save.
        skip_postgeneration_save = True

    name = factory.Sequence(lambda n: f"Workshop {n}")
    short_code = factory.Sequence(lambda n: f"w{n}")
    first_branch = factory.RelatedFactory(
        "apps.workshops.tests.factories.BranchFactory", factory_related_name="workshop"
    )


class BranchFactory(DjangoModelFactory):
    class Meta:
        model = Branch

    # With no workshop given, the branch being made is its workshop's first.
    workshop = factory.SubFactory(WorkshopFactory, first_branch=None)
    name = factory.Sequence(lambda n: f"Branch {n}")

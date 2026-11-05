"""Test data for staff (factory-boy, ADR-0013)."""

import factory
from factory.django import DjangoModelFactory

from apps.staff.models import Designation, StaffMember
from apps.workshops.tests.factories import WorkshopFactory, first_branch


class StaffMemberFactory(DjangoModelFactory):
    """A staff member turned on. To choose the branch, give the workshop too."""

    class Meta:
        model = StaffMember

    workshop = factory.SubFactory(WorkshopFactory)
    branch = factory.LazyAttribute(first_branch)
    name = factory.Sequence(lambda n: f"Person {n}")
    designation = Designation.MECHANIC

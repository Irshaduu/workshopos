"""The workshop and its branches (apps/workshops/models.py, selectors.py)."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from apps.workshops.models import Branch, Workshop, WorkshopStatus
from apps.workshops.selectors import may_work
from apps.workshops.tests.factories import BranchFactory, WorkshopFactory


@pytest.mark.django_db
def test_a_new_workshop_may_work():
    assert may_work(WorkshopFactory())


def test_a_suspended_workshop_may_not_work():
    assert not may_work(WorkshopFactory.build(status=WorkshopStatus.SUSPENDED))


@pytest.mark.django_db
def test_postgresql_refuses_a_status_it_does_not_know():
    workshop = WorkshopFactory()

    with pytest.raises(IntegrityError), transaction.atomic():
        Workshop.objects.filter(pk=workshop.pk).update(status="closed")


@pytest.mark.django_db
def test_a_workshop_with_records_is_never_deleted():
    branch = BranchFactory()

    with pytest.raises(ProtectedError):
        branch.workshop.delete()


@pytest.mark.django_db
def test_a_branch_name_is_used_once_in_a_workshop_whatever_its_case():
    branch = BranchFactory(name="Main")
    again = Branch(workshop=branch.workshop, name="MAIN")

    with pytest.raises(ValidationError, match="already has a branch with this name"):
        again.full_clean()
    with pytest.raises(IntegrityError), transaction.atomic():
        again.save()


@pytest.mark.django_db
def test_two_workshops_may_each_have_a_branch_of_the_same_name():
    BranchFactory(name="Main")
    other = Branch(workshop=WorkshopFactory(), name="Main")

    other.full_clean()
    other.save()


@pytest.mark.django_db
def test_for_workshop_takes_only_a_workshop():
    workshop = WorkshopFactory()

    for wrong in [None, workshop.pk, "Workshop 1"]:
        with pytest.raises(TypeError, match="needs a Workshop"):
            Branch.objects.for_workshop(wrong)

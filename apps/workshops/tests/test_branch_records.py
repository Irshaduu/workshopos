"""Records with a branch (apps/workshops/models.py, ADR-0028)."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.utils.functional import SimpleLazyObject

from apps.workshops.tests.factories import BranchFactory, WorkshopFactory


@pytest.fixture
def place():
    """A workshop with two branches, and another workshop's branch."""
    workshop = WorkshopFactory(first_branch=None)
    here, there = BranchFactory(workshop=workshop), BranchFactory(workshop=workshop)
    return workshop, here, there, BranchFactory()


def test_a_branch_sees_only_its_own_records(planted, place):
    workshop, here, there, _elsewhere = place
    own = planted.objects.create(workshop=workshop, branch=here)
    planted.objects.create(workshop=workshop, branch=there)

    assert list(planted.objects.for_workshop(workshop).for_branch(here)) == [own]


def test_another_workshops_branch_finds_nothing(planted, place):
    workshop, here, _there, elsewhere = place
    planted.objects.create(workshop=workshop, branch=here)

    assert not planted.objects.for_workshop(workshop).for_branch(elsewhere).exists()


@pytest.mark.parametrize("not_a_branch", [None, "main", 1])
def test_for_branch_refuses_anything_but_a_branch(planted, not_a_branch):
    with pytest.raises(TypeError, match="needs a Branch"):
        planted.objects.for_workshop(WorkshopFactory()).for_branch(not_a_branch)


def test_for_branch_refuses_a_workshop(planted, place):
    workshop, *_rest = place

    with pytest.raises(TypeError, match="needs a Branch"):
        planted.objects.for_workshop(workshop).for_branch(workshop)


def test_for_branch_takes_the_branch_a_request_carries(planted, place):
    # request.branch is read only when a page asks for it (apps/accounts/middleware.py).
    workshop, here, *_rest = place
    own = planted.objects.create(workshop=workshop, branch=here)
    request_branch = SimpleLazyObject(lambda: here)

    assert list(planted.objects.for_workshop(workshop).for_branch(request_branch)) == [own]


def test_a_record_needs_a_branch(planted, place):
    workshop, *_rest = place

    with pytest.raises(ValidationError) as refused:
        planted(workshop=workshop).full_clean()

    assert list(refused.value.message_dict) == ["branch"]


def test_a_record_keeps_its_workshop_pair_and_its_link_check(planted, place):
    workshop, _here, _there, elsewhere = place
    wrong = planted(workshop=workshop, branch=elsewhere)

    with pytest.raises(ValidationError, match="another workshop"):
        wrong.full_clean()
    with pytest.raises(IntegrityError, match="same_workshop"), transaction.atomic():
        wrong.save()
        connection.check_constraints()

    names = {constraint.name for constraint in planted._meta.constraints}
    assert names == {"workshops_planted_workshop_id", "workshops_planted_branch_same_workshop"}

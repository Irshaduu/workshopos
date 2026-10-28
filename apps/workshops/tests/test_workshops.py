"""The workshop and its branches (apps/workshops/models.py, selectors.py, admin.py)."""

import pytest
from django.contrib.admin.sites import site
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import ProtectedError

from apps.workshops.models import Branch, Workshop, WorkshopStatus
from apps.workshops.selectors import may_work
from apps.workshops.tests.factories import BranchFactory, WorkshopFactory


@pytest.mark.django_db
@pytest.mark.parametrize("code", ["a", "abcdefghi", "AB", "a-b", "a b", "ab.", ""])
def test_sign_8_a_short_code_is_2_to_8_small_letters_or_digits(code):
    workshop = WorkshopFactory()

    with pytest.raises(ValidationError):
        Workshop(name="Workshop A", short_code=code).full_clean()
    # PostgreSQL refuses it too: a check for the form, the column for the length.
    with pytest.raises(DatabaseError), transaction.atomic():
        Workshop.objects.filter(pk=workshop.pk).update(short_code=code)


@pytest.mark.django_db
@pytest.mark.parametrize("code", ["ab", "fd2026", "abcdefgh"])
def test_sign_8_a_good_short_code_is_taken(code):
    Workshop(name="Workshop A", short_code=code).full_clean()


@pytest.mark.django_db
def test_sign_8_no_two_workshops_on_a_server_share_a_short_code():
    WorkshopFactory(short_code="ab")
    again = Workshop(name="Workshop B", short_code="ab")

    with pytest.raises(ValidationError, match="already has this short code"):
        again.full_clean()
    with pytest.raises(IntegrityError), transaction.atomic():
        again.save()


def test_sign_8_the_admin_never_changes_a_short_code_once_the_workshop_is_made(rf):
    workshop_admin = site._registry[Workshop]
    request = rf.get("/")

    assert "short_code" not in workshop_admin.get_readonly_fields(request)
    assert "short_code" in workshop_admin.get_readonly_fields(request, WorkshopFactory.build())


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

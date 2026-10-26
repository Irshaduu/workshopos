"""The membership (apps/accounts/models.py) and finding it (selectors.py)."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from apps.accounts.models import Membership, Role
from apps.accounts.selectors import membership_of
from apps.accounts.tests.factories import MembershipFactory, UserFactory
from apps.workshops.tests.factories import WorkshopFactory


@pytest.mark.django_db
def test_an_account_belongs_to_one_workshop_for_now():
    member = MembershipFactory()
    second = Membership(workshop=WorkshopFactory(), user=member.user, role=Role.OWNER)

    with pytest.raises(ValidationError, match="already belongs to a workshop"):
        second.full_clean()
    with pytest.raises(IntegrityError), transaction.atomic():
        second.save()


@pytest.mark.django_db
def test_postgresql_refuses_a_role_it_does_not_know():
    member = MembershipFactory()

    with pytest.raises(IntegrityError), transaction.atomic():
        Membership.objects.filter(pk=member.pk).update(role="storekeeper")


@pytest.mark.django_db
@pytest.mark.parametrize("flag", ["is_staff", "is_superuser"])
def test_staff_and_superusers_are_never_members(flag):
    account = UserFactory(**{flag: True})
    membership = Membership(workshop=WorkshopFactory(), user=account, role=Role.OWNER)

    with pytest.raises(ValidationError, match="never members"):
        membership.full_clean()


@pytest.mark.django_db
def test_an_account_with_a_membership_is_never_deleted():
    member = MembershipFactory()

    with pytest.raises(ProtectedError):
        member.user.delete()


@pytest.mark.django_db
def test_a_membership_is_found_with_its_workshop_in_one_query(django_assert_num_queries):
    member = MembershipFactory()

    with django_assert_num_queries(1):
        found = membership_of(member.user)
        assert found.workshop == member.workshop


@pytest.mark.django_db
def test_staff_get_no_membership_whatever_the_data_says():
    member = MembershipFactory()
    member.user.is_staff = True
    member.user.save()

    assert membership_of(member.user) is None

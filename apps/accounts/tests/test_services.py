"""Creating a workshop (apps/accounts/services.py)."""

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import Membership, Role
from apps.accounts.services import create_workshop
from apps.accounts.tests.factories import MembershipFactory, UserFactory
from apps.workshops.models import Branch, Workshop


def nothing_saved():
    return (Workshop.objects.count(), Branch.objects.count()) == (0, 0)


@pytest.mark.django_db
def test_a_new_workshop_starts_with_its_branch_and_its_owner():
    owner = UserFactory()

    workshop = create_workshop(name="Workshop A", short_code="ab", branch_name="Main", owner=owner)

    assert [b.name for b in Branch.objects.for_workshop(workshop)] == ["Main"]
    membership = Membership.objects.for_workshop(workshop).get()
    assert (membership.user, membership.role) == (owner, Role.OWNER)


@pytest.mark.django_db
def test_a_superuser_never_owns_a_workshop_and_nothing_is_saved():
    with pytest.raises(ValidationError, match="never members"):
        create_workshop(
            name="Workshop A",
            short_code="ab",
            branch_name="Main",
            owner=UserFactory(is_superuser=True),
        )

    assert nothing_saved()


@pytest.mark.django_db
def test_an_account_in_a_workshop_cannot_own_a_second_one():
    member = MembershipFactory()
    before = Workshop.objects.count()

    with pytest.raises(ValidationError, match="already belongs to a workshop"):
        create_workshop(name="Workshop B", short_code="bb", branch_name="Main", owner=member.user)

    assert Workshop.objects.count() == before


@pytest.mark.django_db
@pytest.mark.parametrize(("name", "branch_name"), [("", "Main"), ("Workshop A", "")])
def test_a_workshop_and_its_branch_need_a_name(name, branch_name):
    with pytest.raises(ValidationError):
        create_workshop(name=name, short_code="ab", branch_name=branch_name, owner=UserFactory())

    assert nothing_saved()

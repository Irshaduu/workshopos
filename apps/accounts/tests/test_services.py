"""Creating a workshop (apps/accounts/services.py)."""

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import Membership, Role, User
from apps.accounts.services import create_workshop
from apps.accounts.tests.factories import UserFactory
from apps.workshops.models import Branch, Workshop

WORKSHOP_A = {
    "name": "Workshop A",
    "short_code": "ab",
    "branch_name": "Main",
    "owner_login_name": "ravi",
    "owner_email": "ravi@example.com",
}


def counts():
    return Workshop.objects.count(), Branch.objects.count(), User.objects.count()


@pytest.mark.django_db
def test_a_new_workshop_starts_with_its_branch_and_its_owner():
    workshop = create_workshop(**WORKSHOP_A)

    assert [b.name for b in Branch.objects.for_workshop(workshop)] == ["Main"]
    membership = Membership.objects.for_workshop(workshop).get()
    assert membership.role == Role.OWNER
    assert membership.user.email == "ravi@example.com"


@pytest.mark.django_db
def test_sign_3_the_first_owner_has_no_password():
    workshop = create_workshop(**WORKSHOP_A)

    owner = Membership.objects.for_workshop(workshop).get().user
    assert not owner.has_usable_password()


@pytest.mark.django_db
def test_sign_4_a_workshop_cannot_get_an_owner_without_an_email():
    with pytest.raises(ValidationError, match="needs an email"):
        create_workshop(**{**WORKSHOP_A, "owner_email": ""})

    assert counts() == (0, 0, 0)


@pytest.mark.django_db
def test_sign_7_the_owners_username_is_the_short_code_a_dot_and_a_login_name():
    workshop = create_workshop(**WORKSHOP_A)

    assert Membership.objects.for_workshop(workshop).get().user.username == "ab.ravi"


@pytest.mark.django_db
@pytest.mark.parametrize("login", ["Ravi", "ravi.k", "ra vi", "ravi-k", ""])
def test_sign_7_a_login_name_is_small_letters_and_digits_only(login):
    with pytest.raises(ValidationError, match="small letters and digits"):
        create_workshop(**{**WORKSHOP_A, "owner_login_name": login})

    assert counts() == (0, 0, 0)


@pytest.mark.django_db
def test_sign_9_an_email_another_account_has_in_any_capitals_is_refused():
    UserFactory(email="Ravi@Example.com")
    before = counts()

    with pytest.raises(ValidationError, match="already has this email"):
        create_workshop(**WORKSHOP_A)

    assert counts() == before


@pytest.mark.django_db
def test_a_taken_short_code_leaves_nothing_behind():
    create_workshop(**WORKSHOP_A)
    before = counts()

    with pytest.raises(ValidationError, match="already has this short code"):
        create_workshop(**{**WORKSHOP_A, "name": "Workshop B", "owner_email": "b@example.com"})

    assert counts() == before


@pytest.mark.django_db
@pytest.mark.parametrize(("name", "branch_name"), [("", "Main"), ("Workshop A", "")])
def test_a_workshop_and_its_branch_need_a_name(name, branch_name):
    with pytest.raises(ValidationError):
        create_workshop(**{**WORKSHOP_A, "name": name, "branch_name": branch_name})

    assert counts() == (0, 0, 0)

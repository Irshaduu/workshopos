"""The one backend every way in goes through (apps/accounts/backends.py)."""

import pytest
from asgiref.sync import async_to_sync
from django.contrib.auth import aauthenticate, authenticate

from apps.accounts.selectors import minutes_locked
from apps.accounts.services import count_wrong_password
from apps.accounts.tests.factories import PASSWORD, MembershipFactory, UserFactory


def floor_login():
    return MembershipFactory(workshop__short_code="ab", user__username="ab.floor").user


def owner_with_a_password():
    """An owner who somehow has a password, as v1's owners had."""
    owner = MembershipFactory(owner=True).user
    owner.set_password(PASSWORD)
    owner.save()
    return owner


@pytest.mark.django_db
def test_sign_6_office_and_floor_sign_in_with_their_username_and_password():
    floor = floor_login()

    assert authenticate(None, username="ab.floor", password=PASSWORD) == floor


@pytest.mark.django_db
@pytest.mark.parametrize("typed", ["AB.FLOOR", "Ab.Floor", " ab.floor "])
def test_sign_10_capitals_never_matter_in_a_username(typed):
    floor = floor_login()

    assert authenticate(None, username=typed, password=PASSWORD) == floor


@pytest.mark.django_db
def test_sign_5_an_owners_username_never_signs_them_in_and_is_not_counted():
    owner = owner_with_a_password()

    assert authenticate(None, username=owner.username, password=PASSWORD) is None
    assert authenticate(None, username=owner.username, password="wrong") is None
    owner.refresh_from_db()
    assert owner.wrong_passwords == 0


@pytest.mark.django_db
def test_sign_11_a_wrong_username_a_turned_off_account_and_a_wrong_password_are_refused():
    floor = floor_login()
    office = MembershipFactory(user__is_active=False).user

    assert authenticate(None, username="ab.nobody", password=PASSWORD) is None
    assert authenticate(None, username=office.username, password=PASSWORD) is None
    assert authenticate(None, username=floor.username, password="wrong") is None


@pytest.mark.django_db
def test_sign_29_a_wrong_password_is_counted():
    floor = floor_login()

    authenticate(None, username="ab.floor", password="wrong")

    floor.refresh_from_db()
    assert floor.wrong_passwords == 1


@pytest.mark.django_db
def test_sign_32_a_locked_account_is_refused_even_with_the_right_password():
    floor = floor_login()
    for _ in range(5):
        count_wrong_password(floor)

    assert authenticate(None, username="ab.floor", password=PASSWORD) is None
    floor.refresh_from_db()
    assert floor.wrong_passwords == 5


@pytest.mark.django_db
def test_sign_34_signing_in_clears_the_count():
    floor = floor_login()
    for _ in range(3):
        count_wrong_password(floor)

    authenticate(None, username="ab.floor", password=PASSWORD)

    floor.refresh_from_db()
    assert floor.wrong_passwords == 0


@pytest.mark.django_db
def test_sign_35_the_django_admins_sign_in_page_meets_the_same_lockout(client):
    staff = UserFactory(username="platform", is_staff=True, is_superuser=True)
    wrong = {"username": "platform", "password": "wrong"}

    for _ in range(5):
        client.post("/admin/login/", wrong)
    client.post("/admin/login/", {"username": "platform", "password": PASSWORD})

    staff.refresh_from_db()
    assert minutes_locked(staff) == 15
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_djangos_async_sign_in_goes_through_the_same_check():
    owner = owner_with_a_password()
    floor = floor_login()

    def signed_in(username):
        return async_to_sync(aauthenticate)(None, username=username, password=PASSWORD)

    assert signed_in(owner.username) is None
    assert signed_in(floor.username) == floor

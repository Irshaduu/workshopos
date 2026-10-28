"""The user (apps/accounts/models.py)."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import User
from apps.accounts.tests.factories import PASSWORD, UserFactory


def test_the_project_uses_our_own_user():
    assert get_user_model() is User


@pytest.mark.django_db
def test_a_user_from_the_factory_can_sign_in(client):
    user = UserFactory()

    assert client.login(username=user.username, password=PASSWORD)


@pytest.mark.django_db
def test_sign_9_a_username_in_other_capitals_is_the_same_username():
    UserFactory(username="ab.floor")
    again = UserFactory.build(username="AB.Floor")

    with pytest.raises(ValidationError, match="already has this username"):
        again.validate_constraints()
    with pytest.raises(IntegrityError), transaction.atomic():
        again.save()


@pytest.mark.django_db
def test_sign_9_an_email_in_other_capitals_belongs_to_one_account_only():
    UserFactory(email="ravi@example.com")
    again = UserFactory.build(email="Ravi@Example.COM")

    with pytest.raises(ValidationError, match="already has this email"):
        again.validate_constraints()
    with pytest.raises(IntegrityError), transaction.atomic():
        again.save()


@pytest.mark.django_db
def test_sign_6_many_accounts_may_have_no_email():
    # Office and Floor sign in with a username and have no email.
    UserFactory(email="")
    UserFactory(email="")

    assert User.objects.filter(email="").count() == 2

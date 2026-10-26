"""The user (apps/accounts/models.py)."""

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import User
from apps.accounts.tests.factories import PASSWORD, UserFactory


def test_the_project_uses_our_own_user():
    assert get_user_model() is User


@pytest.mark.django_db
def test_a_user_from_the_factory_can_sign_in(client):
    user = UserFactory()

    assert client.login(username=user.username, password=PASSWORD)

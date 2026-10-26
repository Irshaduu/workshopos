"""Test data for accounts (factory-boy, ADR-0013)."""

import factory
from factory.django import DjangoModelFactory, Password

from apps.accounts.models import User

#: Every user the factory makes signs in with this password.
PASSWORD = "test-password"


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda user: f"{user.username}@example.com")
    password = Password(PASSWORD)

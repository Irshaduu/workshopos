"""Test data for accounts (factory-boy, ADR-0013)."""

import factory
from factory.django import DjangoModelFactory, Password

from apps.accounts.models import Membership, Role, User
from apps.workshops.tests.factories import WorkshopFactory

#: Every user the factory makes signs in with this password.
PASSWORD = "test-password"


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda user: f"{user.username}@example.com")
    password = Password(PASSWORD)


class MembershipFactory(DjangoModelFactory):
    """A member with the least access, unless a test asks for another role."""

    class Meta:
        model = Membership

    workshop = factory.SubFactory(WorkshopFactory)
    user = factory.SubFactory(UserFactory)
    role = Role.FLOOR

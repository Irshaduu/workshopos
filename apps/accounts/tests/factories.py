"""Test data for accounts (factory-boy, ADR-0013).

Like the real accounts: a member's username starts with the workshop's short
code (SIGN-7); Office and Floor have a password and no email (SIGN-6); an
owner has an email and no password (SIGN-3, SIGN-4).
"""

import factory
from factory.django import DjangoModelFactory, Password

from apps.accounts.models import Membership, Role, User
from apps.workshops.tests.factories import WorkshopFactory

#: Every user the factory makes signs in with this password; an owner has none.
PASSWORD = "test-password"


class UserFactory(DjangoModelFactory):
    """An account with a password and no email, in no workshop."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    password = Password(PASSWORD)


def member_username(user, n):
    """Like ab.member3: the workshop's short code, a dot and a login name."""
    return f"{user.factory_parent.workshop.short_code}.member{n}"


class MembershipFactory(DjangoModelFactory):
    """A member with the least access, unless a test asks for another role.

    MembershipFactory(owner=True) makes an owner, with an email and no password.
    """

    class Meta:
        model = Membership

    class Params:
        owner = factory.Trait(
            role=Role.OWNER,
            user=factory.SubFactory(
                UserFactory,
                username=factory.LazyAttributeSequence(member_username),
                email=factory.LazyAttribute(lambda user: f"{user.username}@example.com"),
                # A plain None: the password becomes unusable, as for a real
                # owner. Password(None) here kept the test password.
                password=None,
            ),
        )

    workshop = factory.SubFactory(WorkshopFactory)
    user = factory.SubFactory(UserFactory, username=factory.LazyAttributeSequence(member_username))
    role = Role.FLOOR

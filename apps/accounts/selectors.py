"""Reads for accounts: rules that read data, never change it (ADR-0005)."""

import math
from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import Membership, Role, User

# The lockout for a password, the same for every workshop, as in v1 (ADR-0025).
LOCK_AFTER = 5
LOCK_TIME = timedelta(minutes=15)


def membership_of(user):
    """The account's membership, with its workshop, in one query; or None.

    Staff and superusers never have one (ADR-0007), whatever the data says.
    """
    if not user.is_authenticated or user.is_platform_staff:
        return None
    return Membership.objects.select_related("workshop").filter(user=user).first()


def is_owner(user):
    """Whether this account is a workshop's owner (ADR-0007)."""
    membership = membership_of(user)
    return membership is not None and membership.role == Role.OWNER


def account_by_username(username):
    """The account with this username, whatever its capitals; or None (SIGN-10)."""
    return User.objects.filter(username__iexact=username.strip()).first()


def minutes_locked(user):
    """How many more minutes this account is locked; 0 when it is not (SIGN-29, SIGN-33).

    Five wrong passwords in a row lock it for 15 minutes from the last one.
    A part of a minute counts as a whole one, so the page never says
    "0 minutes".
    """
    if user.wrong_passwords < LOCK_AFTER or user.last_wrong_password_at is None:
        return 0
    left = user.last_wrong_password_at + LOCK_TIME - timezone.now()
    return max(0, math.ceil(left.total_seconds() / 60))

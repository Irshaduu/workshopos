"""Reads for accounts: rules that read data, never change it (ADR-0005)."""

import math
from datetime import timedelta

from django.db.models import Count, Max
from django.utils import timezone

from apps.accounts.models import Membership, Role, SignInCode, User
from apps.workshops.modules import MODULES

# The lockout for a password, the same for every workshop, as in v1 (ADR-0025).
LOCK_AFTER = 5
LOCK_TIME = timedelta(minutes=15)

# An owner's sign-in code, as in v1 (ADR-0025): it works for 10 minutes and
# for 5 tries (SIGN-16, SIGN-22); an account gets one a minute, 3 an hour
# (SIGN-20).
CODE_TIME = timedelta(minutes=10)
WRONG_CODES = 5
CODE_GAP = timedelta(minutes=1)
CODES_PER_HOUR = 3


def membership_of(user):
    """The account's membership, with its workshop, in one query; or None.

    Staff and superusers never have one (ADR-0007), whatever the data says.
    The answer is kept on the account object, and each request loads its
    account again, so a page asks once however often it checks a permission
    (ROLE-11); a changed role counts from the next request.
    """
    if not user.is_authenticated or user.is_platform_staff:
        return None
    if not hasattr(user, "_membership"):
        user._membership = Membership.objects.select_related("workshop").filter(user=user).first()
    return user._membership


def may_open(user, view):
    """May this account open this page? The one check (ROLE-6), read by every page.

    The page's mark must name a module in the list, and a permission the
    account has. A page with no mark is refused to everyone (ROLE-8). Only a
    public page, or one that works without a workshop (like signing out),
    may name no permission.
    """
    mark = getattr(view, "page_mark", None)
    if mark is None or mark.module not in MODULES:
        return False
    if mark.permission is None:
        public = not getattr(view, "login_required", True)
        return public or not getattr(view, "workshop_required", True)
    return user.has_perm(mark.permission)


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


def owner_by_email(email):
    """The turned-on owner with this email, whatever its capitals; or None (SIGN-10, SIGN-15)."""
    account = User.objects.filter(email__iexact=email.strip(), is_active=True).first()
    return account if account is not None and is_owner(account) else None


def may_ask_for_code(user):
    """Whether this account may get a new code now: one a minute, 3 an hour (SIGN-20).

    Counted from the codes in the database, so clearing a browser's cookies
    never resets it.
    """
    now = timezone.now()
    last_hour = SignInCode.objects.filter(user=user, created_at__gt=now - timedelta(hours=1))
    asked = last_hour.aggregate(count=Count("id"), newest=Max("created_at"))
    if asked["newest"] is not None and now - asked["newest"] < CODE_GAP:
        return False
    return asked["count"] < CODES_PER_HOUR


def tries_left(sign_in_code):
    """How many more tries a code has (SIGN-16, SIGN-22).

    No tries once it is used, ended, or guessed wrong 5 times. A missing code
    (None) has none either.
    """
    if sign_in_code is None or sign_in_code.used_at is not None:
        return 0
    if sign_in_code.ends_at <= timezone.now():
        return 0
    return max(0, WRONG_CODES - sign_in_code.wrong_tries)


def code_tries_left(sign_in_code_id):
    """tries_left() for the code a browser holds, found by its id."""
    return tries_left(SignInCode.objects.filter(pk=sign_in_code_id).first())

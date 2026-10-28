"""Changes in accounts: rules that change data (ADR-0005)."""

import logging
import secrets

from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import RegexValidator
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Membership, Role, SignInCode, User
from apps.accounts.selectors import (
    CODE_TIME,
    LOCK_TIME,
    WRONG_CODES,
    may_ask_for_code,
    membership_of,
    minutes_locked,
    owner_by_email,
    tries_left,
)
from apps.workshops.models import Branch, Workshop

logger = logging.getLogger(__name__)

# The part of a member's username after the short code and the dot.
login_name_form = RegexValidator(
    r"^[a-z0-9]+$", _("A login name is small letters and digits only, like floor or ravi.")
)


def member_username(workshop, login_name):
    """A member's username: the workshop's short code, a dot and a login name,
    like ab.floor (SIGN-7). So it stays unique on a shared server, and when a
    workshop moves to one."""
    login_name_form(login_name)
    return f"{workshop.short_code}.{login_name}"


@transaction.atomic
def create_workshop(*, name, short_code, branch_name, owner_login_name, owner_email):
    """A new workshop with its first branch and its first owner (ADR-0006, ADR-0007, ADR-0025).

    The owner's account is made here too. Its username is the short code, a
    dot and the owner's login name (SIGN-7); it needs an email (SIGN-4), and
    it has no password, because an owner signs in with a code sent to that
    email (SIGN-3). All four records are saved together, or none of them: a
    refused part leaves nothing behind.
    """
    if not owner_email:
        raise ValidationError({"email": _("An owner needs an email: it is how they sign in.")})
    workshop = Workshop(name=name, short_code=short_code)
    branch = Branch(workshop=workshop, name=branch_name)
    owner = User(
        username=member_username(workshop, owner_login_name),
        email=User.objects.normalize_email(owner_email),
    )
    owner.set_unusable_password()
    membership = Membership(workshop=workshop, user=owner, role=Role.OWNER)
    for record in (workshop, branch, owner, membership):
        record.full_clean()
        record.save()
    return workshop


@transaction.atomic
def count_wrong_password(user):
    """Counts one more wrong password for this account (SIGN-29, SIGN-30).

    The account's row is locked first, so two wrong tries at the same moment
    count as two. A wrong password 15 minutes or more after the one before
    starts the count again at one. While the account is locked, nothing is
    counted, so the lock never grows longer (SIGN-32).
    """
    account = User.objects.select_for_update().get(pk=user.pk)
    if minutes_locked(account):
        return
    now = timezone.now()
    last = account.last_wrong_password_at
    in_a_row = last is not None and now - last < LOCK_TIME
    account.wrong_passwords = account.wrong_passwords + 1 if in_a_row else 1
    account.last_wrong_password_at = now
    account.save(update_fields=["wrong_passwords", "last_wrong_password_at"])


def clear_wrong_passwords(user):
    """The right password clears the count (SIGN-34). An account with no count costs no write."""
    if user.wrong_passwords:
        User.objects.filter(pk=user.pk).update(wrong_passwords=0, last_wrong_password_at=None)
        user.wrong_passwords = 0
        user.last_wrong_password_at = None


class CodeNotSent(Exception):
    """The email with a sign-in code did not go out (SIGN-25)."""


def code_hash(code):
    """A sign-in code, kept only as a hash made with the server's secret key (SIGN-24).

    A plain hash of a 6-digit code is undone in seconds by trying every
    code; this one cannot be, without the secret key.
    """
    return salted_hmac("accounts.SignInCode", code, algorithm="sha256").hexdigest()


def send_sign_in_code(email):
    """Emails a new sign-in code to the owner with this email, if there is one (SIGN-15 to SIGN-20).

    Returns the code's record, or None when no code went out: no turned-on
    owner has this email, or the account asked too often. The page gives one
    answer either way, so it never tells who has an account.

    The email goes out during the request, inside the transaction. When it
    cannot be sent, the transaction is undone: the new code is gone, the one
    before still works, and nothing counts towards a limit (SIGN-25). Then it
    raises CodeNotSent.
    """
    owner = owner_by_email(email)
    if owner is None:
        return None
    with transaction.atomic():
        # The account's row is locked, so two asks at the same moment meet
        # the limits one after the other.
        User.objects.select_for_update().get(pk=owner.pk)
        if not may_ask_for_code(owner):
            return None
        code = _new_code()
        now = timezone.now()
        # A new code ends the one before (SIGN-19).
        SignInCode.objects.filter(user=owner, used_at=None, ends_at__gt=now).update(ends_at=now)
        record = SignInCode.objects.create(
            user=owner, code_hash=code_hash(code), created_at=now, ends_at=now + CODE_TIME
        )
        _email_code(owner, code)
    return record


def remake_sign_in_code(email):
    """A new value for the code an owner's browser holds, to give by phone (SIGN-28).

    For a bad day for email: the owner typed their email on the sign-in page,
    but the code never came. Their newest open code gets a new value, fresh
    tries and 10 more minutes. It stays the code that browser holds, so it
    still works only there (SIGN-16), and no limit is spent. Returns the code
    and its record, or None when the owner has no open code.
    """
    owner = owner_by_email(email)
    if owner is None:
        return None
    with transaction.atomic():
        now = timezone.now()
        record = (
            SignInCode.objects.select_for_update()
            .filter(user=owner, used_at=None, ends_at__gt=now, wrong_tries__lt=WRONG_CODES)
            .order_by("-created_at")
            .first()
        )
        if record is None:
            return None
        code = _new_code()
        record.code_hash = code_hash(code)
        record.wrong_tries = 0
        record.ends_at = now + CODE_TIME
        record.save(update_fields=["code_hash", "wrong_tries", "ends_at"])
    return code, record


def _new_code():
    """Six digits from the operating system's secure random source."""
    return f"{secrets.randbelow(1_000_000):06d}"


def _email_code(owner, code):
    """The code in the subject line, so a phone's banner shows it (SIGN-17); the
    owner's own workshop, and a warning never to share it (SIGN-18)."""
    context = {
        "code": code,
        "workshop": membership_of(owner).workshop.name,
        "minutes": int(CODE_TIME.total_seconds() // 60),
    }
    subject = render_to_string("accounts/email/sign_in_code_subject.txt", context).strip()
    body = render_to_string("accounts/email/sign_in_code.txt", context)
    try:
        sent = send_mail(subject, body, None, [owner.email])
    except Exception as error:  # Any failure of any mail service: SMTP, a web API, no mailer.
        # Only the kind of failure: an error's text can hold the owner's email.
        logger.error("A sign-in code email did not go out: %s", type(error).__name__)
        raise CodeNotSent from error
    if not sent:
        raise CodeNotSent


@transaction.atomic
def check_sign_in_code(sign_in_code_id, code):
    """The owner, when the code is right for the code this browser holds; otherwise None.

    A used, ended or unknown code is always wrong (SIGN-16). A wrong code
    counts one wrong try, and the fifth ends the code (SIGN-22). The right
    code is used up, and ends every other code of the account (SIGN-27).
    """
    record = SignInCode.objects.select_for_update().filter(pk=sign_in_code_id).first()
    if not tries_left(record):
        return None
    now = timezone.now()
    if not constant_time_compare(record.code_hash, code_hash(code)):
        record.wrong_tries += 1
        if record.wrong_tries >= WRONG_CODES:
            record.ends_at = now
        record.save(update_fields=["wrong_tries", "ends_at"])
        return None
    record.used_at = now
    record.save(update_fields=["used_at"])
    SignInCode.objects.filter(user_id=record.user_id, used_at=None, ends_at__gt=now).update(
        ends_at=now
    )
    return record.user

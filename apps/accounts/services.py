"""Changes in accounts: rules that change data (ADR-0005)."""

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Membership, Role, User
from apps.accounts.selectors import LOCK_TIME, minutes_locked
from apps.workshops.models import Branch, Workshop

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

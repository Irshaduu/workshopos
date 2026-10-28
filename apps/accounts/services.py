"""Changes in accounts: rules that change data (ADR-0005)."""

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Membership, Role, User
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

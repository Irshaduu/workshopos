"""Changes in accounts: rules that change data (ADR-0005)."""

from django.db import transaction

from apps.accounts.models import Membership, Role
from apps.workshops.models import Branch, Workshop


@transaction.atomic
def create_workshop(*, name, short_code, branch_name, owner):
    """A new workshop with its first branch and its owner (ADR-0006, ADR-0007).

    The owner's account is made first. All three records are saved together,
    or none of them: a refused owner leaves no workshop behind.
    """
    workshop = Workshop(name=name, short_code=short_code)
    branch = Branch(workshop=workshop, name=branch_name)
    membership = Membership(workshop=workshop, user=owner, role=Role.OWNER)
    for record in (workshop, branch, membership):
        record.full_clean()
        record.save()
    return workshop

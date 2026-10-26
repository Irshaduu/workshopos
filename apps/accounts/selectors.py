"""Reads for accounts: rules that read data, never change it (ADR-0005)."""

from apps.accounts.models import Membership


def membership_of(user):
    """The account's membership, with its workshop, in one query; or None.

    Staff and superusers never have one (ADR-0007), whatever the data says.
    """
    if not user.is_authenticated or user.is_platform_staff:
        return None
    return Membership.objects.select_related("workshop").filter(user=user).first()

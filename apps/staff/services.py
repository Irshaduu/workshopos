"""Changes in staff: rules that change data (ADR-0005)."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404

from apps.staff.models import NAME_TAKEN, StaffMember
from apps.workshops.services import save_once


def add_staff_member(workshop, branch, key, *, name, designation):
    """Adds a staff member once, however many times the form is sent (STAFF-8, STAFF-9).

    It answers with the person saved: a repeat gets the one saved first. A taken name
    raises ValidationError (STAFF-7).
    """
    member = StaffMember(
        id=key, workshop=workshop, branch=branch, name=name, designation=designation
    )
    try:
        saved, _saved_now = save_once(member)
    except IntegrityError:
        # The name was free when it was checked, then another person took it.
        raise ValidationError(NAME_TAKEN) from None
    return saved


def change_staff_member(workshop, branch, key, *, name, designation):
    """Changes the name and the designation of the same record, so every job card that
    points to this person stays with them (STAFF-10).

    A repeat saves the same values again. A taken name raises ValidationError (STAFF-7).
    """
    with transaction.atomic():
        member = _locked(workshop, branch, key)
        member.name = name
        member.designation = designation
        member.full_clean()
        try:
            # Its own savepoint, so a refused save leaves this transaction working.
            with transaction.atomic():
                member.save(update_fields=["name", "designation"])
        except IntegrityError:
            # The name was free when it was checked, then another person took it.
            raise ValidationError(NAME_TAKEN) from None
    return member


def turn_off(workshop, branch, key):
    """Someone who leaves is turned off, never deleted (STAFF-11)."""
    return _set_turned_on(workshop, branch, key, False)


def turn_on(workshop, branch, key):
    """Someone who comes back is turned on, not added again (STAFF-7)."""
    return _set_turned_on(workshop, branch, key, True)


def _set_turned_on(workshop, branch, key, is_active):
    """Sets the state it is asked for, never a flip, so a repeat changes nothing and a
    double tap ends the way it was tapped (STAFF-13)."""
    with transaction.atomic():
        member = _locked(workshop, branch, key)
        if member.is_active != is_active:
            member.is_active = is_active
            member.save(update_fields=["is_active"])
    return member


def _locked(workshop, branch, key):
    """The staff member with this key, locked until the transaction ends."""
    return get_object_or_404(
        StaffMember.objects.for_workshop(workshop).for_branch(branch).select_for_update(), pk=key
    )

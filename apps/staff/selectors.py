"""Reads for staff: rules that read data, never change it (ADR-0005)."""

from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404

from apps.staff.models import Designation, StaffMember


def staff_by_designation(workshop, branch):
    """Each designation, in order, with its staff members: those turned on first, then
    by name, whatever the capitals (STAFF-20)."""
    members = (
        StaffMember.objects.for_workshop(workshop)
        .for_branch(branch)
        .order_by("-is_active", Lower("name"))
    )
    groups = {designation: [] for designation in Designation.values}
    for member in members:
        groups[member.designation].append(member)
    return [(Designation(value), group) for value, group in groups.items()]


def staff_member(workshop, branch, key):
    """The staff member with this key. Any other record answers "not found" (STAFF-4)."""
    return get_object_or_404(StaffMember.objects.for_workshop(workshop).for_branch(branch), pk=key)


def saved_staff_member(workshop, branch, key):
    """The staff member saved under this key; None when none is. A form that makes a
    new record asks this first (STAFF-9)."""
    return StaffMember.objects.for_workshop(workshop).for_branch(branch).filter(pk=key).first()

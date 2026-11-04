"""The people who work at the workshop (docs/rules/staff-list.md)."""

from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from apps.workshops.models import BranchModel

NAME_TAKEN = _("This name is already on the staff list.")


def tidy_name(typed):
    """The name as it is saved (STAFF-6).

    Spaces at the ends and double spaces go, so a second copy cannot hide behind them.
    A name typed with no capitals gets one at the start of each word. A name typed with
    its own capitals keeps them, and only its first letter is raised, so "anil KP" is
    "Anil KP" and "Mohammed bin Salim" stays. No capital is ever made small, so whatever
    is typed can be kept.
    """
    name = " ".join(typed.split())
    return name.title() if name.islower() else name[:1].upper() + name[1:]


class Designation(models.TextChoices):
    """A staff member's job, in the order the list shows them (STAFF-2, STAFF-3).

    It says nothing about what a person may open: that is a login's role.
    """

    MECHANIC = "mechanic", _("Mechanic")
    ASSISTANT_MECHANIC = "assistant_mechanic", _("Assistant Mechanic")
    OFFICE_STAFF = "office_staff", _("Office Staff")
    GENERAL_HELPER = "general_helper", _("General Helper")


class StaffMember(BranchModel):
    """A real person who works at the workshop, not a login (STAFF-1).

    Nothing links the two: every mechanic can share one Floor login, and a person
    with no login is still on the list.
    """

    name = models.CharField(_("name"), max_length=100)
    designation = models.CharField(_("designation"), max_length=20, choices=Designation)
    # False means turned off. Someone who leaves is never deleted (STAFF-11).
    is_active = models.BooleanField(_("turned on"), default=True, db_default=True)

    class Meta(BranchModel.Meta):
        verbose_name = _("staff member")
        verbose_name_plural = _("staff members")
        constraints = [
            *BranchModel.Meta.constraints,
            # A job card's picker shows only the name (STAFF-7). A turned-off
            # person's name counts too: someone who comes back is turned on.
            models.UniqueConstraint(
                Lower("name"),
                "branch",
                name="staff_staffmember_name_once",
                violation_error_message=NAME_TAKEN,
            ),
            models.CheckConstraint(
                condition=models.Q(name__regex=r"\S"),
                name="staff_staffmember_name_given",
                violation_error_message=_("Type a name."),
            ),
            models.CheckConstraint(
                condition=models.Q(designation__in=Designation.values),
                name="staff_staffmember_designation_known",
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        # Here, so every service that checks a record before saving tidies it, whoever
        # calls it, and before the check that the name is free.
        self.name = tidy_name(self.name)

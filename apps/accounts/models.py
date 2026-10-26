"""Who signs in, and their place in a workshop (ADR-0007)."""

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel
from apps.workshops.models import WorkshopModel


class User(BaseModel, AbstractUser):
    """A person who signs in.

    Made before any other app's first migration, so it can grow later without
    rebuilding the database. What a person may do in a workshop comes from
    their membership (ADR-0007).
    """

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    @property
    def is_platform_staff(self):
        """Runs the system: staff and superusers. Never a workshop member (ADR-0007)."""
        return self.is_staff or self.is_superuser


class Role(models.TextChoices):
    OWNER = "owner", _("Owner")
    OFFICE = "office", _("Office")
    FLOOR = "floor", _("Floor")


class Membership(WorkshopModel):
    """An account's place in a workshop, with its role (ADR-0007).

    One per account for now: an account belongs to one workshop. A shared
    login, like one Floor login on the workshop tablet, is still one account.
    Several workshops per account come with a workshop picker (SaaS).
    """

    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="+", verbose_name=_("user")
    )
    role = models.CharField(_("role"), max_length=20, choices=Role)

    class Meta(WorkshopModel.Meta):
        verbose_name = _("membership")
        verbose_name_plural = _("memberships")
        constraints = [
            *WorkshopModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["user"],
                name="accounts_membership_one_per_account",
                violation_error_message=_("This account already belongs to a workshop."),
            ),
            models.CheckConstraint(
                condition=models.Q(role__in=Role.values),
                name="accounts_membership_role_known",
            ),
        ]

    def __str__(self):
        return f"{self.user} ({self.get_role_display()})"

    def clean(self):
        super().clean()
        if self.user_id and self.user.is_platform_staff:
            raise ValidationError(
                {"user": _("Staff and superusers run the system; they are never members.")}
            )

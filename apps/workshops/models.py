"""The workshop, its branches, and the base of every business model (ADR-0023)."""

from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class WorkshopStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    SUSPENDED = "suspended", _("Suspended")


class Workshop(BaseModel):
    """The business that uses the system: the tenant (ADR-0003, ADR-0006).

    Its records live in the models that build on WorkshopModel.
    """

    name = models.CharField(_("name"), max_length=100)
    # Every username of the workshop starts with it, like ab.floor, so a
    # username stays unique on a shared server (SIGN-7, SIGN-8). Given when
    # the workshop is made; nothing changes it after.
    short_code = models.CharField(
        _("short code"),
        max_length=8,
        unique=True,
        error_messages={"unique": _("Another workshop already has this short code.")},
        help_text=_("2 to 8 small letters or digits. It never changes."),
    )
    status = models.CharField(
        _("status"), max_length=20, choices=WorkshopStatus, default=WorkshopStatus.ACTIVE
    )

    class Meta:
        verbose_name = _("workshop")
        verbose_name_plural = _("workshops")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=WorkshopStatus.values),
                name="workshops_workshop_status_known",
            ),
            models.CheckConstraint(
                condition=models.Q(short_code__regex=r"^[a-z0-9]{2,8}$"),
                name="workshops_workshop_short_code_form",
                violation_error_message=_("A short code is 2 to 8 small letters or digits."),
            ),
        ]

    def __str__(self):
        return self.name


class WorkshopQuerySet(models.QuerySet):
    def for_workshop(self, workshop):
        """Only this workshop's records. Every query of a workshop model starts here."""
        if not isinstance(workshop, Workshop):
            raise TypeError(f"for_workshop() needs a Workshop, not {workshop!r}.")
        return self.filter(workshop=workshop)


class WorkshopModel(BaseModel):
    """A record that belongs to one workshop. Every business model builds on it.

    The (workshop, id) pair is unique, so a link from another record can be
    checked to stay in the same workshop. Its index also serves every "this
    workshop's records" query, so the link needs no index of its own.

    A model with its own constraints keeps these: its Meta builds on
    WorkshopModel.Meta and starts its list with *WorkshopModel.Meta.constraints.
    """

    workshop = models.ForeignKey(
        Workshop,
        on_delete=models.PROTECT,
        related_name="+",
        db_index=False,
        verbose_name=_("workshop"),
    )

    objects = WorkshopQuerySet.as_manager()

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["workshop", "id"], name="%(app_label)s_%(class)s_workshop_id"
            ),
        ]


class Branch(WorkshopModel):
    """One of a workshop's places (ADR-0006)."""

    name = models.CharField(_("name"), max_length=100)

    class Meta(WorkshopModel.Meta):
        verbose_name = _("branch")
        verbose_name_plural = _("branches")
        constraints = [
            *WorkshopModel.Meta.constraints,
            models.UniqueConstraint(
                Lower("name"),
                "workshop",
                name="workshops_branch_name_once",
                violation_error_message=_("This workshop already has a branch with this name."),
            ),
        ]

    def __str__(self):
        return self.name

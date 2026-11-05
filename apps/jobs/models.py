"""One visit of one car: the job card and its rows (docs/rules/job-card.md, ADR-0030).

A job card builds on BranchModel. A row of a job card builds on WorkshopModel, with no
branch link of its own: it reaches its branch through its card, so that fact has one home.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.money import MoneyField
from apps.core.text import tidy_spaces
from apps.staff.models import StaffMember
from apps.vehicles.models import PLATE_MAX_LENGTH, Car, Customer
from apps.workshops.constraints import SameWorkshop
from apps.workshops.models import BranchModel, WorkshopModel

NUMBER_LETTERS = "JC"
MILEAGE_MAX = 2_000_000


def number_from(count):
    """A job card's number, like JC-0027: at least four digits, then it grows (JOB-5)."""
    return f"{NUMBER_LETTERS}-{count:04d}"


class NumberCounter(BranchModel):
    """The last job card number given in a branch (JOB-6).

    A row locked in the same transaction as the job card, so two cards never take one
    number and a save that fails uses none. A PostgreSQL sequence would skip a number when
    a save fails.
    """

    last_number = models.PositiveIntegerField(_("last number"), default=0, db_default=0)

    class Meta(BranchModel.Meta):
        verbose_name = _("number counter")
        verbose_name_plural = _("number counters")
        constraints = [
            *BranchModel.Meta.constraints,
            models.UniqueConstraint(fields=["branch"], name="jobs_numbercounter_one_per_branch"),
        ]

    def __str__(self):
        return number_from(self.last_number)


class JobCardStatus(models.TextChoices):
    """A job card's state (JOB-3). Later steps add Ready and Settled."""

    OPEN = "open", _("Open")
    CANCELLED = "cancelled", _("Cancelled")


class JobCard(BranchModel):
    """One visit of one car to one branch (JOB-1). It is never deleted (JOB-49).

    It keeps what is true of the visit, like the plate it came with. What is true of the
    car lives on the car (JOB-12, JOB-13).
    """

    number = models.CharField(_("job card number"), max_length=20, editable=False)
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=JobCardStatus,
        default=JobCardStatus.OPEN,
        db_default=JobCardStatus.OPEN,
        editable=False,
    )
    car = models.ForeignKey(
        Car, on_delete=models.PROTECT, related_name="job_cards", verbose_name=_("car")
    )
    plate = models.CharField(_("plate number"), max_length=PLATE_MAX_LENGTH)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="job_cards",
        null=True,
        blank=True,
        verbose_name=_("customer"),
    )
    lead_mechanic = models.ForeignKey(
        StaffMember,
        on_delete=models.PROTECT,
        related_name="job_cards",
        null=True,
        blank=True,
        verbose_name=_("lead mechanic"),
    )
    admitted_date = models.DateField(_("admitted date"))
    # A whole number of kilometres at this visit. Empty when the odometer does not work
    # or was not read, and settling warns about that (JOB-22).
    mileage = models.PositiveIntegerField(
        _("mileage"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(MILEAGE_MAX)],
    )
    note = models.CharField(_("internal note"), max_length=255, blank=True)
    labour = MoneyField(_("labour charge"), allow_zero=True, blank=True, default=Decimal("0"))
    cancel_reason = models.CharField(_("reason"), max_length=255, blank=True, editable=False)

    class Meta(BranchModel.Meta):
        verbose_name = _("job card")
        verbose_name_plural = _("job cards")
        constraints = [
            *BranchModel.Meta.constraints,
            SameWorkshop("car", name="jobs_jobcard_car_same_workshop"),
            SameWorkshop("customer", name="jobs_jobcard_customer_same_workshop"),
            SameWorkshop("lead_mechanic", name="jobs_jobcard_lead_mechanic_same_workshop"),
            models.UniqueConstraint(
                fields=["car"],
                condition=Q(status="open"),
                name="jobs_jobcard_one_open_per_car",
                violation_error_message=_("This car already has an open job card."),
            ),
            models.UniqueConstraint(fields=["branch", "number"], name="jobs_jobcard_number_once"),
            models.CheckConstraint(
                condition=Q(status__in=JobCardStatus.values),
                name="jobs_jobcard_status_known",
            ),
            models.CheckConstraint(
                condition=Q(plate__regex=r"^[A-Z0-9]+$"),
                name="jobs_jobcard_plate_form",
            ),
            models.CheckConstraint(
                condition=Q(labour__gte=0),
                name="jobs_jobcard_labour_not_negative",
                violation_error_message=_("An amount cannot be negative."),
            ),
            models.CheckConstraint(
                condition=Q(mileage__isnull=True) | Q(mileage__gte=1, mileage__lte=MILEAGE_MAX),
                name="jobs_jobcard_mileage_in_range",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status="open", cancel_reason="")
                    | Q(status="cancelled", cancel_reason__regex=r"\S")
                ),
                name="jobs_jobcard_cancelled_has_a_reason",
            ),
        ]

    def __str__(self):
        return self.number

    @property
    def is_open(self):
        return self.status == JobCardStatus.OPEN


class ConcernStatus(models.TextChoices):
    """Each with its word and its colour (JOB-33)."""

    PENDING = "pending", _("Pending")
    WORKING = "working", _("Working")
    FIXED = "fixed", _("Fixed")


class Concern(WorkshopModel):
    """One thing the customer reported (JOB-33). Rows sort by their key, which keeps the
    order they were added in (JOB-38)."""

    job_card = models.ForeignKey(
        JobCard, on_delete=models.PROTECT, related_name="concerns", verbose_name=_("job card")
    )
    text = models.CharField(_("concern"), max_length=255)
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=ConcernStatus,
        default=ConcernStatus.PENDING,
        db_default=ConcernStatus.PENDING,
    )

    class Meta(WorkshopModel.Meta):
        ordering = ["id"]
        verbose_name = _("concern")
        verbose_name_plural = _("concerns")
        constraints = [
            *WorkshopModel.Meta.constraints,
            SameWorkshop("job_card", name="jobs_concern_job_card_same_workshop"),
            models.UniqueConstraint(Lower("text"), "job_card", name="jobs_concern_text_once"),
            models.CheckConstraint(condition=Q(text__regex=r"\S"), name="jobs_concern_text_given"),
            models.CheckConstraint(
                condition=Q(status__in=ConcernStatus.values), name="jobs_concern_status_known"
            ),
        ]

    def __str__(self):
        return self.text

    def clean(self):
        self.text = tidy_spaces(self.text)


class JobLine(WorkshopModel):
    """One job that was done, in words, with no price (JOB-31, JOB-34)."""

    job_card = models.ForeignKey(
        JobCard, on_delete=models.PROTECT, related_name="job_lines", verbose_name=_("job card")
    )
    text = models.CharField(_("job"), max_length=150)

    class Meta(WorkshopModel.Meta):
        ordering = ["id"]
        verbose_name = _("job line")
        verbose_name_plural = _("job lines")
        constraints = [
            *WorkshopModel.Meta.constraints,
            SameWorkshop("job_card", name="jobs_jobline_job_card_same_workshop"),
            models.UniqueConstraint(Lower("text"), "job_card", name="jobs_jobline_text_once"),
            models.CheckConstraint(condition=Q(text__regex=r"\S"), name="jobs_jobline_text_given"),
        ]

    def __str__(self):
        return self.text

    def clean(self):
        self.text = tidy_spaces(self.text)


class StepKind(models.TextChoices):
    """The steps a job card has today (JOB-39). On hold, back, Ready and its undo come with
    their buttons, and part ordered and received with parts (Phase 6)."""

    CAR_IN = "car_in", _("Car in")
    CONCERN_PENDING = "concern_pending", _("Concern pending")
    CONCERN_WORKING = "concern_working", _("Concern working")
    CONCERN_FIXED = "concern_fixed", _("Concern fixed")
    CANCELLED = "cancelled", _("Cancelled")


#: The step that says a concern reached this status.
CONCERN_STEPS = {
    ConcernStatus.PENDING: StepKind.CONCERN_PENDING,
    ConcernStatus.WORKING: StepKind.CONCERN_WORKING,
    ConcernStatus.FIXED: StepKind.CONCERN_FIXED,
}


class JobCardStep(WorkshopModel):
    """One change in a job card's life, with its time (JOB-39).

    It keeps who acted, by login, and the lead mechanic at that moment, because a shared
    Floor login says only Floor (JOB-40). It cannot be filled in later.
    """

    job_card = models.ForeignKey(
        JobCard, on_delete=models.PROTECT, related_name="steps", verbose_name=_("job card")
    )
    kind = models.CharField(_("kind"), max_length=30, choices=StepKind)
    concern = models.ForeignKey(
        Concern,
        on_delete=models.CASCADE,
        related_name="steps",
        null=True,
        blank=True,
        verbose_name=_("concern"),
    )
    at = models.DateTimeField(_("at"), default=timezone.now)
    by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+", verbose_name=_("by")
    )
    mechanic = models.ForeignKey(
        StaffMember,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        verbose_name=_("lead mechanic"),
    )

    class Meta(WorkshopModel.Meta):
        ordering = ["id"]
        verbose_name = _("step")
        verbose_name_plural = _("steps")
        constraints = [
            *WorkshopModel.Meta.constraints,
            SameWorkshop("job_card", name="jobs_jobcardstep_job_card_same_workshop"),
            SameWorkshop("concern", name="jobs_jobcardstep_concern_same_workshop"),
            SameWorkshop("mechanic", name="jobs_jobcardstep_mechanic_same_workshop"),
            models.CheckConstraint(
                condition=Q(kind__in=StepKind.values), name="jobs_jobcardstep_kind_known"
            ),
            models.CheckConstraint(
                condition=(
                    Q(kind__in=list(CONCERN_STEPS.values()), concern__isnull=False)
                    | (~Q(kind__in=list(CONCERN_STEPS.values())) & Q(concern__isnull=True))
                ),
                name="jobs_jobcardstep_concern_when_about_one",
            ),
        ]

    def __str__(self):
        return self.get_kind_display()

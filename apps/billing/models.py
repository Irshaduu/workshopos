"""A job card's bill, and the money paid for it (docs/rules/settle-bill.md, ADR-0032).

A bill's total is never stored: it is worked out from its job card's rows when it is read
(SETTLE-3). What is stored is what settling decided and must never change by itself: the
number, the date, the discount, who settled it and when, and the copy of what the bill
prints about the customer and the car (SETTLE-34).
"""

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.money import MoneyField
from apps.jobs.models import JobCard
from apps.workshops.constraints import SameBranch, SameWorkshop
from apps.workshops.models import BranchModel, WorkshopModel

#: A bill's number, like INV-26-27-0045: at most 16 characters, as GST allows (SETTLE-31).
NUMBER_LETTERS = "INV"
NUMBER_MAX_LENGTH = 16
#: The shape of every number, which PostgreSQL checks: the letters, the year, a count.
NUMBER_SHAPE = rf"^{NUMBER_LETTERS}-[0-9]{{2}}-[0-9]{{2}}-[0-9]{{4,6}}$"


def number_from(year, count):
    """A bill's number: INV, the financial year that starts in `year`, and a count of at
    least four digits (SETTLE-28). 2026 and 45 give INV-26-27-0045."""
    return f"{NUMBER_LETTERS}-{year % 100:02d}-{(year + 1) % 100:02d}-{count:04d}"


class PaymentMethod(models.TextChoices):
    """How a payment was made, always in words (SETTLE-15). The settle box shows one money box
    for each, in this order."""

    CASH = "cash", _("Cash")
    UPI = "upi", _("UPI")
    CARD = "card", _("Card")
    BANK_TRANSFER = "bank_transfer", _("Bank transfer")


class BillCounter(BranchModel):
    """The last bill number given in a branch in one financial year (SETTLE-29).

    A row locked in the same transaction as the settle, so two bills never take one number
    and a settle that fails uses none. A PostgreSQL sequence would skip a number when a save
    fails. The year's first bill makes its row.
    """

    #: The year the financial year starts in: 2026 for 1 April 2026 to 31 March 2027.
    financial_year = models.PositiveSmallIntegerField(_("financial year"))
    last_number = models.PositiveIntegerField(_("last number"), default=0, db_default=0)

    class Meta(BranchModel.Meta):
        verbose_name = _("bill counter")
        verbose_name_plural = _("bill counters")
        constraints = [
            *BranchModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["branch", "financial_year"], name="billing_billcounter_one_a_year"
            ),
        ]

    def __str__(self):
        return number_from(self.financial_year, self.last_number)


class Bill(BranchModel):
    """What a customer paid for one job card, once it is settled (SETTLE-1). A job card that
    is still open has a preview, which is no record at all (SETTLE-2).

    Its branch is its job card's, by PostgreSQL (SameBranch). Its job card never reads it:
    jobs sits below billing (docs/ARCHITECTURE.md).
    """

    # Its one-bill rule below is its index, so it needs no second one.
    job_card = models.ForeignKey(
        JobCard,
        on_delete=models.PROTECT,
        related_name="+",
        db_index=False,
        verbose_name=_("job card"),
    )
    number = models.CharField(_("bill number"), max_length=NUMBER_MAX_LENGTH, editable=False)
    #: The date paid: a walk-in's bill is dated the day the customer paid (SETTLE-22).
    date = models.DateField(_("date"))
    #: When it was settled and by whom: the moment the money was typed in, which the edit
    #: window counts from and a back-dated bill is judged by (SETTLE-22, CHANGE-10, CHANGE-17).
    settled_at = models.DateTimeField(_("settled at"), default=timezone.now, editable=False)
    settled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        editable=False,
        verbose_name=_("settled by"),
    )
    discount = MoneyField(_("discount"), allow_zero=True)
    # The frozen copy: what the bill prints about the customer and the car, as it was when
    # the bill was settled (SETTLE-34).
    customer_name = models.CharField(_("customer name"), max_length=150, blank=True)
    brand = models.CharField(_("car brand"), max_length=100)
    car_model = models.CharField(_("car model"), max_length=100)

    class Meta(BranchModel.Meta):
        verbose_name = _("bill")
        verbose_name_plural = _("bills")
        constraints = [
            *BranchModel.Meta.constraints,
            SameWorkshop("job_card", name="billing_bill_job_card_same_workshop"),
            SameBranch("job_card", name="billing_bill_job_card_same_branch"),
            # One bill for each job card for now. Cancelling a bill, with Pending and paid
            # bills (Phase 6), lets a card be billed again under a new number.
            models.UniqueConstraint(
                fields=["job_card"],
                name="billing_bill_one_per_job_card",
                violation_error_message=_("This job card already has its bill."),
            ),
            # Unique in the workshop, not only the branch, so a second place cannot settle
            # until it has letters of its own (SETTLE-31, SETTLE-32).
            models.UniqueConstraint(
                fields=["workshop", "number"],
                name="billing_bill_number_once",
                violation_error_message=_("Another bill of this workshop has this number."),
            ),
            models.CheckConstraint(
                condition=Q(number__regex=NUMBER_SHAPE),
                name="billing_bill_number_form",
            ),
            models.CheckConstraint(
                condition=Q(discount__gte=0),
                name="billing_bill_discount_not_negative",
                violation_error_message=_("An amount cannot be negative."),
            ),
        ]

    def __str__(self):
        return self.number


class Payment(WorkshopModel):
    """Money a customer paid toward a bill, by one method (SETTLE-15, SETTLE-16). A row of its
    bill, so it reaches its branch through the bill, and its date is the bill's: a walk-in
    pays all at once (ADR-0032)."""

    # Its one-payment-per-method rule below starts with the bill, so that is its index.
    bill = models.ForeignKey(
        Bill,
        on_delete=models.PROTECT,
        related_name="payments",
        db_index=False,
        verbose_name=_("bill"),
    )
    method = models.CharField(_("payment method"), max_length=20, choices=PaymentMethod)
    amount = MoneyField(_("amount"))

    class Meta(WorkshopModel.Meta):
        ordering = ["id"]
        verbose_name = _("payment")
        verbose_name_plural = _("payments")
        constraints = [
            *WorkshopModel.Meta.constraints,
            SameWorkshop("bill", name="billing_payment_bill_same_workshop"),
            models.UniqueConstraint(
                fields=["bill", "method"],
                name="billing_payment_one_per_method",
                violation_error_message=_("This bill already has a payment by this method."),
            ),
            models.CheckConstraint(
                condition=Q(method__in=PaymentMethod.values), name="billing_payment_method_known"
            ),
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="billing_payment_amount_above_zero",
                violation_error_message=_("Type an amount above zero."),
            ),
        ]

    def __str__(self):
        return f"{self.get_method_display()} {self.amount}"

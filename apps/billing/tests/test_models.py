"""What PostgreSQL holds for a bill and its payments (docs/rules/settle-bill.md)."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import DataError, transaction
from django.db.models import F

from apps.billing.models import Bill, Payment, number_from
from apps.billing.tests.factories import BillFactory, PaymentFactory
from apps.core.tests.postgresql import refused_by_postgresql
from apps.jobs.models import JobCardStatus
from apps.jobs.tests.factories import JobCardFactory
from apps.workshops.tests.factories import BranchFactory

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("year", "count", "number"),
    [
        (2026, 45, "INV-26-27-0045"),
        (2026, 1, "INV-26-27-0001"),
        (2026, 12345, "INV-26-27-12345"),
        (2099, 7, "INV-99-00-0007"),
    ],
)
def test_settle_28_a_number_is_inv_its_financial_year_and_a_count(year, count, number):
    assert number_from(year, count) == number


def test_settle_31_a_number_is_at_most_16_characters_in_its_one_shape():
    assert len(number_from(2026, 999_999)) == 16

    bill = BillFactory()
    with pytest.raises(DataError), transaction.atomic():
        Bill.objects.filter(pk=bill.pk).update(number="INV-26-27-1000000")
    refused_by_postgresql(
        lambda: Bill.objects.filter(pk=bill.pk).update(number="JB-26-027"),
        "billing_bill_number_form",
    )


def test_settle_31_a_number_is_once_in_its_workshop_even_across_branches():
    first = BillFactory()
    there = BranchFactory(workshop=first.workshop)

    refused_by_postgresql(
        lambda: BillFactory(workshop=first.workshop, branch=there, number=first.number),
        "billing_bill_number_once",
    )


def test_settle_31_another_workshop_may_have_the_same_number():
    first = BillFactory()

    BillFactory(number=first.number)


def test_settle_19_a_discount_is_never_below_zero():
    bill = BillFactory()

    # An expression goes straight to PostgreSQL, past the column's own rules (ADR-0029).
    refused_by_postgresql(
        lambda: Bill.objects.filter(pk=bill.pk).update(discount=F("discount") - Decimal("1")),
        "billing_bill_discount_not_negative",
    )


def test_settle_16_a_payment_is_above_zero():
    payment = PaymentFactory()

    refused_by_postgresql(
        lambda: Payment.objects.filter(pk=payment.pk).update(amount=F("amount") * 0),
        "billing_payment_amount_above_zero",
    )
    with pytest.raises(ValidationError):
        PaymentFactory.build(bill=payment.bill, workshop=payment.workshop, amount=0).full_clean()


def test_settle_15_a_bill_has_one_payment_for_each_method():
    payment = PaymentFactory()

    refused_by_postgresql(
        lambda: PaymentFactory(workshop=payment.workshop, bill=payment.bill, method=payment.method),
        "billing_payment_one_per_method",
    )


def test_settle_1_a_job_card_has_one_bill():
    bill = BillFactory()

    refused_by_postgresql(
        lambda: BillFactory(workshop=bill.workshop, branch=bill.branch, job_card=bill.job_card),
        "billing_bill_one_per_job_card",
    )


def test_a_bills_branch_is_its_job_cards_by_postgresql():
    bill = BillFactory()
    there = BranchFactory(workshop=bill.workshop)
    card_there = JobCardFactory(workshop=bill.workshop, branch=there, status=JobCardStatus.SETTLED)

    refused_by_postgresql(
        lambda: Bill.objects.filter(pk=bill.pk).update(job_card=card_there),
        "billing_bill_job_card_same_branch",
    )
    with pytest.raises(ValidationError) as refused:
        BillFactory.build(
            workshop=bill.workshop, branch=bill.branch, job_card=card_there
        ).full_clean()
    assert "This belongs to another branch." in refused.value.messages

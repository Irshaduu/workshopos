"""Reads for billing: rules that read data, never change it (ADR-0005).

One function builds everything a bill shows, bill_sheet(), so a second bill design later
only shows the same figures (ADR-0032, decision 10 of the build plan).
"""

import datetime
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Prefetch
from django.utils import timezone
from django.utils.translation import gettext_lazy

from apps.audit.selectors import money_change_refusal
from apps.billing.models import Bill, Payment, PaymentMethod
from apps.jobs.models import JobLine

#: How many rows each table of the bill is padded to, so its foot sits at the same height
#: on every bill (v1's MIN_JOB_ROWS and MIN_PART_ROWS). A longer list is never cut.
JOB_ROWS = 9
PART_ROWS = 11
#: How many days back Office sees its paid bills, before today (ROLE-20, v1's
#: paid_bills_list). It is never shorter than the longest edit window, so Office always
#: finds a bill it may still change (SETTLE-53); a test holds the two together.
OFFICE_PAID_BILLS_DAYS = 7
#: A settled bill's own first words when Office is past the edit window (CHANGE-12).
SETTLED_AGO = gettext_lazy("Settled %(ago)s.")
#: The boxes of a settled bill a person may change: the date paid and one for each method
#: (SETTLE-39).
BOXES = ("paid_on", *PaymentMethod.values)


def financial_year_of(day):
    """The year a financial year starts in, for a day in it: 1 April to 31 March, as Indian
    tax counts a year (SETTLE-28, SETTLE-30). 31 March 2027 is in 2026's year."""
    return day.year if day.month >= 4 else day.year - 1


def financial_year_days(year):
    """The first and the last day of the financial year that starts in `year`, so the date
    box and the server keep one rule (SETTLE-44)."""
    return datetime.date(year, 4, 1), datetime.date(year + 1, 3, 31)


def change_refusal(workshop, user, bill):
    """Why this person may no longer change this settled bill, in plain words; None when
    they may. Its edit window counts from the moment it was settled, never its date paid,
    and a change never starts it again (CHANGE-9, CHANGE-10, SETTLE-42)."""
    return money_change_refusal(workshop, user, bill.settled_at, happened=SETTLED_AGO)


def bill_total(workshop, card):
    """What the bill adds up to, worked out from its rows each time it is read: the labour
    charge today, and the parts with Phase 6 (SETTLE-3). Never typed, never stored."""
    return card.labour


def nothing_to_settle(total):
    """A bill of 0.00 is never settled (SETTLE-18). The bill page asks this before it offers
    the settle box, and the service asks it again, so the two never disagree."""
    return total <= 0


def printed_names(card):
    """What a bill prints about the customer and the car: the customer's name, the brand and
    the model (SETTLE-34). A preview reads them from the records each time, and settling
    freezes them on the bill, so both come from here."""
    model = card.car.car_model
    return (card.customer.name if card.customer_id else "", model.brand.name, model.name)


def saved_bill(workshop, branch, key):
    """The bill saved under this key; None when none is. The settle box asks this first, so a
    double tap shows the bill settled the first time (SETTLE-25)."""
    return Bill.objects.for_workshop(workshop).for_branch(branch).filter(pk=key).first()


def bill_of(workshop, branch, card):
    """The job card's bill; None while the card is open (SETTLE-2). Only settling makes a
    bill, so a card that is not settled asks nothing."""
    if not card.is_settled:
        return None
    return (
        Bill.objects.for_workshop(workshop)
        .for_branch(branch)
        .filter(job_card=card)
        .select_related("settled_by")
        .first()
    )


def payments_of(workshop, bill):
    """A bill's payments, in the settle box's order of methods."""
    return _in_method_order(Payment.objects.for_workshop(workshop).filter(bill=bill))


def _in_method_order(payments):
    return sorted(payments, key=lambda payment: PaymentMethod.values.index(payment.method))


def bill_figures(workshop, bill):
    """A settled bill's figures that Change payments may move, by name: the date paid, what
    was paid by each method (None for a method not used), and the discount (SETTLE-39,
    SETTLE-41). The change box opens with them, and a kept Change compares them."""
    paid = {payment.method: payment.amount for payment in payments_of(workshop, bill)}
    return {
        "paid_on": bill.date,
        **{method: paid.get(method) for method in PaymentMethod.values},
        "discount": bill.discount,
    }


@dataclass(frozen=True)
class PaidBill:
    """One row of Paid bills (SETTLE-53): the bill, its total and net, and its payments."""

    bill: Bill
    total: Decimal
    net: Decimal
    payments: list


def paid_bills_for(workshop, branch, user, today=None):
    """The settled bills of this branch this person may see, newest first by the date paid
    (SETTLE-53). Office sees those settled in the last 7 days, counted from the moment each
    was settled, as v1 counted, so a bill an owner dated far back today is still there while
    Office may change it (ROLE-20, CHANGE-10). Owners see every bill."""
    bills = Bill.objects.for_workshop(workshop).for_branch(branch)
    if not user.has_perm("billing.see_every_paid_bill"):
        since = (today or timezone.localdate()) - datetime.timedelta(days=OFFICE_PAID_BILLS_DAYS)
        # The moment that day starts in India, so the filter reads settled_at as it is kept.
        start = datetime.datetime.combine(since, datetime.time.min, timezone.get_current_timezone())
        bills = bills.filter(settled_at__gte=start)
    bills = (
        bills.select_related("job_card")
        .prefetch_related(
            Prefetch("payments", queryset=Payment.objects.for_workshop(workshop), to_attr="paid")
        )
        .order_by("-date", "-settled_at")
    )
    rows = []
    for bill in bills:
        # The labour charge, read with the bill. When parts join the total (Phase 6), they
        # come in one query for every row, or tests/test_query_counts.py fails.
        total = bill_total(workshop, bill.job_card)
        rows.append(PaidBill(bill, total, total - bill.discount, _in_method_order(bill.paid)))
    return rows


@dataclass(frozen=True)
class Sheet:
    """Everything a bill shows, worked out once (SETTLE-6 to SETTLE-9, SETTLE-34, SETTLE-35).

    A preview reads the records as they are now; a settled bill reads its own frozen copy.
    """

    bill: object
    customer_name: str
    brand: str
    car_model: str
    plate: str
    mileage: object
    job_lines: list
    job_pad: range
    part_pad: range
    labour: Decimal
    parts: Decimal
    total: Decimal
    discount: Decimal
    net: Decimal
    payments: list

    @property
    def settled(self):
        return self.bill is not None


def bill_sheet(workshop, branch, card):
    """The bill of this job card, as it shows and prints. The card comes from job_card(), with
    its car, model, brand and customer already read."""
    bill = bill_of(workshop, branch, card)
    job_lines = list(
        JobLine.objects.for_workshop(workshop)
        .filter(job_card=card)
        .order_by("id")
        .values_list("text", flat=True)
    )
    total = bill_total(workshop, card)
    if bill is None:
        customer_name, brand, car_model = printed_names(card)
        discount, payments = Decimal("0"), []
    else:
        customer_name, brand, car_model = bill.customer_name, bill.brand, bill.car_model
        discount, payments = bill.discount, payments_of(workshop, bill)
    return Sheet(
        bill=bill,
        customer_name=customer_name,
        brand=brand,
        car_model=car_model,
        plate=card.plate,
        mileage=card.mileage,
        job_lines=job_lines,
        job_pad=range(max(0, JOB_ROWS - len(job_lines))),
        # Parts fill this table with Parts on the job card (Phase 6).
        part_pad=range(PART_ROWS),
        labour=card.labour,
        parts=Decimal("0"),
        total=total,
        discount=discount,
        net=total - discount,
        payments=payments,
    )

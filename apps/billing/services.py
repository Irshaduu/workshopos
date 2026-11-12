"""Changes in billing: settling a bill (docs/rules/settle-bill.md, ADR-0032)."""

from decimal import Decimal

from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import transaction
from django.http import Http404
from django.template.defaultfilters import floatformat
from django.utils.formats import date_format
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.audit.selectors import money_date_problem
from apps.billing.models import Bill, BillCounter, Payment, PaymentMethod, number_from
from apps.billing.selectors import (
    bill_total,
    financial_year_of,
    nothing_to_settle,
    printed_names,
    saved_bill,
)
from apps.jobs.selectors import job_card
from apps.jobs.services import end_as_settled, lock_job_card
from apps.workshops.services import save_once

#: The words for a bill that comes to nothing (SETTLE-18).
NOTHING_TO_BILL = gettext_lazy(
    "This bill comes to 0.00, so there is nothing to settle. Add the labour charge, or "
    "cancel the job card with its reason."
)


def money(amount):
    """An amount as a bill shows it: paise always, like 45,000.00 (docs/DESIGN.md)."""
    return floatformat(amount, "2g")


class TotalChanged(ValidationError):
    """The bill's total moved after the person saw it, so a discount would be worked out on a
    total nobody saw (SETTLE-26). A refusal like the others, in plain words, with the total
    now."""

    def __init__(self, total):
        super().__init__(
            _(
                "The bill changed while you were settling: its total is now %(total)s. "
                "Check the payments, then settle again."
            )
            % {"total": money(total)}
        )
        self.total = total


class NotOpen(Exception):
    """The job card was settled or cancelled before this send (SETTLE-25). It carries the
    card, so the page can say who settled it and when."""

    def __init__(self, card):
        super().__init__(card.number)
        self.card = card


def check_settle(workshop, by, card, total, paid_on, payments, *, total_seen):
    """Refuses a settle that breaks a rule, saying each one in plain words (SETTLE-16 to
    SETTLE-21, SETTLE-26). When it keeps them all, it answers with the discount: the rest of
    the bill (SETTLE-19). `payments` are the boxes typed, by method, and `total_seen` is the
    total the person saw.

    The settle box asks this before it shows the check, and settle_bill() asks it again
    under the lock, so both answer the same, and the check shows the discount that is saved.
    """
    if total_seen != total:
        raise TotalChanged(total)
    if nothing_to_settle(total):
        raise ValidationError(NOTHING_TO_BILL)
    problems = {}
    paid = sum(payments.values(), Decimal("0"))
    if any(amount <= 0 for amount in payments.values()):
        problems[NON_FIELD_ERRORS] = [_("Type an amount above zero.")]
    elif not payments:
        problems[NON_FIELD_ERRORS] = [_("Type what the customer paid, in at least one box.")]
    elif paid > total:
        problems[NON_FIELD_ERRORS] = [
            _("The payments come to %(paid)s, more than the total of %(total)s.")
            % {"paid": money(paid), "total": money(total)}
        ]
    if (problem := money_date_problem(workshop, by, paid_on)) is not None:
        problems["paid_on"] = [problem]
    elif paid_on < card.admitted_date:
        problems["paid_on"] = [
            _("The date paid cannot be before the car came in, on %(day)s.")
            % {"day": date_format(card.admitted_date)}
        ]
    if problems:
        raise ValidationError(problems)
    return total - paid


def settle_bill(workshop, branch, card_key, bill_key, by, *, paid_on, payments, total_seen):
    """Settles a job card's bill once, however many times the box is sent (SETTLE-14 to
    SETTLE-33). It answers with the bill.

    The card's lock comes first and the question whether the key is saved after it, so a
    double tap waits, then finds the bill (SETTLE-25). Then the number's counter is locked,
    always after the card, so two settles never wait for each other in a circle. A refusal
    undoes all of it, so a settle that fails uses no number (SETTLE-29).

    `total_seen` is the total the person saw: a bill that moved since then is refused
    (SETTLE-26).
    """
    with transaction.atomic():
        card = lock_job_card(workshop, branch, card_key)
        saved = saved_bill(workshop, branch, bill_key)
        if saved is not None:
            # A key is the bill of one card only; any other card's send is not found.
            if saved.job_card_id != card.pk:
                raise Http404
            return saved
        if not card.is_open:
            raise NotOpen(card)
        discount = check_settle(
            workshop,
            by,
            card,
            bill_total(workshop, card),
            paid_on,
            payments,
            total_seen=total_seen,
        )
        # Read with its links after the card's lock, which joins nothing, and before the
        # number's lock, so that lock is held as briefly as it can be (CONTRIBUTING.md).
        customer_name, brand, car_model = printed_names(job_card(workshop, branch, card_key))

        year = financial_year_of(paid_on)
        counter, _made = (
            BillCounter.objects.for_workshop(workshop)
            .for_branch(branch)
            .select_for_update()
            .get_or_create(workshop=workshop, branch=branch, financial_year=year)
        )
        counter.last_number += 1
        counter.save(update_fields=["last_number"])
        # Always saved now: this card's own repeat was answered above, under its lock, and a
        # key another card's settle saved at the same moment is not found (parent).
        bill, _saved_now = save_once(
            Bill(
                id=bill_key,
                workshop=workshop,
                branch=branch,
                job_card=card,
                number=number_from(year, counter.last_number),
                date=paid_on,
                settled_by=by,
                discount=discount,
                customer_name=customer_name,
                brand=brand,
                car_model=car_model,
            ),
            parent="job_card",
        )
        for method in PaymentMethod.values:
            if method in payments:
                Payment(workshop=workshop, bill=bill, method=method, amount=payments[method]).save()
        end_as_settled(card, by)
    return bill

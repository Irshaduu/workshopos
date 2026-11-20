"""Changes in billing: settling a bill, and changing a settled bill's payments
(docs/rules/settle-bill.md, ADR-0032)."""

from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import floatformat
from django.utils.formats import date_format
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from apps.audit.models import ChangedRecord
from apps.audit.selectors import kept_change, money_date_problem
from apps.audit.services import keep_change
from apps.billing.models import Bill, BillCounter, Payment, PaymentMethod, number_from
from apps.billing.selectors import (
    BOXES,
    bill_figures,
    bill_total,
    change_refusal,
    financial_year_of,
    nothing_to_settle,
    printed_names,
    saved_bill,
)
from apps.core.text import tidy_spaces
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


#: The words for a total that moved since the person saw it, while settling (SETTLE-26).
SETTLING_TOTAL_MOVED = gettext_lazy(
    "The bill changed while you were settling: its total is now %(total)s. Check the "
    "payments, then settle again."
)
#: The same, while changing a settled bill's payments (SETTLE-39).
CHANGING_TOTAL_MOVED = gettext_lazy(
    "The bill changed while you had this box open: its total is now %(total)s. Check the "
    "payments, then change them again."
)


class TotalChanged(ValidationError):
    """The bill's total moved after the person saw it, so a discount would be worked out on a
    total nobody saw (SETTLE-26). A refusal like the others, in plain words, with the total
    now."""

    def __init__(self, total, words=SETTLING_TOTAL_MOVED):
        super().__init__(words % {"total": money(total)})
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
    if (problem := _payments_problem(total, payments)) is not None:
        problems[NON_FIELD_ERRORS] = [problem]
    if (problem := _date_problem(workshop, by, card, paid_on)) is not None:
        problems["paid_on"] = [problem]
    if problems:
        raise ValidationError(problems)
    return total - sum(payments.values(), Decimal("0"))


def _payments_problem(total, payments):
    """What is wrong with the payments typed, in plain words; None when nothing is: each
    above zero, at least one, and never more than the total (SETTLE-16, SETTLE-17)."""
    paid = sum(payments.values(), Decimal("0"))
    if any(amount <= 0 for amount in payments.values()):
        return _("Type an amount above zero.")
    if not payments:
        return _("Type what the customer paid, in at least one box.")
    if paid > total:
        return _("The payments come to %(paid)s, more than the total of %(total)s.") % {
            "paid": money(paid),
            "total": money(total),
        }
    return None


def _date_problem(workshop, by, card, day):
    """What is wrong with the date paid typed, in plain words; None when nothing is: the
    money date rules, and never before the car came in (SETTLE-21)."""
    if (problem := money_date_problem(workshop, by, day)) is not None:
        return problem
    if day < card.admitted_date:
        return _("The date paid cannot be before the car came in, on %(day)s.") % {
            "day": date_format(card.admitted_date)
        }
    return None


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


class PastTheWindow(Exception):
    """Office is past the edit window for this bill, and only an owner may change it now
    (CHANGE-9, CHANGE-12). It carries the refusal's words."""

    def __init__(self, words):
        super().__init__(words)
        self.words = words


class BillChanged(Exception):
    """Someone changed the bill's payments or its date paid after this box opened, or the
    send does not say what the box opened with, so the send is refused whole, never merged
    box by box (SETTLE-52)."""

    def __init__(self):
        self.words = _(
            "Someone changed this bill while you had it open. Here it is as it is now: check "
            "it, then change it again."
        )
        super().__init__(self.words)


@dataclass(frozen=True)
class PaymentsChange:
    """What a Change payments send would do, worked out before anything is saved
    (SETTLE-39): the bill's figures (bill_figures()) as saved, and as they would be."""

    before: dict
    after: dict

    @property
    def moved(self):
        return self.after != self.before


def check_change(
    workshop, by, card, bill, total, *, paid_on, payments, opening, reason, total_seen
):
    """Refuses a change that breaks a rule, in plain words, or answers with what it would do
    (SETTLE-39, SETTLE-44, SETTLE-52, SETTLE-54, CHANGE-5, CHANGE-9 to CHANGE-12).

    `payments` are the boxes typed, by method; `opening` is what each box held when the box
    opened, or None when the send does not say; `total_seen` is the total the person saw.
    The box asks this before it shows the check, and change_payments() asks it again under
    the locks, so both answer the same. A double tap is answered before this, by the
    change's own key.
    """
    if (refusal := change_refusal(workshop, by, bill)) is not None:
        raise PastTheWindow(refusal)
    before = bill_figures(workshop, bill)
    saved = {box: before[box] for box in BOXES}
    if opening != saved:
        raise BillChanged
    typed = {
        "paid_on": paid_on,
        **{method: payments.get(method) for method in PaymentMethod.values},
    }
    if typed == saved:
        return PaymentsChange(before, before)
    if total_seen != total:
        raise TotalChanged(total, CHANGING_TOTAL_MOVED)
    problems = {}
    if (problem := _payments_problem(total, payments)) is not None:
        problems[NON_FIELD_ERRORS] = [problem]
    # Only a changed date is judged, on the day it is changed (SETTLE-54).
    if paid_on != bill.date:
        if (problem := _date_problem(workshop, by, card, paid_on)) is not None:
            problems["paid_on"] = [problem]
        elif financial_year_of(paid_on) != financial_year_of(bill.date):
            problems["paid_on"] = [
                _(
                    "The date paid must stay in the bill's financial year, because its number "
                    "%(number)s belongs to that year."
                )
                % {"number": bill.number}
            ]
    # Why is asked only of a change: a send that changes nothing needs no reason (CHANGE-5).
    if not tidy_spaces(reason):
        problems["reason"] = [_("Type why you are changing this bill.")]
    if problems:
        raise ValidationError(problems)
    return PaymentsChange(before, {**typed, "discount": total - sum(payments.values())})


def change_payments(
    workshop,
    branch,
    card_key,
    change_key,
    by,
    *,
    paid_on,
    payments,
    opening,
    reason,
    total_seen,
):
    """Changes a settled bill's payments and its date paid, and keeps the change in the change
    history under `change_key`, in one locked transaction (SETTLE-38, SETTLE-39, SETTLE-41,
    SETTLE-42, SETTLE-44 to SETTLE-46, SETTLE-52, SETTLE-54). It answers with the bill and
    what the send did, or None for a repeat of a change kept already.

    The card's lock comes first and the bill's after it, the same order as every save of a
    card and its bill, so two saves never wait for each other in a circle. Both join nothing,
    and the payments are read after them. The question whether the key is kept comes after
    the locks, so a double tap waits, then finds its first change (SETTLE-52). A refusal
    undoes all of it, the Change included. The bill keeps its number, and the moment it was
    settled and by whom (SETTLE-42).
    """
    with transaction.atomic():
        card = lock_job_card(workshop, branch, card_key)
        bill = get_object_or_404(
            Bill.objects.for_workshop(workshop).for_branch(branch).select_for_update(),
            job_card=card,
        )
        if (kept := kept_change(workshop, branch, change_key)) is not None:
            # A key is the change of one bill only; any other bill's send is not found.
            if kept.record_key != bill.pk:
                raise Http404
            return bill, None
        change = check_change(
            workshop,
            by,
            card,
            bill,
            bill_total(workshop, card),
            paid_on=paid_on,
            payments=payments,
            opening=opening,
            reason=reason,
            total_seen=total_seen,
        )
        if change.moved:
            _apply(workshop, bill, change.after)
            keep_change(
                workshop,
                branch,
                by,
                key=change_key,
                what=ChangedRecord.BILL,
                record_key=bill.pk,
                label=f"{bill.number}, {card.plate}",
                before=change.before,
                after=change.after,
                reason=reason,
            )
    return bill, change


def _apply(workshop, bill, after):
    """Saves the bill's new date paid, discount and payments: a payment changed in its own
    row, a new method as a new row, and a method left empty removed (SETTLE-15, SETTLE-39)."""
    bill.date = after["paid_on"]
    bill.discount = after["discount"]
    bill.save(update_fields=["date", "discount"])
    saved = {
        payment.method: payment
        for payment in Payment.objects.for_workshop(workshop).filter(bill=bill)
    }
    for method in PaymentMethod.values:
        amount, payment = after[method], saved.get(method)
        if payment is None and amount is not None:
            Payment(workshop=workshop, bill=bill, method=method, amount=amount).save()
        elif payment is not None and amount is None:
            payment.delete()
        elif payment is not None and payment.amount != amount:
            payment.amount = amount
            payment.save(update_fields=["amount"])

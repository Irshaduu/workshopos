"""Pages of billing: thin, from the request to the form, a service and the answer (ADR-0005).

A GET on an address that saves shows a real page: a session can end while someone settles,
and signing in brings them back with a GET (SIGN-38).
"""

import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods

from apps.accounts.decorators import page
from apps.audit.selectors import kept_change
from apps.billing import services
from apps.billing.forms import ChangePaymentsForm, SettleForm
from apps.billing.models import PaymentMethod
from apps.billing.selectors import (
    OFFICE_PAID_BILLS_DAYS,
    bill_of,
    bill_sheet,
    bill_total,
    change_refusal,
    nothing_to_settle,
    paid_bills_for,
    saved_bill,
)
from apps.billing.services import (
    NOTHING_TO_BILL,
    BillChanged,
    NotOpen,
    PastTheWindow,
    check_change,
    check_settle,
    settle_bill,
)
from apps.jobs.selectors import job_card, unfilled
from apps.jobs.services import not_open_words


@page("pending_and_paid_bills", "billing.see_paid_bills")
@require_GET
def paid_bills(request):
    """The first, plain Paid bills, so a settled bill can be found (SETTLE-53)."""
    context = {
        "rows": paid_bills_for(request.workshop, request.branch, request.user),
        "every_bill": request.user.has_perm("billing.see_every_paid_bill"),
        "office_days": OFFICE_PAID_BILLS_DAYS,
    }
    return render(request, "billing/paid_bills.html", context)


@page("settle_bill", "billing.see_bill")
@require_GET
def bill(request, key):
    """A job card's bill: a preview while the card is open, the bill itself once settled
    (SETTLE-2, SETTLE-6)."""
    card = job_card(request.workshop, request.branch, key)
    return _bill_or_card(request, card, new_key=uuid.uuid7())


@page("settle_bill", "billing.settle_bill")
@require_http_methods(["GET", "POST"])
def settle(request, key, new_key):
    """Settles a job card's bill once (SETTLE-14 to SETTLE-26). The settle box sends the total
    it showed (SETTLE-26). A send with a discount is answered first with the check (SETTLE-20),
    whose Settle bill button sends the box again, with the total the check showed."""
    card = job_card(request.workshop, request.branch, key)
    # First, because the box's checks would refuse a repeat as a card already settled.
    saved = saved_bill(request.workshop, request.branch, new_key)
    if saved is not None:
        if saved.job_card_id != card.pk:
            raise Http404
        if request.method == "POST":
            return _settled(request, saved, card)
        return redirect("billing:bill", key=card.pk)
    if request.method == "GET":
        return _bill_or_card(request, card, new_key=new_key)
    if not card.is_open:
        return _ended(request, card)

    form = SettleForm(request.POST, workshop=request.workshop, user=request.user, job_card=card)
    if not form.is_valid():
        return _bill_page(request, card, new_key=new_key, form=form)
    paid_on, payments = form.cleaned_data["paid_on"], form.payments()
    seen = _total_seen(request.POST)
    total = bill_total(request.workshop, card)
    try:
        discount = check_settle(
            request.workshop, request.user, card, total, paid_on, payments, total_seen=seen
        )
    except ValidationError as refused:
        form.add_error(None, refused)
        return _bill_page(request, card, new_key=new_key, form=form)

    if discount and "checked" not in request.POST:
        check = Check(total, _labelled(payments), discount, paid_on)
        return _bill_page(request, card, new_key=new_key, form=form, check=check)
    try:
        saved = settle_bill(
            request.workshop,
            request.branch,
            key,
            new_key,
            request.user,
            paid_on=paid_on,
            payments=payments,
            total_seen=seen,
        )
    except NotOpen as ended:
        return _ended(request, ended.card)
    except ValidationError as refused:
        form.add_error(None, refused)
    else:
        return _settled(request, saved, card)
    # Read again, so the box shows the bill as it is now.
    card = job_card(request.workshop, request.branch, key)
    return _bill_page(request, card, new_key=new_key, form=form)


@page("settle_bill", "billing.settle_bill")
@require_http_methods(["GET", "POST"])
def change_payments(request, key, change_key):
    """Changes a settled bill's payments and its date paid, with the reason why (SETTLE-38,
    SETTLE-39, SETTLE-41, SETTLE-42, SETTLE-44 to SETTLE-46, SETTLE-52, SETTLE-54). The box's
    address holds the new change's key, so a double tap shows the change kept the first time.
    A send that leaves a discount is answered first with the check (SETTLE-39), whose Change
    payments button sends the box again."""
    card = job_card(request.workshop, request.branch, key)
    settled = bill_of(request.workshop, request.branch, card)
    if settled is None:
        # Only a settled card has a bill to change; its bill page says what the card has.
        return redirect("billing:bill", key=card.pk)
    # First, because the box's checks would refuse a repeat as a bill changed since it opened.
    kept = kept_change(request.workshop, request.branch, change_key)
    if kept is not None:
        if kept.record_key != settled.pk:
            raise Http404
        if request.method == "POST":
            return _changed(request, settled, card)
        return redirect("billing:bill", key=card.pk)
    if request.method == "GET":
        return _bill_page(request, card, change_key=change_key)

    form = ChangePaymentsForm(
        request.POST, workshop=request.workshop, user=request.user, job_card=card, bill=settled
    )
    if not form.is_valid():
        return _bill_page(request, card, change_key=change_key, change_form=form)
    typed = {
        "paid_on": form.cleaned_data["paid_on"],
        "payments": form.payments(),
        "opening": form.opening(),
        "reason": form.cleaned_data["reason"],
        "total_seen": _total_seen(request.POST),
    }
    total = bill_total(request.workshop, card)
    try:
        change = check_change(request.workshop, request.user, card, settled, total, **typed)
        if change.moved and change.after["discount"] and "checked" not in request.POST:
            check = Check.of_change(total, change)
            return _bill_page(
                request, card, change_key=change_key, change_form=form, change_check=check
            )
        if change.moved:
            settled, change = services.change_payments(
                request.workshop, request.branch, key, change_key, request.user, **typed
            )
    except PastTheWindow:
        # The bill page says why, in place of the button (SETTLE-46).
        messages.warning(request, _("Nothing was saved."))
        return redirect("billing:bill", key=card.pk)
    except BillChanged as changed:
        return _changed_first(request, key, change_key, form, changed)
    except ValidationError as refused:
        form.add_error(None, refused)
        # Read again, so the box shows the bill as it is now.
        card = job_card(request.workshop, request.branch, key)
        return _bill_page(request, card, change_key=change_key, change_form=form)
    if change is None or change.moved:
        return _changed(request, settled, card)
    messages.info(request, _("Nothing changed, so nothing was saved."))
    return redirect("billing:bill", key=card.pk)


def _changed(request, settled, card):
    """The bill as changed, with its notice and its sound, for the first send and for a
    double tap alike (SETTLE-52)."""
    messages.success(
        request,
        _("The payments of %(number)s are changed. The change is kept in the change history.")
        % {"number": settled.number},
    )
    return redirect("billing:bill", key=card.pk)


def _changed_first(request, key, change_key, form, changed):
    """Someone changed the bill while this box was open: the box opens again with the bill as
    it is now, and with the reason as it was typed (SETTLE-52)."""
    card = job_card(request.workshop, request.branch, key)
    fresh = ChangePaymentsForm(
        initial={"reason": form.cleaned_data["reason"]},
        workshop=request.workshop,
        user=request.user,
        job_card=card,
        bill=bill_of(request.workshop, request.branch, card),
    )
    return _bill_page(
        request, card, change_key=change_key, change_form=fresh, change_problem=changed.words
    )


#: A method with no payment, as a check adds it up.
ZERO = Decimal("0")


@dataclass(frozen=True)
class Check:
    """What the server worked out, shown before anything is saved (SETTLE-20). A change's
    check also shows what each changed figure was (SETTLE-39): each payment is its word, its
    amount and what it was, or None when it did not move."""

    total: Decimal
    payments: list
    discount: Decimal
    paid_on: datetime.date
    discount_was: Decimal | None = None
    paid_on_was: datetime.date | None = None

    @property
    def net(self):
        return self.total - self.discount

    @property
    def net_was(self):
        return None if self.discount_was is None else self.total - self.discount_was

    @property
    def today(self):
        return self.paid_on == timezone.localdate()

    @classmethod
    def of_change(cls, total, change):
        """The check of a change: each method paid before or after, as it will be, with what
        it was when it moved. A method left empty shows 0.00, so the sum still adds up."""
        before, after = change.before, change.after

        def was(name, nothing=None):
            """What a figure was, when it moved; None when it did not."""
            return None if before[name] == after[name] else (before[name] or nothing)

        payments = [
            (PaymentMethod(method).label, after[method] or ZERO, was(method, ZERO))
            for method in PaymentMethod.values
            if before[method] is not None or after[method] is not None
        ]
        return cls(
            total,
            payments,
            after["discount"],
            after["paid_on"],
            discount_was=was("discount"),
            paid_on_was=was("paid_on"),
        )


def _labelled(payments):
    """Each payment typed, as its method's word and its amount, in the box's order. A settle
    has nothing it was."""
    return [(PaymentMethod(method).label, amount, None) for method, amount in payments.items()]


def _total_seen(data):
    """The total the person saw: the check's, or else the settle box's own (SETTLE-26). None
    when the send carries none, or carries something that is not an amount."""
    try:
        total = Decimal(data.get("checked", data.get("seen", "")))
    except InvalidOperation:
        return None
    return total if total.is_finite() else None


def _settled(request, saved, card):
    """The settled bill, with its notice and its sound, for the first send and for a double
    tap alike (SETTLE-24, SETTLE-25)."""
    messages.success(
        request,
        _("%(plate)s settled. Its bill number is %(number)s.")
        % {"plate": card.plate, "number": saved.number},
    )
    return redirect("billing:bill", key=card.pk)


def _ended(request, card):
    """A send to a card that was settled or cancelled first: nothing is saved, and the page
    says so, with who settled it and when (SETTLE-25)."""
    if not card.is_settled:
        messages.warning(request, not_open_words(card))
        return redirect("jobs:edit", key=card.pk)
    settled = bill_of(request.workshop, request.branch, card)
    messages.warning(
        request,
        _("%(who)s settled this bill on %(when)s, so nothing was saved.")
        % {
            "who": settled.settled_by.get_full_name() or settled.settled_by.get_username(),
            "when": date_format(timezone.localtime(settled.settled_at), "DATETIME_FORMAT"),
        },
    )
    return redirect("billing:bill", key=card.pk)


def _bill_or_card(request, card, *, new_key):
    """A cancelled card has no bill, so its bill's address opens the card (SETTLE-4)."""
    if card.is_cancelled:
        return redirect("jobs:edit", key=card.pk)
    return _bill_page(request, card, new_key=new_key)


def _month_words():
    """Each month's short word as a date shows it, like Sep, for the date chip's script, so
    the chip reads like every other date on the page (docs/DESIGN.md)."""
    return "|".join(date_format(datetime.date(2026, month, 1), "M") for month in range(1, 13))


def _bill_page(
    request,
    card,
    *,
    new_key=None,
    form=None,
    check=None,
    change_key=None,
    change_form=None,
    change_check=None,
    change_problem="",
):
    """The one page of a bill: a preview with its settle box, or the settled bill with its
    change box, or the words that say why it has none."""
    sheet = bill_sheet(request.workshop, request.branch, card)
    context = {"card": card, "sheet": sheet, "check": check, "change_check": change_check}
    if sheet.settled:
        context |= _change_parts(request, card, sheet.bill, change_form, change_problem)
        context["change_key"] = change_key or uuid.uuid7()
    else:
        context |= _settle_parts(request, card, sheet, new_key or uuid.uuid7(), form)
    boxes = context.get("form") or context.get("change_form")
    context["months"] = _month_words() if boxes else ""
    return render(request, "billing/bill.html", context)


def _settle_parts(request, card, sheet, new_key, form):
    """What a preview offers: its settle box, for the roles that settle."""
    offered = card.is_open and request.user.has_perm("billing.settle_bill")
    # A bill of 0.00 is never settled, so it offers no box that could only be refused; the
    # page says why instead (SETTLE-18, ROLE-12).
    nothing = offered and nothing_to_settle(sheet.total)
    if not offered or nothing:
        form = None
    elif form is None:
        form = SettleForm(workshop=request.workshop, user=request.user, job_card=card)
    return {
        "new_key": new_key,
        "form": form,
        "unfilled": unfilled(request.workshop, card) if form is not None else (),
        "nothing_to_bill": NOTHING_TO_BILL if nothing else "",
    }


def _change_parts(request, card, settled, form, problem):
    """What a settled bill offers the roles that settle: its change box, or for Office past
    the edit window the words that say why not, in place of the button (SETTLE-46, ROLE-12)."""
    if not request.user.has_perm("billing.settle_bill"):
        return {}
    if (late := change_refusal(request.workshop, request.user, settled)) is not None:
        return {"change_refusal": late}
    if form is None:
        form = ChangePaymentsForm(
            workshop=request.workshop, user=request.user, job_card=card, bill=settled
        )
    return {"change_form": form, "change_problem": problem}

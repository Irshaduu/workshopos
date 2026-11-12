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
from apps.billing.forms import SettleForm
from apps.billing.models import PaymentMethod
from apps.billing.selectors import bill_of, bill_sheet, bill_total, nothing_to_settle, saved_bill
from apps.billing.services import NOTHING_TO_BILL, NotOpen, check_settle, settle_bill
from apps.jobs.selectors import job_card, unfilled
from apps.jobs.services import not_open_words


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


@dataclass(frozen=True)
class Check:
    """What the server worked out, shown before anything is saved (SETTLE-20)."""

    total: Decimal
    payments: list
    discount: Decimal
    paid_on: datetime.date

    @property
    def net(self):
        return self.total - self.discount

    @property
    def today(self):
        return self.paid_on == timezone.localdate()


def _labelled(payments):
    """Each payment typed, as its method's word and its amount, in the box's order."""
    return [(PaymentMethod(method).label, amount) for method, amount in payments.items()]


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


def _bill_page(request, card, *, new_key, form=None, check=None):
    """The one page of a bill: a preview with its settle box, or the settled bill."""
    sheet = bill_sheet(request.workshop, request.branch, card)
    offered = card.is_open and request.user.has_perm("billing.settle_bill")
    # A bill of 0.00 is never settled, so it offers no box that could only be refused; the
    # page says why instead (SETTLE-18, ROLE-12).
    nothing = offered and nothing_to_settle(sheet.total)
    if not offered or nothing:
        form = None
    elif form is None:
        form = SettleForm(workshop=request.workshop, user=request.user, job_card=card)
    context = {
        "card": card,
        "sheet": sheet,
        "new_key": new_key,
        "form": form,
        "unfilled": unfilled(request.workshop, card) if form is not None else (),
        "check": check,
        "months": _month_words() if form is not None else "",
        "nothing_to_bill": NOTHING_TO_BILL if nothing else "",
    }
    return render(request, "billing/bill.html", context)

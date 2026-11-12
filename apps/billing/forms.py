"""The settle box (docs/rules/settle-bill.md). A form checks what was typed, box by box; the
rules that need the bill, like never above its total, are the service's (check_settle)."""

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.audit.selectors import earliest_money_date
from apps.billing.models import PaymentMethod
from apps.core.money import MoneyFormField


class SettleForm(forms.Form):
    """The date paid, and one money box for each payment method, all empty at first
    (SETTLE-15, SETTLE-21). Each box's name is its method, so a box is a payment by that
    method. Only Office and owners ever get it (SETTLE-47)."""

    paid_on = forms.DateField(
        label=_("Date paid"),
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    # Each box takes its method's own word, so the box, the check and the bill say the same.
    # A test checks there is one box for each method, in its order.
    cash = MoneyFormField(label=PaymentMethod.CASH.label, required=False)
    upi = MoneyFormField(label=PaymentMethod.UPI.label, required=False)
    card = MoneyFormField(label=PaymentMethod.CARD.label, required=False)
    bank_transfer = MoneyFormField(label=PaymentMethod.BANK_TRANSFER.label, required=False)

    def __init__(self, *args, workshop, user, job_card, **kwargs):
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        self.fields["paid_on"].initial = today
        # The date box offers only the days this person may choose: never after today, never
        # before the car came in, and for Office not before the back-date limit. Only the
        # server decides (CHANGE-15).
        earliest = job_card.admitted_date
        if (limit := earliest_money_date(workshop, user, today)) is not None:
            earliest = max(earliest, limit)
        self.fields["paid_on"].widget.attrs.update(
            max=today.isoformat(),
            min=min(earliest, today).isoformat(),
            # Its words are the chip's label above it (billing/bill.html).
            **{"aria-labelledby": "settle-date-label"},
        )
        for method in PaymentMethod.values:
            self.fields[method].widget.attrs.update(
                {"class": "field__input pay__amount num", "autocomplete": "off"}
            )

    def payments(self):
        """Each method typed, with its amount, in the box's order."""
        return {
            method: amount
            for method in PaymentMethod.values
            if (amount := self.cleaned_data.get(method)) is not None
        }

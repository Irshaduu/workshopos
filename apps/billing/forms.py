"""The settle box and the change box (docs/rules/settle-bill.md). A form checks what was
typed, box by box; the rules that need the bill, like never above its total, are the
service's (check_settle, check_change)."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.audit.selectors import earliest_money_date
from apps.billing.models import PaymentMethod
from apps.billing.selectors import BOXES, bill_figures, financial_year_days, financial_year_of
from apps.core.money import MoneyFormField


class SettleForm(forms.Form):
    """The date paid, and one money box for each payment method, all empty at first
    (SETTLE-15, SETTLE-21). Each box's name is its method, so a box is a payment by that
    method. Only Office and owners ever get it (SETTLE-47)."""

    #: The id of the words over the date box, which name it for a screen reader.
    date_label_id = "settle-date-label"

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
        self.today = timezone.localdate()
        self.fields["paid_on"].initial = self.today
        earliest, latest = self.date_limits(workshop, user, job_card)
        self.fields["paid_on"].widget.attrs.update(
            max=latest.isoformat(),
            min=min(earliest, latest).isoformat(),
            # Its words are the chip's label above it (billing/_pay_boxes.html), and the chip
            # reads today from here, because the last day offered may be another.
            **{"aria-labelledby": self.date_label_id, "data-today-iso": self.today.isoformat()},
        )
        for method in PaymentMethod.values:
            self.fields[method].widget.attrs.update(
                {"class": "field__input pay__amount num", "autocomplete": "off"}
            )

    def date_limits(self, workshop, user, job_card):
        """The first and the last day the date box offers: the days this person may choose,
        never after today, never before the car came in, and for Office not before the
        back-date limit. Only the server decides (CHANGE-15)."""
        earliest = job_card.admitted_date
        if (limit := earliest_money_date(workshop, user, self.today)) is not None:
            earliest = max(earliest, limit)
        return earliest, self.today

    def money_boxes(self):
        """The box for each method, in the box's order."""
        return [self[method] for method in PaymentMethod.values]

    def payments(self):
        """Each method typed, with its amount, in the box's order."""
        return {
            method: amount
            for method in PaymentMethod.values
            if (amount := self.cleaned_data.get(method)) is not None
        }


class ChangePaymentsForm(SettleForm):
    """The settle box as the bill was saved, and why (SETTLE-39). Each box keeps what it held
    when the box opened, in a hidden opening value, so a change someone else saved first is
    refused (SETTLE-52). Why is checked by the service, because only a change needs one."""

    date_label_id = "change-date-label"

    reason = forms.CharField(
        label=_("Why are you changing this bill?"),
        max_length=255,
        required=False,
        help_text=_("Kept in the change history, with what it was."),
    )

    def __init__(self, *args, workshop, user, job_card, bill, **kwargs):
        self.bill = bill
        super().__init__(*args, workshop=workshop, user=user, job_card=job_card, **kwargs)
        saved = bill_figures(workshop, bill)
        for box in BOXES:
            self.fields[box].initial = saved[box]
            self.fields[box].show_hidden_initial = True
        self.fields["reason"].widget.attrs.update({"class": "field__input", "autocomplete": "off"})

    def date_limits(self, workshop, user, job_card):
        """The settle box's days, kept inside the bill's financial year (SETTLE-44), and the
        saved day always offered, even one Office could not type today (SETTLE-54). So for a
        bill dated further back than Office may date, the box also offers the days between,
        and only the server refuses them."""
        earliest, latest = super().date_limits(workshop, user, job_card)
        first, last = financial_year_days(financial_year_of(self.bill.date))
        return min(max(earliest, first), self.bill.date), min(latest, last)

    def opening(self):
        """What each box held when the box opened, from its hidden opening values; None when
        one cannot be read. A send that does not hold them never matches the saved bill, whose
        date paid is never empty, so it is refused as a box opened on another bill
        (SETTLE-52)."""
        found = {}
        for box in BOXES:
            field = self.fields[box]
            sent = field.hidden_widget().value_from_datadict(
                self.data, self.files, self.add_initial_prefix(box)
            )
            try:
                found[box] = field.to_python(sent)
            except ValidationError:
                return None
        return found

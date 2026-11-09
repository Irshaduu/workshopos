"""Checks what was typed on a job card (ADR-0005, docs/rules/job-card.md).

A form holds only what its role may change (ROLE-13): JobCardForm is Floor's, and
OfficeJobCardForm adds the customer and the labour charge, chosen by a permission.

Every box keeps the value the page opened with (show_hidden_initial), so changed_data says
what this person changed, not how the page differs from the record. A service applies only
that, so nobody undoes another person's save by accident (JOB-43).
"""

import re
from dataclasses import dataclass

from django import forms
from django.core.exceptions import ValidationError
from django.forms import formset_factory
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.money import MoneyFormField
from apps.core.text import tidy_name, tidy_spaces
from apps.jobs.models import MILEAGE_MAX, ConcernStatus
from apps.staff.models import StaffMember
from apps.staff.selectors import may_lead
from apps.vehicles.models import (
    CHASSIS_CODE_MAX_LENGTH,
    OWN_COLOUR,
    Colour,
    contact_number_problem,
    plate_problem,
    tidy_chassis_code,
    tidy_contact_number,
    tidy_plate,
    tidy_vin,
    vin_problem,
)

#: The colour box starts here when a car has no colour of its own. A browser's colour box
#: always sends a colour, so this keeps an untouched box from looking changed, and tells
#: Other with nothing chosen from a real pick (JOB-21).
OTHER_STARTS_AT = "#808080"

#: A mileage as people write it: digits, with commas only where they truly group a number,
#: so the last group has three digits, and km after it (JOB-22). The digits are 0 to 9 only:
#: Python reads more.
READING = re.compile(
    r"(?P<digits>[0-9]{1,3}(?:,[0-9]{2,3})*,[0-9]{3}|[0-9]+)"
    r"\s*(?:k\s*\.?\s*m\s*\.?\s*s?|kilomet(?:er|re)s?)?",
    re.IGNORECASE,
)
#: Longer than any odometer, and Python refuses to read a very long line of digits.
READING_MAX_LENGTH = 20
MILEAGE_WORDS = _("Type the kilometres as a whole number, like 132022. Miles are not taken.")


def box(extra=None, **attrs):
    """The attributes of a box on this page. A box with a placeholder wears the red hairline
    while it is empty (JOB-48): the mark is declared here, beside the field."""
    return {"class": "job-input", **(extra or {}), **attrs}


#: The empty placeholder that gives a box its hairline. No hint text in an empty box.
MARKED = {"placeholder": " "}
#: A box for letters and digits off the car: capitals as you type, and no spelling help.
OFF_THE_CAR = {"autocapitalize": "characters", "spellcheck": "false", "autocomplete": "off"}


class MileageField(forms.IntegerField):
    """A whole number of kilometres. Anything else is refused, never guessed (JOB-22)."""

    widget = forms.TextInput(attrs=box(MARKED, inputmode="numeric", autocomplete="off"))
    default_error_messages = {"invalid": MILEAGE_WORDS}

    def __init__(self, **kwargs):
        super().__init__(
            min_value=1,
            max_value=MILEAGE_MAX,
            error_messages={"min_value": MILEAGE_WORDS, "max_value": MILEAGE_WORDS},
            **kwargs,
        )

    def to_python(self, value):
        typed = "" if value is None else str(value).strip()
        if not typed:
            return None
        match = READING.fullmatch(typed)
        if match is None or len(match["digits"]) > READING_MAX_LENGTH:
            raise ValidationError(self.error_messages["invalid"], code="invalid")
        return int(match["digits"].replace(",", ""))


class LeadMechanicField(forms.ModelChoiceField):
    """The picker (JOB-23): a card keeps the person it has, shown with "not current" when
    they have been turned off or their designation has changed."""

    def label_from_instance(self, member):
        if member.may_lead:
            return member.name
        return f"{member.name}, {member.get_designation_display()}, {_('not current')}"


class JobCardForm(forms.Form):
    """The boxes every role may change. This is Floor's form (JOB-54).

    No box for the plate, the chassis code or the VIN tells the browser a length: it would
    cut a VIN typed in groups (JOB-19). Each is measured after it is tidied.
    """

    plate = forms.CharField(
        label=_("Plate Number"),
        error_messages={"required": _("Type the plate.")},
        widget=forms.TextInput(attrs=box(MARKED, **OFF_THE_CAR)),
    )
    brand = forms.CharField(
        label=_("Car Brand"),
        max_length=100,
        error_messages={"required": _("Type the brand.")},
        widget=forms.TextInput(attrs=box(MARKED, autocomplete="off")),
    )
    car_model = forms.CharField(
        label=_("Car Model"),
        max_length=100,
        error_messages={"required": _("Type the model.")},
        widget=forms.TextInput(attrs=box(MARKED, autocomplete="off")),
    )
    chassis_code = forms.CharField(
        label=_("Chassis Code"),
        required=False,
        widget=forms.TextInput(attrs=box(MARKED, **OFF_THE_CAR)),
    )
    vin = forms.CharField(
        label=_("VIN"),
        required=False,
        widget=forms.TextInput(attrs=box(MARKED, **OFF_THE_CAR)),
    )
    colour = forms.ChoiceField(
        label=_("Colour"),
        required=False,
        choices=[*Colour.choices, ("", _("Not set"))],
        widget=forms.RadioSelect,
    )
    colour_other = forms.CharField(
        label=_("Other colour"),
        required=False,
        widget=forms.TextInput(attrs={"type": "color", "class": "job-other"}),
    )
    mileage = MileageField(label=_("Mileage (Km)"), required=False)
    lead_mechanic = LeadMechanicField(
        label=_("Lead Mechanic"),
        queryset=StaffMember.objects.none(),
        required=False,
        empty_label=_("Not picked"),
        error_messages={"invalid_choice": _("This person can no longer be picked. Pick again.")},
        widget=forms.Select(attrs=box()),
    )
    admitted_date = forms.DateField(
        label=_("Admitted Date"),
        error_messages={
            "required": _("Type the date the car came in."),
            "invalid": _("Type a date, day first."),
        },
        widget=forms.DateInput(format="%Y-%m-%d", attrs=box(type="date")),
    )
    note = forms.CharField(
        label=_("Internal Note"),
        required=False,
        max_length=255,
        widget=forms.Textarea(attrs=box(rows=1, **{"class": "job-input job-note"})),
    )

    def __init__(self, *args, workshop, branch, mechanic_key=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lead_mechanic"].queryset = may_lead(workshop, branch, mechanic_key)
        # The picker stops at today, read on each page, but only the server decides (JOB-24).
        self.fields["admitted_date"].widget.attrs["max"] = timezone.localdate().isoformat()
        for field in self.fields.values():
            field.show_hidden_initial = True

    def opening_colour(self):
        """The colour's opening value, for a page that draws its choices one by one."""
        return self["colour"].as_hidden(only_initial=True)

    def paint(self):
        """The paint class's last word for what the colour says now. No colour has its own,
        never grey (JOB-21)."""
        return self["colour"].value() or "unset"

    def own_colour(self):
        """Other's own colour, which a script paints: a page has no inline style. Empty for
        every other colour."""
        return self["colour_other"].value() if self["colour"].value() == Colour.OTHER else ""

    def colour_word(self):
        """What the colour is called now, for a screen reader on the swatch."""
        return dict(self.fields["colour"].choices).get(self["colour"].value() or "", "")

    def clean_plate(self):
        plate = tidy_plate(self.cleaned_data["plate"])
        if problem := plate_problem(plate):
            raise ValidationError(problem)
        return plate

    def clean_brand(self):
        return tidy_name(self.cleaned_data["brand"])

    def clean_car_model(self):
        return tidy_spaces(self.cleaned_data["car_model"])

    def clean_chassis_code(self):
        code = tidy_chassis_code(self.cleaned_data["chassis_code"])
        if len(code) > CHASSIS_CODE_MAX_LENGTH:
            raise ValidationError(_("A chassis code has at most 20 characters."))
        return code

    def clean_vin(self):
        vin = tidy_vin(self.cleaned_data["vin"])
        if problem := vin_problem(vin):
            raise ValidationError(problem)
        return vin

    def clean_admitted_date(self):
        """Refused, never moved to today (JOB-24)."""
        admitted = self.cleaned_data["admitted_date"]
        if admitted > timezone.localdate():
            raise ValidationError(_("A car cannot be admitted on a date in the future."))
        return admitted

    def clean(self):
        cleaned = super().clean()
        # Only Other has a colour of its own (JOB-21).
        if cleaned.get("colour") == Colour.OTHER:
            own = cleaned.get("colour_other", "").lower()
            if not OWN_COLOUR.fullmatch(own) or own == OTHER_STARTS_AT:
                self.add_error("colour_other", _("Pick a colour."))
            cleaned["colour_other"] = own
        else:
            cleaned["colour_other"] = ""
        return cleaned

    def changes(self):
        """Only what this person changed since opening the page (JOB-43)."""
        changed = {name: self.cleaned_data[name] for name in self.changed_data}
        # The two colour boxes are one answer, and the second alone means nothing.
        if "colour" not in changed and "colour_other" in changed:
            if self.cleaned_data["colour"] == Colour.OTHER:
                changed["colour"] = Colour.OTHER
            else:
                del changed["colour_other"]
        elif "colour" in changed:
            changed["colour_other"] = self.cleaned_data["colour_other"]
        return changed


class OfficeJobCardForm(JobCardForm):
    """Floor's boxes, and who the customer is and the labour charge (ROLE-16, ROLE-17)."""

    customer_name = forms.CharField(
        label=_("Customer Name"),
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs=box(autocomplete="off")),
    )
    contact_number = forms.CharField(
        label=_("Contact Number"),
        required=False,
        widget=forms.TextInput(attrs=box(inputmode="tel", autocomplete="off")),
    )
    labour = MoneyFormField(
        label=_("Labour Charge (₹)"),
        allow_zero=True,
        zero_is_empty=True,
        required=False,
        widget=forms.TextInput(attrs=box(inputmode="decimal", autocomplete="off")),
    )

    def clean_customer_name(self):
        return tidy_name(self.cleaned_data["customer_name"])

    def clean_contact_number(self):
        number = tidy_contact_number(self.cleaned_data["contact_number"])
        if problem := contact_number_problem(number):
            raise ValidationError(problem)
        return number


def form_for(user):
    """The form this person's role may change, chosen by a permission (ROLE-13)."""
    if user.has_perm("jobs.save_customer_and_labour"):
        return OfficeJobCardForm
    return JobCardForm


class RowForm(forms.Form):
    """One row of a list. Empty words remove a saved row, and a new empty row is never
    saved (JOB-35, JOB-36), so no row requires them."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.show_hidden_initial = True

    def changes(self):
        """Only what this person changed on this row (JOB-43)."""
        return {name: self.cleaned_data[name] for name in self.changed_data}


class ConcernForm(RowForm):
    text = forms.CharField(
        label=_("Concern"),
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs=box(autocomplete="off")),
    )
    status = forms.ChoiceField(
        label=_("Status"),
        choices=ConcernStatus.choices,
        initial=ConcernStatus.PENDING,
        widget=forms.Select(attrs={"class": "job-status"}),
    )


class JobLineForm(RowForm):
    text = forms.CharField(
        label=_("Job"),
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs=box(autocomplete="off")),
    )


NewConcerns = formset_factory(ConcernForm, extra=1)
NewJobLines = formset_factory(JobLineForm, extra=1)


class CancelForm(forms.Form):
    """The reason a job card ends with no bill (JOB-50)."""

    reason = forms.CharField(
        label=_("Reason"),
        max_length=255,
        error_messages={"required": _("Type why this job card is cancelled.")},
        widget=forms.TextInput(attrs={"class": "field__input", "autocomplete": "off"}),
    )


@dataclass
class RowList:
    """One list on the page: a form for each saved row, with its key in its names, and the
    new rows. So a row someone else removed is simply not there to save (JOB-43), and a row
    someone else added after this page opened is left alone."""

    words: dict
    saved: list
    new: object

    @classmethod
    def of(cls, rows, form_class, new_rows, word, words, *, data=None, locked=False):
        saved = []
        for number, row in enumerate(rows, start=1):
            prefix = f"{word}-{row.pk}"
            sent = data is not None and f"{prefix}-text" in data
            form = form_class(
                data if sent else None,
                prefix=prefix,
                initial=row_values(row),
                empty_permitted=True,
                use_required_attribute=False,
            )
            form.key = row.pk
            label(form, words, number)
            saved.append(form)
        new = None if locked else new_rows(data, prefix=f"{word}s")
        if new is not None:
            for form in new:
                label(form, words)
        return cls(words=words, saved=saved, new=new)

    def blank(self):
        """The row a script copies when the open row is typed into (JOB-35)."""
        form = self.new.empty_form
        label(form, self.words)
        return form

    def is_valid(self):
        # Each is asked, so every row's errors show at once.
        checks = [form.is_valid() for form in self.saved if form.is_bound]
        return all(checks) and (self.new is None or self.new.is_valid())

    def saved_changes(self):
        """Each saved row this person changed: its key, and what changed."""
        return [
            (form.key, form.changes())
            for form in self.saved
            if form.is_bound and form.has_changed()
        ]

    def new_rows(self):
        """Each new row with words in it. A status alone is not typing (JOB-35)."""
        return [form.cleaned_data for form in self.new if form.cleaned_data.get("text")]

    def forms(self):
        return [*self.saved, *(self.new.forms if self.new is not None else [])]


def row_values(row):
    values = {"text": row.text}
    if hasattr(row, "status"):
        values["status"] = row.status
    return values


def label(form, words, number=None):
    """Every box of a list has a name for a screen reader (docs/DESIGN.md)."""
    for name, field in form.fields.items():
        field.widget.attrs["aria-label"] = (
            words[name] % {"number": number} if number else words[f"new_{name}"]
        )


CONCERN_WORDS = {
    "text": _("Concern %(number)d"),
    "status": _("Status of concern %(number)d"),
    "new_text": _("New concern"),
    "new_status": _("Status of the new concern"),
}
JOB_LINE_WORDS = {"text": _("Job %(number)d"), "new_text": _("New job")}


def initial_of(card):
    """What a saved card's boxes open with."""
    car = card.car
    customer = card.customer
    return {
        "plate": card.plate,
        "brand": car.car_model.brand.name,
        "car_model": car.car_model.name,
        "chassis_code": car.chassis_code,
        "vin": car.vin,
        "colour": car.colour,
        "colour_other": car.colour_other or OTHER_STARTS_AT,
        "mileage": card.mileage,
        "lead_mechanic": card.lead_mechanic_id,
        "admitted_date": card.admitted_date,
        "note": card.note,
        "customer_name": customer.name if customer else "",
        "contact_number": customer.contact_number if customer else "",
        "labour": card.labour,
    }


def initial_of_a_new_card():
    return {
        "admitted_date": timezone.localdate(),
        "colour": "",
        "colour_other": OTHER_STARTS_AT,
    }


def asks_what_it_names():
    """What makes a new card's plate box ask the server what the plate names, when the box
    is left (KNOWN-4, ADR-0016). A newer ask replaces an older one (KNOWN-5)."""
    return {
        "hx-get": reverse("jobs:known_plate"),
        "hx-trigger": "change",
        "hx-target": "#known-plate",
        "hx-swap": "innerHTML",
        "hx-sync": "this:replace",
    }


@dataclass
class CardForms:
    """Everything a job card's page holds: its boxes and its two lists."""

    main: JobCardForm
    concerns: RowList
    job_lines: RowList

    @classmethod
    def of(cls, user, workshop, branch, *, card=None, data=None):
        locked = card is not None and not card.is_open
        form_class = form_for(user)
        opening = initial_of(card) if card else initial_of_a_new_card()
        main = form_class(
            data,
            workshop=workshop,
            branch=branch,
            mechanic_key=card.lead_mechanic_id if card else None,
            # Only this form's boxes: what a role may not see never reaches its form.
            initial={box: value for box, value in opening.items() if box in form_class.base_fields},
        )
        if card is None:
            # Only a new card is filled from a known plate (KNOWN-4).
            main.fields["plate"].widget.attrs.update(asks_what_it_names())
        concerns = list(card.concerns.all()) if card else []
        lines = list(card.job_lines.all()) if card else []
        return cls(
            main=main,
            concerns=RowList.of(
                concerns,
                ConcernForm,
                NewConcerns,
                "concern",
                CONCERN_WORDS,
                data=data,
                locked=locked,
            ),
            job_lines=RowList.of(
                lines,
                JobLineForm,
                NewJobLines,
                "job_line",
                JOB_LINE_WORDS,
                data=data,
                locked=locked,
            ),
        )

    def is_valid(self):
        # Each is asked, so every error shows at once.
        checks = [self.main.is_valid(), self.concerns.is_valid(), self.job_lines.is_valid()]
        return all(checks)

    def refuse(self, refused):
        """Shows a service's refusal next to its box, or above the form when the box is not on
        this form."""
        if not hasattr(refused, "error_dict"):
            self.main.add_error(None, refused)
            return
        for name, errors in refused.error_dict.items():
            self.main.add_error(name if name in self.main.fields else None, errors)

    def refuse_row(self, refused):
        """Shows a refused row's error next to that row (JOB-37)."""
        for form in [*self.concerns.saved, *self.job_lines.saved]:
            if form.key == refused.key:
                form.add_error("text", refused.messages)

    def problems(self):
        """Everything that stopped this save, each named by what it holds (JOB-44)."""
        found = [
            (self.main[name].label, error)
            for name, errors in self.main.errors.items()
            if name in self.main.fields
            for error in errors
        ]
        found += [(_("Job card"), error) for error in self.main.non_field_errors()]
        for row_list, word in ((self.concerns, _("Concern")), (self.job_lines, _("Job"))):
            for form in row_list.forms():
                for error in form.non_field_errors():
                    found.append((word, error))
                for name, errors in form.errors.items():
                    if name in form.fields:
                        words = form["text"].value() or ""
                        for error in errors:
                            found.append((f"{word}, {words}" if words else word, error))
            if row_list.new is not None:
                found += [(word, error) for error in row_list.new.non_form_errors()]
        return found

"""Money: one column, and one box for typing an amount (ADR-0029)."""

import re
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.template.defaultfilters import floatformat
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

#: Every money column holds up to 9,99,99,99,999.99: v1's numeric(12, 2).
MAX_DIGITS = 12
DECIMAL_PLACES = 2
ONE_PAISA = Decimal("0.01")

#: What a person may type: digits, one point, and a minus so a negative gets its own words.
#: Python reads more than this, like "2_95" as 295 and "1e3" as 1000: the same slip as a comma.
#: Written so it never has to try again: a very long line of digits is refused at once.
TYPED_AMOUNT = re.compile(r"-?(\d+(\.\d*)?|\.\d+)")

TYPE_AN_AMOUNT = _("Type an amount.")
TOO_LONG = _("An amount has at most 10 digits before the point and 2 after.")

#: The column and the box say the same, so a service's full_clean() speaks like a form.
WORDS = {
    "invalid": _("Type the amount in numbers, like 2950.50, with no commas."),
    "max_digits": TOO_LONG,
    "max_whole_digits": TOO_LONG,
    "max_decimal_places": TOO_LONG,
}


def lowest_amount(*, allow_zero):
    """How low an amount may go, in words a person can act on."""
    if allow_zero:
        return MinValueValidator(Decimal("0"), _("An amount cannot be negative."))
    return MinValueValidator(ONE_PAISA, _("Type an amount above zero."))


def check_typed(text, field):
    """Refuses text that Python would read as a number and a person would not."""
    if not TYPED_AMOUNT.fullmatch(text):
        raise ValidationError(field.error_messages["invalid"], code="invalid")


class MoneyField(models.DecimalField):
    """A column of rupees and paise, the same size everywhere.

    MoneyField() is money that moved, like a payment: it must be above zero.
    MoneyField(allow_zero=True) is a charge, like labour: zero is fine.
    Nothing is ever negative.

    Each one also has its check in its model's Meta, so PostgreSQL refuses a wrong amount
    too, and tests/test_money.py finds one that is missing. The check is not built in
    here, because when a column changes Django never asks a field for its own check again:
    PostgreSQL would keep the old rule, with no error.
    """

    default_error_messages = {**WORDS, "null": TYPE_AN_AMOUNT, "blank": TYPE_AN_AMOUNT}

    def __init__(self, *args, allow_zero=False, **kwargs):
        self.allow_zero = allow_zero
        # Not forced: a migration keeps the size it was written with, so a later change of
        # size shows up as a new migration. tests/test_money.py checks the size on a model.
        kwargs.setdefault("max_digits", MAX_DIGITS)
        kwargs.setdefault("decimal_places", DECIMAL_PLACES)
        super().__init__(*args, **kwargs)

    @cached_property
    def validators(self):
        return [*super().validators, lowest_amount(allow_zero=self.allow_zero)]

    def to_python(self, value):
        # A programmer's mistake, not a person's, so it stops the work instead of showing
        # as a message on a form. It covers saving, full_clean() and queries.
        if isinstance(value, float | bool):
            raise TypeError(f"Money is a Decimal, never a {type(value).__name__}: {value!r}")
        if isinstance(value, str):
            check_typed(value.strip(), self)
        return super().to_python(value)

    def get_db_prep_save(self, value, connection):
        """Every save of a plain amount runs this column's rules, even with no full_clean().

        Without this, PostgreSQL rounds a third decimal with no error, so a service that
        forgot to check would change money and nobody would see it. What a person typed was
        checked long before this, so here it is a programmer's mistake: ValueError, which no
        page shows as a message on a form, and error tracking sees.

        An expression, like F("amount") * Decimal("1.18") or Value(...), goes straight to
        PostgreSQL. Its check guards zero and negative, but it would round a third decimal,
        so a calculation rounds on purpose before it saves.
        """
        if not hasattr(value, "as_sql"):
            try:
                self.run_validators(self.to_python(value))
            except ValidationError as refused:
                raise ValueError(f"{self.name}: {' '.join(refused.messages)}") from refused
        return super().get_db_prep_save(value, connection)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.allow_zero:
            kwargs["allow_zero"] = True
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                "form_class": MoneyFormField,
                "allow_zero": self.allow_zero,
                # On a column that cannot be empty, an empty box can only mean 0.
                "zero_is_empty": not self.null,
                **kwargs,
            }
        )


class MoneyFormField(forms.DecimalField):
    """The box for typing an amount: Django's decimal field, with no parser of our own.

    It is a text box, because a number box can change with the mouse wheel and hands the
    server an empty value for "2,950". A comma is refused, not removed, because a slip
    like "2,95" would become 295 on a bill.

    zero_is_empty is for a column that cannot be empty. If its box may be left empty, like
    labour's, empty means 0. Anywhere else, empty means not filled yet and 0 means free, so
    a saved 0 stays on show (v1's lesson: a free part came back as "no cost recorded").
    """

    widget = forms.TextInput(attrs={"inputmode": "decimal"})
    default_error_messages = {**WORDS, "required": TYPE_AN_AMOUNT}

    def __init__(self, *, allow_zero=False, zero_is_empty=False, **kwargs):
        self.zero_is_empty = zero_is_empty
        # One size, always: clean() relies on it to round nothing.
        kwargs["max_digits"] = MAX_DIGITS
        kwargs["decimal_places"] = DECIMAL_PLACES
        super().__init__(**kwargs)
        self.validators.append(lowest_amount(allow_zero=allow_zero))

    @property
    def _empty_means_zero(self):
        # Read each time, because a role's form may make the box required.
        return self.zero_is_empty and not self.required

    def to_python(self, value):
        if not isinstance(value, str):
            return super().to_python(value)
        typed = value.strip()
        if not typed:
            return Decimal("0") if self._empty_means_zero else None
        check_typed(typed, self)
        return super().to_python(typed)

    def clean(self, value):
        """The amount, always with two decimals, like a saved one.

        None is a box never sent, and "" is a box left empty. A service gets only this
        answer, so it could not tell them apart, and a saved amount would be wiped (v1's
        lesson). So a box never sent refuses the whole form: a form holds only what its role
        may change (ROLE-13), and a form like that always sends its boxes.
        """
        if value is None and not self.disabled:
            raise ValidationError(self.error_messages["required"], code="required")
        amount = super().clean(value)
        # The checks let no third decimal through, so this rounds nothing. And + 0 makes -0
        # a plain 0.
        return None if amount is None else (amount + 0).quantize(ONE_PAISA)

    def has_changed(self, initial, data):
        # Where empty means 0, an empty box and a 0 are one answer, saved or typed.
        return super().has_changed(
            (initial or Decimal("0")) if self._empty_means_zero else initial, data
        )

    def prepare_value(self, value):
        """A saved amount, ready to type over: 8500.00 shows as 8500, and 1250.50 stays.

        What a person typed arrives as text and stays exactly as it was, so a refused
        amount comes back to be fixed (v1's _tidy_money_initial).
        """
        if not isinstance(value, Decimal | int):
            return value
        if self._empty_means_zero and not value:
            return ""
        return floatformat(value, "-2u")

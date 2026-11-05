"""Every money column has the one size and its check, and every box is right (ADR-0029)."""

from decimal import Decimal

import pytest
from django import forms
from django.db import models
from django.test.utils import isolate_apps
from test_queries import form_classes

from apps.core.models import BaseModel
from apps.core.money import DECIMAL_PLACES, MAX_DIGITS, MoneyField, MoneyFormField

A_NUMBER_BOX = "a number box: use a text box with inputmode (CONTRIBUTING.md)"
NOT_MONEY_BOX = "a decimal box that is not a MoneyFormField, so it reads 2_95 as 295"
A_FLOAT = "a float column: money is a Decimal, and a float cannot hold paise exactly"
NOT_MONEY_FIELD = (
    "not a MoneyField. A decimal column that is not money, like a quantity, gets a short "
    "list in this test, with why"
)
NOT_THE_SIZE = "not the one size: leave out max_digits and decimal_places"
REFUSES_EMPTY = (
    "its box may be left empty, which means 0, and this column refuses 0: "
    "add allow_zero=True, or null=True"
)
ABOVE_ZERO_CHECK = (
    "add to its Meta: models.CheckConstraint(condition=models.Q(amount__gt=0), name=...)"
)
NOT_NEGATIVE_CHECK = (
    "add to its Meta: models.CheckConstraint(condition=models.Q(amount__gte=0), name=...)"
)


def money_problems(model):
    """What is wrong with a model's number columns, by column. Empty when all is right."""
    return {
        field.name: problem
        for field in model._meta.concrete_fields
        if (problem := column_problem(field))
    }


def column_problem(field):
    """What is wrong with one column, or None when it is right."""
    column = field.output_field if isinstance(field, models.GeneratedField) else field
    if isinstance(column, models.FloatField):
        return A_FLOAT
    if not isinstance(column, models.DecimalField):
        return None
    if not isinstance(column, MoneyField):
        return NOT_MONEY_FIELD
    if (column.max_digits, column.decimal_places) != (MAX_DIGITS, DECIMAL_PLACES):
        return NOT_THE_SIZE
    if column.blank and not column.null and not column.allow_zero:
        return REFUSES_EMPTY
    return check_problem(field, column.allow_zero)


def check_problem(field, allow_zero):
    """A money column's check in Meta must match its kind, so PostgreSQL has the same rule."""
    lookup = f"{field.name}__{'gte' if allow_zero else 'gt'}"
    checks = [
        constraint.condition
        for constraint in field.model._meta.constraints
        if isinstance(constraint, models.CheckConstraint)
    ]
    if models.Q(**{lookup: 0}) in checks:
        return None
    return f"add to its Meta: models.CheckConstraint(condition=models.Q({lookup}=0), name=...)"


def test_every_money_column_in_our_apps_has_its_size_and_its_check(our_models):
    problems = {model._meta.label: money_problems(model) for model in our_models}

    assert {label: found for label, found in problems.items() if found} == {}


def planted_with(column, condition=None):
    """A model with this column and at most one check, with no table behind it."""

    class Planted(BaseModel):
        amount = column

        class Meta:
            app_label = "core"
            constraints = (
                [models.CheckConstraint(condition=condition, name="planted_check")]
                if condition
                else []
            )

    return Planted


def generated(output_field):
    return models.GeneratedField(
        expression=models.F("id"), output_field=output_field, db_persist=True
    )


@isolate_apps("apps.core")
@pytest.mark.parametrize(
    ("column", "condition", "problem"),
    [
        pytest.param(MoneyField(), None, ABOVE_ZERO_CHECK, id="no check"),
        pytest.param(
            MoneyField(allow_zero=True), None, NOT_NEGATIVE_CHECK, id="a charge, no check"
        ),
        pytest.param(
            MoneyField(),
            models.Q(amount__gte=0),
            ABOVE_ZERO_CHECK,
            id="the check lets zero in, the column does not",
        ),
        pytest.param(
            MoneyField(allow_zero=True),
            models.Q(amount__gt=0),
            NOT_NEGATIVE_CHECK,
            id="the check refuses zero, the column does not",
        ),
        pytest.param(
            MoneyField(allow_zero=True),
            models.Q(other__gte=0),
            NOT_NEGATIVE_CHECK,
            id="the check is about another column",
        ),
        pytest.param(
            MoneyField(max_digits=10),
            models.Q(amount__gt=0),
            NOT_THE_SIZE,
            id="another size",
        ),
        pytest.param(
            MoneyField(blank=True, default=Decimal("0")),
            models.Q(amount__gt=0),
            REFUSES_EMPTY,
            id="an empty box means 0, and the column refuses 0",
        ),
        pytest.param(
            models.DecimalField(max_digits=12, decimal_places=2),
            None,
            NOT_MONEY_FIELD,
            id="a plain decimal column",
        ),
        pytest.param(models.FloatField(), None, A_FLOAT, id="a float column"),
        pytest.param(generated(models.FloatField()), None, A_FLOAT, id="a generated float column"),
        pytest.param(
            generated(models.DecimalField(max_digits=20, decimal_places=4)),
            None,
            NOT_MONEY_FIELD,
            id="a generated plain decimal column",
        ),
        pytest.param(generated(MoneyField()), None, ABOVE_ZERO_CHECK, id="generated, no check"),
    ],
)
def test_a_wrong_column_is_caught(column, condition, problem):
    assert money_problems(planted_with(column, condition)) == {"amount": problem}


@isolate_apps("apps.core")
@pytest.mark.parametrize(
    ("column", "condition"),
    [
        pytest.param(MoneyField(), models.Q(amount__gt=0), id="money that moved"),
        pytest.param(MoneyField(allow_zero=True), models.Q(amount__gte=0), id="a charge"),
        pytest.param(
            MoneyField(allow_zero=True, blank=True, default=Decimal("0")),
            models.Q(amount__gte=0),
            id="a charge whose box may be left empty",
        ),
        pytest.param(
            MoneyField(allow_zero=True, null=True, blank=True),
            models.Q(amount__gte=0),
            id="a price that may be empty",
        ),
        pytest.param(
            MoneyField(null=True, blank=True),
            models.Q(amount__gt=0),
            id="money that moved, not filled yet",
        ),
        pytest.param(
            MoneyField(allow_zero=True),
            models.Q(amount__gte=Decimal("0")),
            id="a check written with a Decimal",
        ),
        pytest.param(generated(MoneyField()), models.Q(amount__gt=0), id="generated, with a check"),
        pytest.param(models.IntegerField(), None, id="a whole number is not money"),
    ],
)
def test_a_right_column_passes(column, condition):
    assert money_problems(planted_with(column, condition)) == {}


def box_problem(field):
    """What is wrong with one field on a form, or None when it is right."""
    if isinstance(field.widget, forms.NumberInput):
        return A_NUMBER_BOX
    if isinstance(field, forms.DecimalField) and not isinstance(field, MoneyFormField):
        return NOT_MONEY_BOX
    return None


def test_every_box_for_a_number_on_a_form_is_right():
    found_forms = form_classes()
    # A floor, so a search that found nothing cannot pass for being clean.
    assert found_forms

    problems = {
        f"{form.__name__}.{name}": problem
        for form in found_forms
        for name, field in form.base_fields.items()
        if (problem := box_problem(field))
    }

    assert problems == {}


@pytest.mark.parametrize(
    ("box", "problem"),
    [
        pytest.param(forms.DecimalField(), A_NUMBER_BOX, id="Django's decimal box"),
        pytest.param(forms.IntegerField(), A_NUMBER_BOX, id="Django's whole number box"),
        pytest.param(
            forms.DecimalField(widget=forms.TextInput),
            NOT_MONEY_BOX,
            id="a decimal text box that is not the money box",
        ),
    ],
)
def test_a_wrong_box_is_caught(box, problem):
    assert box_problem(box) == problem


@pytest.mark.parametrize(
    "box",
    [
        pytest.param(MoneyFormField(), id="the money box"),
        pytest.param(
            forms.IntegerField(widget=forms.TextInput(attrs={"inputmode": "numeric"})),
            id="a whole number in a text box",
        ),
        pytest.param(forms.CharField(), id="a box for words"),
    ],
)
def test_a_right_box_passes(box):
    assert box_problem(box) is None

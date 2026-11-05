"""One column and one box for every amount (apps/core/money.py, ADR-0029)."""

import time
from decimal import Decimal

import pytest
from django import forms
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, models, transaction
from django.db.models import F, Sum
from django.test.utils import isolate_apps

from apps.core.models import BaseModel
from apps.core.money import MoneyField, MoneyFormField

ABOVE_ZERO = "Type an amount above zero."
NOT_NEGATIVE = "An amount cannot be negative."
IN_NUMBERS = "Type the amount in numbers, like 2950.50, with no commas."
TOO_LONG = "An amount has at most 10 digits before the point and 2 after."
TYPE_AN_AMOUNT = "Type an amount."


@pytest.fixture
def planted(db):
    """A table with each kind of money column, each with the check a real one has.

    It is made inside the test's own transaction, so it is gone when the test ends.
    tests/test_money.py covers every real column by itself.
    """
    with isolate_apps("apps.core"):

        class Planted(BaseModel):
            # Money that moved, like a payment.
            paid = MoneyField()
            # A charge, like labour: an empty box means 0.
            charge = MoneyField(allow_zero=True, blank=True, default=Decimal("0"))
            # A price, like a part's: empty means not priced yet, and 0 means free.
            price = MoneyField(allow_zero=True, null=True, blank=True)

            class Meta:
                app_label = "core"
                constraints = [
                    models.CheckConstraint(
                        condition=models.Q(paid__gt=0), name="core_planted_paid_above_zero"
                    ),
                    models.CheckConstraint(
                        condition=models.Q(charge__gte=0), name="core_planted_charge_not_negative"
                    ),
                    models.CheckConstraint(
                        condition=models.Q(price__gte=0), name="core_planted_price_not_negative"
                    ),
                ]

        with connection.schema_editor() as editor:
            editor.create_model(Planted)
        yield Planted


# The column.


def test_a_money_column_has_one_size():
    field = MoneyField()

    assert (field.max_digits, field.decimal_places) == (12, 2)


def test_the_stricter_kind_is_the_default():
    assert MoneyField().allow_zero is False


def test_a_migration_carries_the_size_and_the_kind():
    name, path, args, kwargs = MoneyField(allow_zero=True).deconstruct()

    assert path == "apps.core.money.MoneyField"
    assert kwargs == {"max_digits": 12, "decimal_places": 2, "allow_zero": True}
    assert MoneyField(*args, **kwargs).allow_zero is True


def test_a_migration_of_the_default_kind_says_nothing_about_it():
    assert "allow_zero" not in MoneyField().deconstruct()[3]


def test_an_old_migration_keeps_the_size_it_was_written_with():
    # Or a later change of size would show up as no change at all.
    assert MoneyField(max_digits=10).deconstruct()[3]["max_digits"] == 10


@pytest.mark.parametrize(
    ("column", "amount", "words"),
    [
        pytest.param("paid", Decimal("0"), ABOVE_ZERO, id="money that moved: zero"),
        pytest.param("paid", Decimal("-1"), ABOVE_ZERO, id="money that moved: negative"),
        pytest.param("charge", Decimal("-1"), NOT_NEGATIVE, id="a charge: negative"),
        pytest.param("price", Decimal("-1"), NOT_NEGATIVE, id="a price: negative"),
        pytest.param("paid", Decimal("2950.555"), TOO_LONG, id="a third decimal"),
        pytest.param("paid", Decimal("10000000000"), TOO_LONG, id="too big"),
        pytest.param("paid", "abc", IN_NUMBERS, id="not a number"),
        pytest.param("paid", "2_95", IN_NUMBERS, id="text Python reads as 295"),
        pytest.param("paid", "1e3", IN_NUMBERS, id="text Python reads as 1000"),
        pytest.param("paid", None, TYPE_AN_AMOUNT, id="nothing, on a column that needs it"),
    ],
)
def test_full_clean_refuses_a_wrong_amount_in_plain_words(planted, column, amount, words):
    record = planted(**{"paid": Decimal("1"), column: amount})

    with pytest.raises(ValidationError) as refused:
        record.full_clean()

    assert refused.value.message_dict == {column: [words]}


@pytest.mark.parametrize(
    ("column", "amount"),
    [
        pytest.param("paid", Decimal("0.01"), id="money that moved: the lowest"),
        pytest.param("paid", Decimal("9999999999.99"), id="money that moved: the biggest"),
        pytest.param("charge", Decimal("0"), id="a charge: zero"),
        pytest.param("price", Decimal("0"), id="a price: zero means free"),
        pytest.param("price", None, id="a price: empty means not priced yet"),
    ],
)
def test_full_clean_takes_a_right_amount(planted, column, amount):
    planted(**{"paid": Decimal("1"), column: amount}).full_clean()


def test_an_amount_reads_back_with_its_two_decimals(planted):
    record = planted.objects.create(paid=Decimal("10.5"))

    record.refresh_from_db()

    assert str(record.paid) == "10.50"


def test_the_biggest_amount_is_saved(planted):
    record = planted.objects.create(paid=Decimal("9999999999.99"))

    record.refresh_from_db()

    assert record.paid == Decimal("9999999999.99")


# Every save of a plain amount, with no full_clean().


def by_save(model, amount):
    model(paid=amount).save()


def by_bulk_create(model, amount):
    model.objects.bulk_create([model(paid=amount)])


def by_update(model, amount):
    record = model.objects.create(paid=Decimal("1"))
    model.objects.filter(pk=record.pk).update(paid=amount)


def by_bulk_update(model, amount):
    record = model.objects.create(paid=Decimal("1"))
    record.paid = amount
    model.objects.bulk_update([record], ["paid"])


EVERY_WAY_TO_SAVE = [by_save, by_bulk_create, by_update, by_bulk_update]


@pytest.mark.parametrize(
    "amount",
    [
        pytest.param(Decimal("2950.555"), id="a third decimal: PostgreSQL would round it"),
        pytest.param(Decimal("10000000000"), id="too big"),
        pytest.param(Decimal("0"), id="zero"),
        pytest.param(Decimal("-1"), id="negative"),
        pytest.param(Decimal("NaN"), id="NaN: PostgreSQL calls it above zero"),
        pytest.param(Decimal("Infinity"), id="Infinity"),
        pytest.param("2950.555", id="a third decimal, as text"),
        pytest.param("abc", id="not a number"),
        pytest.param("2_95", id="text Python reads as 295"),
        pytest.param("0e99999999999", id="a zero PostgreSQL cannot read"),
    ],
)
def test_a_save_refuses_a_wrong_amount_and_names_its_column(planted, amount):
    # ValueError, not ValidationError: a page must never show this as a message on a form,
    # and it stops before PostgreSQL could round it. A refused save marks the transaction,
    # so this try has its own.
    with pytest.raises(ValueError, match="paid"), transaction.atomic():
        by_save(planted, amount)


@pytest.mark.parametrize("save", EVERY_WAY_TO_SAVE)
def test_every_way_to_save_refuses_a_third_decimal(planted, save):
    with pytest.raises(ValueError, match="paid"), transaction.atomic():
        save(planted, Decimal("2950.555"))


@pytest.mark.parametrize("save", EVERY_WAY_TO_SAVE)
def test_every_way_to_save_refuses_a_float(planted, save):
    with pytest.raises(TypeError, match="never a float"), transaction.atomic():
        save(planted, 2950.5)


@pytest.mark.parametrize("save", EVERY_WAY_TO_SAVE)
def test_every_way_to_save_takes_a_right_amount(planted, save):
    save(planted, Decimal("2950.50"))

    assert planted.objects.filter(paid=Decimal("2950.50")).count() == 1


def test_a_save_refuses_a_bool(planted):
    with pytest.raises(TypeError, match="never a bool"), transaction.atomic():
        by_save(planted, True)


def test_a_text_or_a_whole_number_is_saved_exactly(planted):
    by_text = planted.objects.create(paid="2950.50")
    by_number = planted.objects.create(paid=2950)

    by_text.refresh_from_db()
    by_number.refresh_from_db()

    assert (by_text.paid, by_number.paid) == (Decimal("2950.50"), Decimal("2950.00"))


def test_full_clean_refuses_a_float(planted):
    with pytest.raises(TypeError, match="never a float"):
        planted(paid=2950.5).full_clean()


def test_a_query_refuses_a_float(planted):
    with pytest.raises(TypeError, match="never a float"):
        planted.objects.filter(paid__gt=2950.5).exists()


def test_a_query_is_not_a_save_so_any_amount_can_be_compared(planted):
    planted.objects.create(paid=Decimal("1"))

    assert planted.objects.filter(paid__gt=0, paid__lt=Decimal("1.001")).exists()


def test_an_empty_price_is_saved_empty(planted):
    record = planted.objects.create(paid=Decimal("1"), price=None)

    record.refresh_from_db()

    assert record.price is None


def test_an_expression_is_left_to_postgresql(planted):
    record = planted.objects.create(paid=Decimal("1"))

    planted.objects.filter(pk=record.pk).update(paid=F("paid") + Decimal("1.50"))
    record.refresh_from_db()

    assert record.paid == Decimal("2.50")


@pytest.mark.parametrize(
    ("column", "too_low"),
    [
        pytest.param("paid", F("paid") - Decimal("1"), id="money that moved: to zero"),
        pytest.param("paid", F("paid") - Decimal("2"), id="money that moved: below zero"),
        pytest.param("charge", F("charge") - Decimal("1"), id="a charge: below zero"),
        pytest.param("price", F("paid") - Decimal("2"), id="a price: below zero"),
    ],
)
def test_postgresql_refuses_an_expression_that_goes_too_low(planted, column, too_low):
    # An expression steps around the save's rules, so only the check in Meta can stop this.
    record = planted.objects.create(paid=Decimal("1"))

    with pytest.raises(IntegrityError), transaction.atomic():
        planted.objects.filter(pk=record.pk).update(**{column: too_low})


def test_totals_stay_decimal_and_add_up_from_their_rows(planted):
    planted.objects.create(paid=Decimal("10.50"), charge=Decimal("2.25"))
    planted.objects.create(paid=Decimal("5.25"), charge=Decimal("1.00"))

    total = planted.objects.aggregate(total=Sum("paid", default=Decimal("0")))["total"]
    net = planted.objects.annotate(net=F("paid") - F("charge")).order_by("net").first().net

    assert (total, net) == (Decimal("15.75"), Decimal("4.25"))
    assert isinstance(total, Decimal)
    assert isinstance(net, Decimal)


# The box.


@pytest.mark.parametrize(
    ("typed", "amount"),
    [
        ("2950", "2950.00"),
        ("2950.5", "2950.50"),
        ("2950.50", "2950.50"),
        ("2950.", "2950.00"),
        (".50", "0.50"),
        ("  2950  ", "2950.00"),
        ("0.01", "0.01"),
        ("9999999999.99", "9999999999.99"),
    ],
)
def test_the_box_takes_an_amount_with_two_decimals_like_a_saved_one(typed, amount):
    assert str(MoneyFormField().clean(typed)) == amount


@pytest.mark.parametrize(
    ("typed", "words"),
    [
        pytest.param("2,950", IN_NUMBERS, id="a comma: 2,95 would become 295 on a bill"),
        pytest.param("1,50,000", IN_NUMBERS, id="Indian commas"),
        pytest.param("2_95", IN_NUMBERS, id="an underscore: Python reads it as 295"),
        pytest.param("1_50_000", IN_NUMBERS, id="underscores"),
        pytest.param("1e3", IN_NUMBERS, id="a power of ten: Python reads it as 1000"),
        pytest.param("1.23E+06", IN_NUMBERS, id="as Excel pastes a big number"),
        pytest.param("0e99999999999", IN_NUMBERS, id="a zero PostgreSQL cannot read"),
        pytest.param("abc", IN_NUMBERS, id="letters"),
        pytest.param("+500", IN_NUMBERS, id="a plus"),
        pytest.param("500 rupees", IN_NUMBERS, id="a word after it"),
        pytest.param("1.2.3", IN_NUMBERS, id="two points"),
        pytest.param(".", IN_NUMBERS, id="only a point"),
        pytest.param("-", IN_NUMBERS, id="only a minus"),
        pytest.param("NaN", IN_NUMBERS, id="NaN"),
        pytest.param("sNaN", IN_NUMBERS, id="the NaN that crashes a comparison"),
        pytest.param("Infinity", IN_NUMBERS, id="Infinity"),
        pytest.param("2950.555", TOO_LONG, id="a third decimal is refused, never rounded"),
        pytest.param("2950.3333333333", TOO_LONG, id="from a calculator"),
        pytest.param("10000000000", TOO_LONG, id="too big, before the point"),
        pytest.param("99999999999.99", TOO_LONG, id="too big, in all"),
        pytest.param("0", ABOVE_ZERO, id="zero"),
        pytest.param("0.00", ABOVE_ZERO, id="zero with its paise"),
        pytest.param("-1", ABOVE_ZERO, id="negative"),
    ],
)
def test_the_box_refuses_in_plain_words(typed, words):
    with pytest.raises(ValidationError) as refused:
        MoneyFormField().clean(typed)

    assert refused.value.messages == [words]


@pytest.mark.parametrize(
    ("typed", "amount"),
    [("0", "0.00"), ("0.00", "0.00"), ("-0", "0.00"), ("500", "500.00")],
)
def test_the_box_of_a_charge_takes_zero(typed, amount):
    assert str(MoneyFormField(allow_zero=True).clean(typed)) == amount


def test_a_very_long_line_of_digits_is_refused_at_once():
    # An older pattern took about 10 seconds on this, so one person could freeze a worker.
    started = time.perf_counter()

    with pytest.raises(ValidationError) as refused:
        MoneyFormField().clean("1" * 40000 + "x")

    assert refused.value.messages == [IN_NUMBERS]
    assert time.perf_counter() - started < 1


def test_a_box_has_the_one_size_whatever_it_is_given():
    # Or clean() would round a third decimal.
    with pytest.raises(ValidationError) as refused:
        MoneyFormField(decimal_places=3).clean("1.235")

    assert refused.value.messages == [TOO_LONG]


def test_the_box_of_a_charge_refuses_negative():
    with pytest.raises(ValidationError) as refused:
        MoneyFormField(allow_zero=True).clean("-1")

    assert refused.value.messages == [NOT_NEGATIVE]


@pytest.mark.parametrize("typed", ["", "   "])
def test_the_box_must_be_filled_when_the_column_needs_it(typed):
    with pytest.raises(ValidationError) as refused:
        MoneyFormField().clean(typed)

    assert refused.value.messages == [TYPE_AN_AMOUNT]


@pytest.mark.parametrize("typed", ["", "   "])
def test_a_box_where_empty_means_zero_gives_zero(typed):
    box = MoneyFormField(allow_zero=True, zero_is_empty=True, required=False)

    assert str(box.clean(typed)) == "0.00"


def test_a_role_that_needs_the_box_filled_wins_over_empty_means_zero():
    box = MoneyField(allow_zero=True, blank=True, default=Decimal("0")).formfield()
    box.required = True

    with pytest.raises(ValidationError) as refused:
        box.clean("")

    assert refused.value.messages == [TYPE_AN_AMOUNT]
    assert box.prepare_value(Decimal("0.00")) == "0"


def test_empty_means_zero_cannot_get_past_a_column_that_refuses_zero():
    box = MoneyFormField(zero_is_empty=True, required=False)

    with pytest.raises(ValidationError) as refused:
        box.clean("")

    assert refused.value.messages == [ABOVE_ZERO]


def test_a_box_where_empty_means_not_filled_yet_stays_empty():
    assert MoneyFormField(allow_zero=True, required=False).clean("") is None


def test_a_charge_that_must_be_typed_keeps_its_0_on_show():
    # Its box cannot be left empty, so showing it empty would only make someone type 0 again.
    box = MoneyField(allow_zero=True).formfield()

    assert box.prepare_value(Decimal("0.00")) == "0"


@pytest.mark.parametrize(
    "box",
    [
        pytest.param(MoneyFormField(), id="money that moved"),
        pytest.param(
            MoneyFormField(allow_zero=True, zero_is_empty=True, required=False), id="a charge"
        ),
        pytest.param(MoneyFormField(allow_zero=True, required=False), id="a price"),
    ],
)
def test_a_box_never_sent_is_refused_on_every_kind(box):
    # A service gets only the answer, so it could not tell this from a box left empty.
    with pytest.raises(ValidationError) as refused:
        box.clean(None)

    assert refused.value.messages == [TYPE_AN_AMOUNT]


@pytest.mark.parametrize(
    ("zero_is_empty", "initial", "typed", "changed"),
    [
        pytest.param(True, None, "", False, id="a charge: a blank row is untouched"),
        pytest.param(True, Decimal("0.00"), "", False, id="a charge: a saved 0 shows empty"),
        pytest.param(True, Decimal("0.00"), "0", False, id="a charge: 0 typed over a saved 0"),
        pytest.param(True, None, "0", False, id="a charge: 0 typed on a blank row"),
        pytest.param(True, Decimal("500.00"), "500", False, id="a charge: the same amount"),
        pytest.param(True, Decimal("500.00"), "", True, id="a charge: cleared"),
        pytest.param(True, None, "500", True, id="a charge: typed"),
        pytest.param(False, None, "", False, id="a price: a blank row is untouched"),
        pytest.param(False, None, "0", True, id="a price: 0 is an answer"),
        pytest.param(False, Decimal("0.00"), "0", False, id="a price: the same 0"),
        pytest.param(False, Decimal("0.00"), "", True, id="a price: a free part is cleared"),
    ],
)
def test_the_box_knows_when_it_changed(zero_is_empty, initial, typed, changed):
    box = MoneyFormField(allow_zero=True, zero_is_empty=zero_is_empty, required=False)

    assert box.has_changed(initial, typed) is changed


@pytest.mark.parametrize(
    ("saved", "zero_is_empty", "shown"),
    [
        pytest.param(Decimal("8500.00"), True, "8500", id="no zeros to delete before typing"),
        pytest.param(Decimal("8500"), True, "8500", id="a whole number"),
        pytest.param(8500, True, "8500", id="a plain number"),
        pytest.param(Decimal("1250.50"), True, "1250.50", id="paise are kept"),
        pytest.param(Decimal("1250.5"), True, "1250.50", id="paise have two digits"),
        pytest.param(Decimal("0.50"), True, "0.50", id="under a rupee"),
        pytest.param(Decimal("100.00"), True, "100", id="zeros before the point stay"),
        pytest.param(Decimal("150000.00"), True, "150000", id="no commas in a box"),
        pytest.param(Decimal("0.00"), True, "", id="a charge of 0 shows empty"),
        pytest.param(0, True, "", id="a default of 0 shows empty"),
        pytest.param(Decimal("0.00"), False, "0", id="a free part stays 0"),
        pytest.param(None, True, None, id="nothing saved yet"),
        pytest.param(None, False, None, id="not priced yet"),
    ],
)
def test_a_saved_amount_shows_ready_to_type_over(saved, zero_is_empty, shown):
    box = MoneyFormField(zero_is_empty=zero_is_empty, required=False)

    assert box.prepare_value(saved) == shown


class AmountForm(forms.Form):
    amount = MoneyFormField()


def test_a_form_opens_with_the_amount_ready_to_type_over():
    assert AmountForm(initial={"amount": Decimal("8500.00")})["amount"].value() == "8500"


@pytest.mark.parametrize("typed", ["2,950", "2950.00", "abc"])
def test_what_a_person_typed_comes_back_as_it_was_typed(typed):
    assert AmountForm({"amount": typed})["amount"].value() == typed


def test_a_nan_that_crashes_a_comparison_only_counts_as_a_change():
    form = AmountForm({"amount": "sNaN"}, initial={"amount": Decimal("500")})

    assert form.changed_data == ["amount"]
    assert not form.is_valid()


def test_the_box_is_a_text_box_for_a_number_keypad():
    html = str(AmountForm()["amount"])

    assert 'type="text"' in html
    assert 'inputmode="decimal"' in html
    assert "step=" not in html
    assert "min=" not in html


# The column and the box together.


@pytest.fixture
def planted_form(planted):
    return forms.modelform_factory(planted, fields=["paid", "charge", "price"])


def test_a_form_saves_what_was_typed(planted_form):
    form = planted_form({"paid": "2950.50", "charge": "500", "price": "0"})

    record = form.save()
    record.refresh_from_db()

    assert (record.paid, record.charge, record.price) == (
        Decimal("2950.50"),
        Decimal("500.00"),
        Decimal("0.00"),
    )


def test_a_form_with_empty_boxes_saves_a_charge_of_zero_and_no_price(planted_form):
    record = planted_form({"paid": "1", "charge": "", "price": ""}).save()
    record.refresh_from_db()

    assert (record.charge, record.price) == (Decimal("0.00"), None)


def test_boxes_cleared_on_a_saved_record_make_a_charge_zero_and_a_price_empty(
    planted, planted_form
):
    saved = planted.objects.create(paid=Decimal("1"), charge=Decimal("500"), price=Decimal("750"))

    record = planted_form({"paid": "1", "charge": "", "price": ""}, instance=saved).save()
    record.refresh_from_db()

    assert (record.charge, record.price) == (Decimal("0.00"), None)


@pytest.mark.parametrize("column", ["paid", "charge", "price"])
def test_a_form_that_never_sent_a_box_is_refused(planted, planted_form, column):
    # v1's lesson: a box not sent is not a box left empty, and mixing them destroys money.
    saved = planted.objects.create(paid=Decimal("1"), charge=Decimal("500"), price=Decimal("750"))
    sent = {"paid": "2", "charge": "2", "price": "2"}
    del sent[column]

    assert planted_form(sent, instance=saved).errors == {column: [TYPE_AN_AMOUNT]}


@pytest.mark.parametrize("price", [Decimal("750.00"), None])
def test_a_disabled_box_is_not_sent_and_keeps_its_saved_amount(planted, planted_form, price):
    saved = planted.objects.create(paid=Decimal("1"), price=price)
    form = planted_form({"paid": "2", "charge": ""}, instance=saved)
    form.fields["price"].disabled = True

    record = form.save()
    record.refresh_from_db()

    assert (record.paid, record.price) == (Decimal("2.00"), price)


@pytest.mark.parametrize(
    ("column", "typed", "words"),
    [
        ("paid", "0", ABOVE_ZERO),
        ("paid", "", TYPE_AN_AMOUNT),
        ("paid", "2,950", IN_NUMBERS),
        ("paid", "2_95", IN_NUMBERS),
        ("charge", "-1", NOT_NEGATIVE),
        ("price", "-1", NOT_NEGATIVE),
    ],
)
def test_a_wrong_amount_is_refused_on_its_own_box(planted_form, column, typed, words):
    form = planted_form({"paid": "1", "charge": "", "price": "", column: typed})

    assert not form.is_valid()
    assert form.errors == {column: [words]}


def test_a_saved_record_opens_with_each_box_ready_to_type_over(planted, planted_form):
    saved = planted.objects.create(paid=Decimal("8500"), charge=Decimal("0"), price=Decimal("0"))
    saved.refresh_from_db()
    form = planted_form(instance=saved)

    assert form["paid"].value() == "8500"
    assert form["charge"].value() == ""
    assert form["price"].value() == "0"


def test_a_new_form_opens_with_empty_boxes(planted_form):
    form = planted_form()

    assert form["paid"].value() is None
    assert form["charge"].value() == ""
    assert form["price"].value() is None


def test_a_new_form_sent_with_a_blank_charge_counts_it_as_untouched(planted_form):
    assert "charge" not in planted_form({"paid": "1", "charge": "", "price": ""}).changed_data

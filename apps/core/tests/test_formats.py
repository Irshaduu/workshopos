"""Indian dates and numbers on every screen (apps/core/formats/en/formats.py).

Each style here is a line of docs/DESIGN.md, with v1's reason for it.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django import forms
from django.conf import settings
from django.template import engines
from django.utils.formats import get_format

WHOLE_RUPEES = '{{ value|floatformat:"0g" }}'
PAISE_WHEN_ANY = '{{ value|floatformat:"-2g" }}'
PAISE_ALWAYS = '{{ value|floatformat:"2g" }}'

INDIA = ZoneInfo("Asia/Kolkata")
# 3:05 in the afternoon in India.
MOMENT = datetime(2026, 10, 3, 9, 35, tzinfo=UTC)
A_DAY = date(2026, 10, 3)
TYPED_DAY = date(2026, 11, 10)


def shown(template, value):
    return engines["django"].from_string(template).render({"value": value})


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        ("0", "0"),
        ("999", "999"),
        ("1000", "1,000"),
        ("150000", "1,50,000"),
        ("4523678", "45,23,678"),
        ("45236789.25", "4,52,36,789"),
        ("-150000", "-1,50,000"),
    ],
)
def test_whole_rupees_are_grouped_the_indian_way(amount, expected):
    assert shown(WHOLE_RUPEES, Decimal(amount)) == expected


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        ("2.50", "3"),
        ("3.50", "4"),
        ("499.50", "500"),
        ("500.50", "501"),
        ("-150000.50", "-1,50,001"),
    ],
)
def test_half_a_rupee_rounds_up_unlike_v1_which_went_to_the_even_rupee(amount, expected):
    assert shown(WHOLE_RUPEES, Decimal(amount)) == expected


def test_a_small_minus_amount_never_shows_as_minus_zero():
    assert shown(WHOLE_RUPEES, Decimal("-0.40")) == "0"


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        ("1200", "1,200"),
        ("1200.00", "1,200"),
        ("499.50", "499.50"),
        ("150000.50", "1,50,000.50"),
        ("-150000.50", "-1,50,000.50"),
    ],
)
def test_a_list_row_shows_paise_only_when_there_are_any(amount, expected):
    assert shown(PAISE_WHEN_ANY, Decimal(amount)) == expected


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        ("17800", "17,800.00"),
        ("1919.5", "1,919.50"),
        ("-1200", "-1,200.00"),
        # The biggest amount a money column holds.
        ("9999999999.99", "9,99,99,99,999.99"),
    ],
)
def test_a_printed_bill_always_shows_paise(amount, expected):
    assert shown(PAISE_ALWAYS, Decimal(amount)) == expected


@pytest.mark.parametrize("style", [WHOLE_RUPEES, PAISE_WHEN_ANY, PAISE_ALWAYS])
def test_an_empty_amount_shows_nothing_not_none_or_zero(style):
    assert shown(style, None) == ""


@pytest.mark.parametrize("value", [150000, 2026])
def test_a_number_with_no_filter_stays_plain_so_a_year_is_never_split(value):
    assert shown("{{ value }}", value) == str(value)


@pytest.mark.parametrize(
    ("template", "value", "expected"),
    [
        ("{{ value }}", A_DAY, "3 Oct 2026"),
        ("{{ value|date }}", date(2026, 10, 26), "26 Oct 2026"),
        ('{{ value|date:"SHORT_DATE_FORMAT" }}', A_DAY, "03/10/2026"),
        ('{{ value|date:"YEAR_MONTH_FORMAT" }}', A_DAY, "October 2026"),
        ('{{ value|date:"MONTH_DAY_FORMAT" }}', A_DAY, "3 Oct"),
        ("{{ value }}", MOMENT, "3 Oct 2026, 3:05 PM"),
        ('{{ value|date:"SHORT_DATETIME_FORMAT" }}', MOMENT, "03/10/2026, 3:05 PM"),
        ("{{ value|time }}", MOMENT, "3:05 PM"),
    ],
)
def test_dates_show_the_indian_way_in_india_time(template, value, expected):
    assert shown(template, value) == expected


@pytest.mark.parametrize(
    "typed",
    ["10/11/2026", "10-11-2026", "10/11/26", "10 Nov 2026", "10 November 2026", "2026-11-10"],
)
def test_a_typed_date_is_read_day_first(typed):
    assert forms.DateField().clean(typed) == TYPED_DAY


def test_a_date_typed_month_first_is_refused():
    with pytest.raises(forms.ValidationError):
        forms.DateField().clean("12/31/2026")


@pytest.mark.parametrize("typed", ["10/11/2026 15:05", "10-11-2026 15:05", "2026-11-10 15:05"])
def test_a_typed_date_and_time_is_read_day_first_in_india_time(typed):
    assert forms.DateTimeField().clean(typed) == datetime(2026, 11, 10, 15, 5, tzinfo=INDIA)


def test_a_date_time_typed_month_first_is_refused():
    with pytest.raises(forms.ValidationError):
        forms.DateTimeField().clean("12/31/2026 15:05")


def test_a_form_shows_a_saved_date_the_way_a_browsers_date_box_can_read_it():
    assert forms.DateInput().format_value(TYPED_DAY) == "2026-11-10"


@pytest.mark.parametrize("code", [code for code, _name in settings.LANGUAGES])
def test_every_language_has_our_formats(code):
    assert get_format("NUMBER_GROUPING", lang=code) == (3, 2, 0)
    assert get_format("DATE_FORMAT", lang=code) == "j M Y"

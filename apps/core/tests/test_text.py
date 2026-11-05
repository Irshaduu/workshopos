"""Tidying what a person typed (apps/core/text.py). Staff names: apps/staff/tests/test_forms.py."""

import pytest

from apps.core.text import tidy_name, tidy_spaces


@pytest.mark.parametrize(
    ("typed", "saved"),
    [
        ("  Oil   leak ", "Oil leak"),
        ("Oil leak", "Oil leak"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_spaces_at_the_ends_and_double_spaces_go(typed, saved):
    assert tidy_spaces(typed) == saved


def test_an_empty_name_stays_empty():
    assert tidy_name("   ") == ""

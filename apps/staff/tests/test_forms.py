"""What an owner types (apps/staff/forms.py)."""

import pytest

from apps.staff.forms import StaffMemberForm
from apps.staff.models import Designation, tidy_name


@pytest.mark.parametrize(
    ("typed", "saved"),
    [
        pytest.param("anil kumar", "Anil Kumar", id="no capitals: each word gets one"),
        pytest.param("c.k. rajan", "C.K. Rajan", id="no capitals: initials too"),
        pytest.param("d'souza", "D'Souza", id="no capitals: after an apostrophe too"),
        pytest.param("anil KP", "Anil KP", id="its own capitals stay, v1 gave Anil Kp"),
        pytest.param("KP", "KP", id="v1 gave Kp"),
        pytest.param("Anil KP", "Anil KP", id="as typed"),
        pytest.param("Mohammed bin Salim", "Mohammed bin Salim", id="a small word can stay"),
        pytest.param("D'souza", "D'souza", id="a family's own spelling can stay"),
        pytest.param("ANIL KUMAR", "ANIL KUMAR", id="no capital is made small"),
        pytest.param("  Anil   Kumar ", "Anil Kumar", id="spaces at the ends and double spaces"),
        pytest.param("Anil Kumar", "Anil Kumar", id="a space from another keyboard"),
        pytest.param("അനിൽ കുമാർ", "അനിൽ കുമാർ", id="Malayalam has no capitals"),
        pytest.param("അനിൽ KP", "അനിൽ KP", id="Malayalam with initials"),
    ],
)
def test_staff_6_a_name_is_tidied_and_whatever_is_typed_can_be_kept(typed, saved):
    assert tidy_name(typed) == saved


def form(**typed):
    return StaffMemberForm({"name": "Anil Kumar", "designation": "mechanic", **typed})


# A model form asks PostgreSQL about the model's check constraints, so these need it.


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["", "   "])
def test_staff_5_a_name_is_required(name):
    typed = form(name=name)

    assert not typed.is_valid()
    assert typed.errors["name"] == ["Type a name."]


@pytest.mark.django_db
def test_staff_5_a_name_stops_at_100_characters():
    assert form(name="A" * 100).is_valid()

    typed = form(name="A" * 101)

    assert not typed.is_valid()
    assert list(typed.errors) == ["name"]


@pytest.mark.django_db
def test_staff_8_no_designation_is_chosen_for_you():
    typed = form(designation="")

    assert not typed.is_valid()
    assert typed.errors["designation"] == ["Choose a designation."]


@pytest.mark.django_db
def test_staff_3_a_designation_not_on_the_list_is_refused():
    typed = form(designation="painter")

    assert not typed.is_valid()
    assert list(typed.errors) == ["designation"]


@pytest.mark.django_db
@pytest.mark.parametrize("value", Designation.values)
def test_staff_3_each_designation_is_taken(value):
    assert form(designation=value).is_valid()


def test_role_13_the_form_holds_only_what_an_owner_may_change():
    assert list(StaffMemberForm.base_fields) == ["name", "designation"]

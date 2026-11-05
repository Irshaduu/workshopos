"""What is typed on a job card (apps/jobs/forms.py)."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.forms import HiddenInput
from django.utils import timezone

from apps.accounts.models import Role
from apps.accounts.tests.factories import MembershipFactory
from apps.jobs.forms import (
    OTHER_STARTS_AT,
    CancelForm,
    CardForms,
    JobCardForm,
    MileageField,
    OfficeJobCardForm,
    form_for,
    initial_of,
)
from apps.jobs.models import ConcernStatus
from apps.jobs.tests.factories import ConcernFactory, JobCardFactory, JobLineFactory
from apps.staff.models import Designation
from apps.staff.tests.factories import StaffMemberFactory
from apps.vehicles.models import Colour
from apps.vehicles.tests.factories import CustomerFactory
from apps.workshops.models import Branch
from apps.workshops.tests.factories import WorkshopFactory

FLOOR_BOXES = {
    "plate",
    "brand",
    "car_model",
    "chassis_code",
    "vin",
    "colour",
    "colour_other",
    "mileage",
    "lead_mechanic",
    "admitted_date",
    "note",
}
GOOD_VIN = "WBA8E9C50GK123456"


def sent(**typed):
    """What a page sends for a new card, with these boxes typed."""
    return {
        "plate": "KL10AA1000",
        "brand": "BMW",
        "car_model": "520d",
        "admitted_date": timezone.localdate().isoformat(),
        **typed,
    }


@pytest.fixture
def place():
    workshop = WorkshopFactory()
    return {"workshop": workshop, "branch": Branch.objects.for_workshop(workshop).first()}


def checked(place, form_class=JobCardForm, **typed):
    form = form_class(sent(**typed), **place)
    form.is_valid()
    return form


def office(place, **typed):
    return checked(place, OfficeJobCardForm, **{"labour": "", **typed})


pytestmark = pytest.mark.django_db


# Who has which form.


def test_job_54_floors_form_has_no_customer_and_no_labour():
    assert set(JobCardForm.base_fields) == FLOOR_BOXES


def test_job_54_office_adds_the_customer_and_the_labour_charge():
    assert set(OfficeJobCardForm.base_fields) == FLOOR_BOXES | {
        "customer_name",
        "contact_number",
        "labour",
    }


@pytest.mark.parametrize(
    ("role", "form"),
    [
        (Role.OWNER, OfficeJobCardForm),
        (Role.OFFICE, OfficeJobCardForm),
        (Role.FLOOR, JobCardForm),
    ],
)
def test_role_13_a_permission_chooses_the_form(role, form):
    assert form_for(MembershipFactory(role=role).user) is form


def test_role_13_what_floor_may_not_see_never_reaches_its_form():
    customer = CustomerFactory(name="Arun")
    card = JobCardFactory(workshop=customer.workshop, customer=customer, labour=Decimal("2950"))
    floor = MembershipFactory(role=Role.FLOOR, workshop=card.workshop).user

    forms = CardForms.of(floor, card.workshop, card.branch, card=card)

    assert not {"customer_name", "contact_number", "labour"} & forms.main.initial.keys()


# The plate.


@pytest.mark.parametrize(
    ("typed", "saved"), [("kl-10 aa 1000", "KL10AA1000"), ("UAE 12345", "UAE12345")]
)
def test_job_16_a_plate_is_saved_in_one_spelling(place, typed, saved):
    assert checked(place, plate=typed).cleaned_data["plate"] == saved


@pytest.mark.parametrize("plate", ["", "   ", "KL10@1000", "A" * 21])
def test_job_16_a_wrong_or_missing_plate_is_refused(place, plate):
    assert "plate" in checked(place, plate=plate).errors


def test_job_16_the_browser_never_cuts_a_plate(place):
    assert "maxlength" not in str(JobCardForm(**place)["plate"])


# The brand and the model.


def test_job_17_the_brand_and_the_model_are_required(place):
    form = checked(place, brand=" ", car_model="")

    assert {"brand", "car_model"} <= form.errors.keys()


def test_job_17_a_brand_is_tidied_like_a_name_and_a_model_keeps_its_shape(place):
    form = checked(place, brand="land  rover", car_model=" CR-V ")

    assert form.cleaned_data["brand"] == "Land Rover"
    assert form.cleaned_data["car_model"] == "CR-V"


# The chassis code and the VIN.


def test_job_18_a_chassis_code_is_tidied_and_never_refused_for_its_shape(place):
    form = checked(place, chassis_code="991.2 ")

    assert form.errors == {}
    assert form.cleaned_data["chassis_code"] == "991.2"


def test_job_18_a_chassis_code_is_at_most_20(place):
    assert "chassis_code" in checked(place, chassis_code="x" * 21).errors


def test_job_19_a_vin_typed_in_groups_is_one_vin(place):
    assert checked(place, vin="wba 8e9c-50gk 123456").cleaned_data["vin"] == GOOD_VIN


@pytest.mark.parametrize("vin", ["WBA8E9C50GK", "WBA8E9C50GK12345I", "WBA8E9C50GK12345."])
def test_job_19_a_wrong_vin_is_refused_never_corrected(place, vin):
    assert "vin" in checked(place, vin=vin).errors


def test_job_19_the_vin_may_be_left_empty(place):
    assert checked(place, vin="").errors == {}


def test_job_19_the_browser_never_cuts_a_vin(place):
    assert "maxlength" not in str(JobCardForm(**place)["vin"])


# The colour.


def test_job_21_every_colour_and_not_set_are_offered(place):
    values = [value for value, _word in JobCardForm(**place).fields["colour"].choices]

    assert values == [*Colour.values, ""]


def test_job_21_a_colour_that_is_not_on_the_list_is_refused(place):
    assert "colour" in checked(place, colour="purple").errors


def test_job_21_other_needs_its_own_colour(place):
    form = checked(place, colour=Colour.OTHER, colour_other="#7F1D1D")
    assert form.cleaned_data["colour_other"] == "#7f1d1d"

    assert "colour_other" in checked(place, colour=Colour.OTHER, colour_other="red").errors


def test_job_21_other_left_at_the_starting_grey_is_refused_because_nobody_chose_it(place):
    form = checked(place, colour=Colour.OTHER, colour_other=OTHER_STARTS_AT)

    assert form.errors["colour_other"] == ["Pick a colour."]


def test_job_21_any_other_colour_keeps_no_own_colour(place):
    form = checked(place, colour=Colour.RED, colour_other="#7f1d1d")

    assert form.cleaned_data["colour_other"] == ""


def test_job_21_the_swatch_and_the_rail_read_the_colour(place):
    assert JobCardForm(initial={"colour": ""}, **place).paint() == "unset"
    assert JobCardForm(initial={"colour": "red"}, **place).paint() == "red"
    assert JobCardForm(initial={"colour": "red"}, **place).colour_word() == "Red"
    other = JobCardForm(initial={"colour": "other", "colour_other": "#7f1d1d"}, **place)
    assert other.own_colour() == "#7f1d1d"
    assert (
        JobCardForm(initial={"colour": "red", "colour_other": "#7f1d1d"}, **place).own_colour()
        == ""
    )


# The mileage.


@pytest.mark.parametrize(
    ("typed", "reading"),
    [
        ("132022", 132022),
        ("  50000  ", 50000),
        ("50,000", 50000),
        ("1,02,340", 102340),
        ("50000 km", 50000),
        ("50000km", 50000),
        ("50,000 KMS", 50000),
        ("50000 kilometres", 50000),
        ("50000 kilometers", 50000),
        ("50000 k.m.", 50000),
        ("1", 1),
        ("2000000", 2_000_000),
    ],
)
def test_job_22_a_reading_is_a_whole_number_of_kilometres(typed, reading):
    assert MileageField(required=False).clean(typed) == reading


@pytest.mark.parametrize("typed", ["", "   "])
def test_job_22_an_empty_box_means_no_reading(typed):
    assert MileageField(required=False).clean(typed) is None


@pytest.mark.parametrize(
    "typed",
    [
        "0",
        "-100",
        "50000 mi",
        "50000 miles",
        "approx 50000",
        "n/a",
        "50k",
        "50.5k",
        "50000.4",
        "50,0",
        "1,2,3",
        "2,95",
        "13,20",
        "123,45",
        "1,32,02",
        "9" * 5000,
        "85000 2",
        "1_000",
        "٣٤",
        "2000001",
    ],
)
def test_job_22_anything_else_is_refused_never_guessed(place, typed):
    form = checked(place, mileage=typed)

    assert "mileage" in form.errors
    assert "whole number" in form.errors["mileage"][0]


def test_job_22_the_box_is_a_text_box_with_a_number_keypad():
    widget = MileageField().widget

    assert widget.input_type == "text"
    assert widget.attrs["inputmode"] == "numeric"


# The lead mechanic.


def test_job_23_the_picker_offers_mechanics_then_assistants_each_by_name(place):
    member = dict(place)
    StaffMemberFactory(name="Zaid", **member)
    StaffMemberFactory(name="Biju", designation=Designation.ASSISTANT_MECHANIC, **member)
    StaffMemberFactory(name="Ajay", **member)
    StaffMemberFactory(name="Office Person", designation=Designation.OFFICE_STAFF, **member)
    StaffMemberFactory(name="Gone", is_active=False, **member)

    choices = [word for _key, word in JobCardForm(**place).fields["lead_mechanic"].choices]

    assert choices == ["Not picked", "Ajay", "Zaid", "Biju"]


def test_job_23_a_person_of_another_branch_or_workshop_is_not_offered(place):
    StaffMemberFactory(name="Theirs")
    other_branch = Branch(workshop=place["workshop"], name="Other")
    other_branch.save()
    StaffMemberFactory(name="There", workshop=place["workshop"], branch=other_branch)

    choices = [word for _key, word in JobCardForm(**place).fields["lead_mechanic"].choices]

    assert choices == ["Not picked"]


def test_job_23_a_card_keeps_its_person_shown_as_not_current(place):
    gone = StaffMemberFactory(name="Gone", is_active=False, **place)
    moved = StaffMemberFactory(name="Moved", designation=Designation.GENERAL_HELPER, **place)
    StaffMemberFactory(name="Ajay", **place)

    for person, word in (
        (gone, "Gone, Mechanic, not current"),
        (moved, "Moved, General Helper, not current"),
    ):
        choices = JobCardForm(mechanic_key=person.pk, **place).fields["lead_mechanic"].choices
        assert [text for _key, text in choices] == ["Not picked", "Ajay", word]


def test_job_23_a_person_not_offered_is_refused(place):
    helper = StaffMemberFactory(designation=Designation.GENERAL_HELPER, **place)

    assert "lead_mechanic" in checked(place, lead_mechanic=str(helper.pk)).errors


# The admitted date.


def test_job_24_today_and_an_earlier_day_are_fine(place):
    today = timezone.localdate()

    assert checked(place, admitted_date=today.isoformat()).errors == {}
    assert checked(place, admitted_date=(today - timedelta(days=90)).isoformat()).errors == {}


def test_job_24_a_day_in_the_future_is_refused_never_moved(place):
    tomorrow = timezone.localdate() + timedelta(days=1)

    form = checked(place, admitted_date=tomorrow.isoformat())

    assert form.errors == {"admitted_date": ["A car cannot be admitted on a date in the future."]}


def test_job_24_the_date_is_required(place):
    assert "admitted_date" in checked(place, admitted_date="").errors


def test_job_24_the_picker_stops_at_today_read_on_each_page(place):
    form = JobCardForm(**place)

    assert form.fields["admitted_date"].widget.attrs["max"] == timezone.localdate().isoformat()


# The note and the customer.


def test_job_25_a_note_is_optional_up_to_255(place):
    assert checked(place, note="").errors == {}
    assert checked(place, note="x" * 255).errors == {}
    assert "note" in checked(place, note="x" * 256).errors


def test_job_30_a_name_is_tidied_and_a_number_has_one_spelling(place):
    form = office(place, customer_name="anil KP", contact_number="+91 90000 00001")

    assert form.errors == {}
    assert form.cleaned_data["customer_name"] == "Anil KP"
    assert form.cleaned_data["contact_number"] == "9000000001"


def test_job_30_a_wrong_number_is_refused(place):
    assert "contact_number" in office(place, contact_number="abc").errors


def test_job_26_the_customer_is_optional(place):
    assert office(place, customer_name="", contact_number="", labour="").errors == {}


# The labour charge.


def test_job_32_an_empty_labour_box_means_zero(place):
    assert office(place, labour="").cleaned_data["labour"] == Decimal("0.00")


@pytest.mark.parametrize(
    ("typed", "words"),
    [("-1", "cannot be negative"), ("2,950", "no commas"), ("2950.555", "at most")],
)
def test_job_32_a_wrong_amount_is_refused_in_plain_words(place, typed, words):
    assert words in office(place, labour=typed).errors["labour"][0]


def test_adr_29_a_labour_box_never_sent_refuses_the_form(place):
    form = OfficeJobCardForm(sent(), **place)

    assert "labour" in form.errors


# What a page marks and what a box keeps.


@pytest.mark.parametrize("name", ["plate", "brand", "car_model", "chassis_code", "vin", "mileage"])
def test_job_48_these_empty_boxes_wear_the_hairline(place, name):
    assert OfficeJobCardForm(**place).fields[name].widget.attrs.get("placeholder") == " "


@pytest.mark.parametrize("name", ["customer_name", "contact_number", "note", "labour"])
def test_job_48_these_empty_boxes_do_not(place, name):
    assert "placeholder" not in OfficeJobCardForm(**place).fields[name].widget.attrs


def test_every_box_keeps_the_value_the_page_opened_with(place):
    html = str(OfficeJobCardForm(initial={"plate": "KL10AA1000"}, **place)["plate"])

    assert 'name="initial-plate" value="KL10AA1000"' in html
    assert all(field.show_hidden_initial for field in OfficeJobCardForm(**place).fields.values())


def test_role_13_the_field_itself_is_never_hidden():
    assert not isinstance(OfficeJobCardForm.base_fields["labour"].widget, HiddenInput)


def opened_with(place, **values):
    return {f"initial-{box}": value for box, value in values.items()}


def typed_over(place, opening, **typed):
    data = {**sent(**opening), **opened_with(place, **sent(**opening)), **sent(**typed)}
    form = JobCardForm(data, **place)
    assert form.is_valid(), form.errors
    return form


def test_job_43_only_what_this_person_changed(place):
    form = typed_over(place, {"note": "Old"}, note="Old", mileage="5000")

    assert form.changes() == {"mileage": 5000}


def test_job_43_a_record_moved_on_since_is_not_a_change(place):
    data = {**sent(note="Old"), **opened_with(place, **sent(note="Old"))}

    form = JobCardForm(data, initial={"note": "Office's fix"}, **place)

    assert form.is_valid()
    assert form.changes() == {}


def test_job_21_a_new_colour_brings_the_colour_box_with_it(place):
    form = typed_over(place, {"colour": "red"}, colour="other", colour_other="#7f1d1d")

    assert form.changes() == {"colour": "other", "colour_other": "#7f1d1d"}


def test_job_21_a_changed_colour_box_counts_only_under_other(place):
    form = typed_over(
        place,
        {"colour": "red", "colour_other": OTHER_STARTS_AT},
        colour="red",
        colour_other="#7f1d1d",
    )
    assert form.changes() == {}

    form = typed_over(
        place,
        {"colour": "other", "colour_other": "#000000"},
        colour="other",
        colour_other="#7f1d1d",
    )
    assert form.changes() == {"colour": "other", "colour_other": "#7f1d1d"}


def test_job_21_a_colour_box_always_opens_with_a_colour(place):
    # A browser's colour box always sends a colour, so an empty one would look changed.
    assert initial_of(JobCardFactory())["colour_other"] == OTHER_STARTS_AT

    own = JobCardFactory(car__colour=Colour.OTHER, car__colour_other="#7f1d1d")
    assert initial_of(own)["colour_other"] == "#7f1d1d"


def test_job_21_leaving_other_clears_its_own_colour(place):
    form = typed_over(
        place, {"colour": "other", "colour_other": "#000000"}, colour="red", colour_other="#000000"
    )

    assert form.changes() == {"colour": "red", "colour_other": ""}


# The lists.


def forms_of(card, data=None, role=Role.OFFICE):
    user = MembershipFactory(role=role, workshop=card.workshop).user
    return CardForms.of(user, card.workshop, card.branch, card=card, data=data)


def list_data(prefix="concerns", total=1):
    return {
        f"{prefix}-TOTAL_FORMS": str(total),
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }


def card_data(card, **typed):
    """What a saved card's page sends with nothing touched, and these boxes typed."""
    opening = {
        "plate": card.plate,
        "brand": card.car.car_model.brand.name,
        "car_model": card.car.car_model.name,
        "admitted_date": card.admitted_date.isoformat(),
        "colour_other": OTHER_STARTS_AT,
        "labour": "",
    }
    return {
        **opening,
        **{f"initial-{box}": value for box, value in opening.items()},
        **list_data("concerns"),
        **list_data("job_lines"),
        **typed,
    }


def test_job_35_an_untouched_open_row_is_never_saved():
    card = JobCardFactory()

    forms = forms_of(card, card_data(card))

    assert forms.is_valid(), forms.problems()
    assert forms.concerns.new_rows() == []
    assert forms.job_lines.new_rows() == []


def test_job_35_a_status_alone_is_not_typing():
    card = JobCardFactory()

    forms = forms_of(card, card_data(card, **{"concerns-0-status": ConcernStatus.FIXED}))

    assert forms.is_valid(), forms.problems()
    assert forms.concerns.new_rows() == []


def test_job_35_a_new_row_with_words_is_saved():
    card = JobCardFactory()
    data = card_data(
        card,
        **{
            "concerns-0-text": "Oil leak",
            "concerns-0-status": ConcernStatus.WORKING,
            "job_lines-0-text": "Oil changed",
        },
    )

    forms = forms_of(card, data)

    assert forms.is_valid(), forms.problems()
    assert forms.concerns.new_rows()[0]["status"] == ConcernStatus.WORKING
    assert forms.job_lines.new_rows()[0]["text"] == "Oil changed"


def test_job_34_a_row_too_long_is_refused_and_named():
    card = JobCardFactory()
    data = card_data(
        card,
        **{
            "job_lines-0-text": "x" * 151,
            "concerns-0-text": "y" * 256,
            "concerns-0-status": ConcernStatus.PENDING,
        },
    )

    forms = forms_of(card, data)

    assert not forms.is_valid()
    assert "job_lines" not in forms.problems()
    assert [where.split(",")[0] for where, _what in forms.problems()] == ["Concern", "Job"]


def test_job_43_a_saved_row_with_nothing_touched_is_no_change():
    row = ConcernFactory(text="Oil leak")
    card = row.job_card
    prefix = f"concern-{row.pk}"
    data = card_data(
        card,
        **{
            f"{prefix}-text": "Oil leak",
            f"initial-{prefix}-text": "Oil leak",
            f"{prefix}-status": ConcernStatus.PENDING,
            f"initial-{prefix}-status": ConcernStatus.PENDING,
        },
    )

    forms = forms_of(card, data)

    assert forms.is_valid(), forms.problems()
    assert forms.concerns.saved_changes() == []


def test_job_43_a_saved_row_gives_only_what_changed_and_its_key():
    row = ConcernFactory(text="Oil leak")
    card = row.job_card
    prefix = f"concern-{row.pk}"
    data = card_data(
        card,
        **{
            f"{prefix}-text": "Oil leak",
            f"initial-{prefix}-text": "Oil leak",
            f"{prefix}-status": ConcernStatus.FIXED,
            f"initial-{prefix}-status": ConcernStatus.PENDING,
        },
    )

    forms = forms_of(card, data)

    assert forms.is_valid(), forms.problems()
    assert forms.concerns.saved_changes() == [(row.pk, {"status": ConcernStatus.FIXED})]


def test_job_36_emptied_words_are_a_change_not_an_error():
    row = JobLineFactory(text="Oil changed")
    card = row.job_card
    prefix = f"job_line-{row.pk}"
    data = card_data(card, **{f"{prefix}-text": "", f"initial-{prefix}-text": "Oil changed"})

    forms = forms_of(card, data)

    assert forms.is_valid(), forms.problems()
    assert forms.job_lines.saved_changes() == [(row.pk, {"text": ""})]


def test_job_43_a_row_someone_else_added_after_the_page_opened_is_left_alone():
    row = ConcernFactory(text="Added by someone else")
    card = row.job_card

    forms = forms_of(card, card_data(card))

    assert forms.is_valid(), forms.problems()
    assert forms.concerns.saved_changes() == []
    assert forms.concerns.saved[0]["text"].value() == "Added by someone else"


def test_every_box_of_a_list_has_a_name_for_a_screen_reader():
    row = ConcernFactory(text="Oil leak")

    forms = forms_of(row.job_card)

    assert 'aria-label="Concern 1"' in str(forms.concerns.saved[0]["text"])
    assert 'aria-label="Status of concern 1"' in str(forms.concerns.saved[0]["status"])
    assert 'aria-label="New concern"' in str(forms.concerns.new[0]["text"])
    assert 'aria-label="New job"' in str(forms.job_lines.blank()["text"])


def test_a_cancelled_card_has_no_open_row():
    card = JobCardFactory(status="cancelled", cancel_reason="Customer left")

    assert forms_of(card).concerns.new is None


# Cancelling.


def test_job_50_a_reason_must_be_typed():
    assert "reason" in CancelForm({"reason": "   "}).errors
    assert CancelForm({"reason": "Customer left"}).is_valid()
    assert "reason" in CancelForm({"reason": "x" * 256}).errors

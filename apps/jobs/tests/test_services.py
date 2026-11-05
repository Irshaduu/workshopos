"""Making, changing and cancelling a job card (apps/jobs/services.py)."""

import uuid
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.http import Http404
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.jobs.models import ConcernStatus, JobCard, JobCardStatus, StepKind
from apps.jobs.selectors import cancelled_step, job_card, open_card_of, open_job_cards
from apps.jobs.services import (
    CarHasOpenCard,
    RowRefused,
    cancel_job_card,
    change_job_card,
    make_job_card,
)
from apps.jobs.tests.factories import ConcernFactory, JobCardFactory, JobLineFactory
from apps.staff.tests.factories import StaffMemberFactory
from apps.vehicles.models import Car, Colour, Customer
from apps.vehicles.tests.factories import CarFactory, CustomerFactory
from apps.workshops.models import Branch
from apps.workshops.tests.factories import BranchFactory, WorkshopFactory

pytestmark = pytest.mark.django_db


def typed(plate="KL10AA1000", **more):
    return {
        "plate": plate,
        "brand": "BMW",
        "car_model": "520d",
        "admitted_date": timezone.localdate(),
        **more,
    }


@pytest.fixture
def place():
    """A workshop, its first branch, and who acts."""
    workshop = WorkshopFactory()
    return workshop, Branch.objects.for_workshop(workshop).first(), UserFactory()


def make(place, key=None, concerns=(), job_lines=(), **more):
    workshop, branch, by = place
    return make_job_card(
        workshop,
        branch,
        key or uuid.uuid7(),
        by,
        typed=typed(**more),
        concerns=concerns,
        job_lines=job_lines,
    )


def change(place, card, **more):
    workshop, branch, by = place
    return change_job_card(workshop, branch, card.pk, by, changes=more.pop("changes", {}), **more)


def fresh(card):
    return JobCard.objects.get(pk=card.pk)


def kinds(card):
    return [step.kind for step in card.steps.all()]


def concern_row(text, status=ConcernStatus.PENDING):
    return {"text": text, "status": status}


# Making a card.


def test_job_1_a_card_holds_its_car_visit_and_rows(place):
    card = make(
        place,
        mileage=132022,
        note="Noise only when cold",
        labour=Decimal("2950.00"),
        customer_name="Arun K",
        contact_number="9000000001",
        concerns=[concern_row("Brake noise")],
        job_lines=[{"text": "Brake disc skim"}],
    )

    card = fresh(card)
    assert card.is_open
    assert card.car.name == "BMW 520d"
    assert card.plate == "KL10AA1000"
    assert (card.mileage, card.note, card.labour) == (
        132022,
        "Noise only when cold",
        Decimal("2950.00"),
    )
    assert card.customer.name == "Arun K"
    assert [row.text for row in card.concerns.all()] == ["Brake noise"]
    assert [row.text for row in card.job_lines.all()] == ["Brake disc skim"]


def test_job_2_a_card_belongs_to_the_branch_it_was_made_in(place):
    workshop, branch, by = place
    there = BranchFactory(workshop=workshop)

    card = make_job_card(workshop, there, uuid.uuid7(), by, typed=typed())

    assert card.branch == there
    assert open_job_cards(workshop, there).get() == card
    assert not open_job_cards(workshop, branch).exists()


def test_job_54_a_new_card_from_floor_has_no_customer_and_no_labour(place):
    card = fresh(make(place))

    assert card.customer is None
    assert card.labour == 0


def test_job_26_a_card_may_have_no_customer_and_makes_no_record(place):
    workshop, _branch, _by = place

    make(place, customer_name="", contact_number="")

    assert not Customer.objects.for_workshop(workshop).exists()


def test_job_14_a_known_plate_joins_its_car(place):
    workshop, branch, by = place
    car = CarFactory(workshop=workshop, plate="KL10AA1000")

    card = make(place, plate="kl-10 aa 1000")

    assert card.car == car
    assert Car.objects.for_workshop(workshop).count() == 1


# One open card per car.


def test_job_4_a_second_open_card_is_refused_and_names_the_first(place):
    first = make(place)

    with pytest.raises(CarHasOpenCard) as refused:
        make(place)

    assert refused.value.card == first
    assert refused.value.message_dict == {
        "plate": [f"This car already has an open job card, {first.number}."]
    }
    assert JobCard.objects.for_workshop(place[0]).count() == 1


def test_job_4_it_holds_across_branches(place):
    workshop, _branch, by = place
    first = make(place)
    there = BranchFactory(workshop=workshop)

    with pytest.raises(CarHasOpenCard) as refused:
        make_job_card(workshop, there, uuid.uuid7(), by, typed=typed())

    assert refused.value.card == first


def test_job_4_a_second_open_card_changes_nothing_on_the_car(place):
    first = make(place, chassis_code="F30")

    with pytest.raises(CarHasOpenCard):
        make(place, chassis_code="G20")

    assert Car.objects.get(pk=first.car_id).chassis_code == "F30"


def test_job_51_a_cancelled_card_frees_its_car_at_once(place):
    workshop, branch, by = place
    first = make(place)
    cancel_job_card(workshop, branch, first.pk, by, "Customer left")

    assert make(place).car == first.car
    assert open_card_of(first.workshop, first.car) != first


# Saving once.


def test_job_42_a_repeat_answers_with_the_card_saved_first_and_adds_nothing(place):
    key = uuid.uuid7()

    first = make(place, key=key, concerns=[concern_row("Brake noise")])
    again = make(place, key=key, concerns=[concern_row("Brake noise")])

    assert again == first
    assert fresh(first).concerns.count() == 1
    assert kinds(first) == [StepKind.CAR_IN]


def test_job_42_a_key_saved_in_another_workshop_answers_not_found(place):
    theirs = JobCardFactory()

    with pytest.raises(Http404):
        make(place, key=theirs.pk, plate="KL99ZZ9999")


def test_job_42_a_key_saved_in_another_branch_answers_not_found(place):
    workshop, _branch, _by = place
    there = BranchFactory(workshop=workshop)
    theirs = JobCardFactory(workshop=workshop, branch=there)

    with pytest.raises(Http404):
        make(place, key=theirs.pk, plate="KL99ZZ9999")


def test_job_42_only_a_uuid7_may_become_a_key(place):
    with pytest.raises(Http404):
        make(place, key=uuid.uuid4())

    assert not JobCard.objects.for_workshop(place[0]).exists()


# A save changes only what this person changed.


def test_job_43_a_box_not_in_changes_is_left_alone(place):
    card = make(place, note="Office's fix", mileage=1000, chassis_code="F30")

    change(place, card, changes={"mileage": 2000})

    card = fresh(card)
    assert (card.note, card.mileage, card.car.chassis_code) == ("Office's fix", 2000, "F30")


def test_job_43_nothing_changed_changes_nothing(place):
    card = make(place)

    change(place, card)

    assert kinds(fresh(card)) == [StepKind.CAR_IN]


def test_job_12_a_change_on_a_card_changes_the_car(place):
    card = make(place)

    change(
        place,
        card,
        changes={
            "brand": "bmw",
            "car_model": "530d",
            "vin": "WBA8E9C50GK123456",
            "colour": Colour.OTHER,
            "colour_other": "#7f1d1d",
        },
    )

    car = fresh(card).car
    assert car.name == "BMW 530d"
    assert car.vin == "WBA8E9C50GK123456"
    assert (car.colour, car.colour_other) == (Colour.OTHER, "#7f1d1d")


def test_job_21_a_colour_with_no_own_colour_clears_others(place):
    card = make(place, colour=Colour.OTHER, colour_other="#7f1d1d")

    change(place, card, changes={"colour": Colour.RED, "colour_other": ""})

    car = fresh(card).car
    assert (car.colour, car.colour_other) == (Colour.RED, "")


def test_job_13_a_new_plate_changes_the_car_from_that_day_and_an_old_card_keeps_its_own(place):
    workshop, branch, by = place
    old = make(place, plate="KL10AA1000")
    cancel_job_card(workshop, branch, old.pk, by, "Finished for this test")
    new = make(place, plate="KL10AA1000")

    change(place, new, changes={"plate": "TN01AB2000"})

    assert fresh(new).plate == "TN01AB2000"
    assert fresh(new).car.plate == "TN01AB2000"
    assert fresh(old).plate == "KL10AA1000"
    assert fresh(old).car == fresh(new).car


def test_job_15_a_plate_on_another_car_is_refused_and_nothing_changes(place):
    workshop, _branch, _by = place
    other = CarFactory(
        workshop=workshop, plate="KL10AB2000", car_model__brand__name="Audi", car_model__name="A4"
    )
    card = make(place, plate="KL10AA1000")

    with pytest.raises(ValidationError) as refused:
        change(place, card, changes={"plate": other.plate, "mileage": 5000})

    assert refused.value.message_dict == {"plate": ["This plate is on another car, Audi A4."]}
    assert fresh(card).plate == "KL10AA1000"
    assert fresh(card).mileage is None


def test_job_23_a_change_of_mechanic(place):
    workshop, _branch, _by = place
    mechanic = StaffMemberFactory(workshop=workshop)
    card = make(place)

    change(place, card, changes={"lead_mechanic": mechanic})

    assert fresh(card).lead_mechanic == mechanic


def test_job_24_a_card_may_be_dated_earlier(place):
    earlier = timezone.localdate().replace(year=2020)
    card = make(place)

    change(place, card, changes={"admitted_date": earlier})

    assert fresh(card).admitted_date == earlier


def test_job_32_the_labour_charge_changes_alone(place):
    card = make(place)

    change(place, card, changes={"labour": Decimal("2950.00")})

    assert fresh(card).labour == Decimal("2950.00")


# The customer.


def customer_of(card):
    return fresh(card).customer


def test_job_28_new_boxes_point_the_card_to_another_record_and_no_other_card_changes(place):
    workshop, branch, _by = place
    arun = CustomerFactory(workshop=workshop, name="Arun", contact_number="9000000001")
    other_card = JobCardFactory(workshop=workshop, branch=branch, customer=arun)
    card = make(place, customer_name="Arun", contact_number="9000000001")
    assert customer_of(card) == arun

    change(place, card, changes={"customer_name": "Vijay", "contact_number": "9000000003"})

    assert customer_of(card).name == "Vijay"
    assert customer_of(other_card) == arun
    arun.refresh_from_db()
    assert arun.name == "Arun"


def test_job_28_one_box_changed_keeps_the_others_value(place):
    card = make(place, customer_name="Arun", contact_number="9000000001")

    change(place, card, changes={"customer_name": "Vijay"})

    assert customer_of(card).name == "Vijay"
    assert customer_of(card).contact_number == "9000000001"

    change(place, card, changes={"contact_number": "9000000002"})

    assert customer_of(card).name == "Vijay"
    assert customer_of(card).contact_number == "9000000002"


def test_job_28_emptying_both_takes_the_customer_off_and_keeps_the_record(place):
    workshop, _branch, _by = place
    card = make(place, customer_name="Arun", contact_number="9000000001")

    change(place, card, changes={"customer_name": "", "contact_number": ""})

    assert customer_of(card) is None
    assert Customer.objects.for_workshop(workshop).count() == 1


def test_job_29_a_sale_changes_only_the_next_card(place):
    workshop, branch, by = place
    old = make(place, customer_name="Arun", contact_number="9000000001")
    cancel_job_card(workshop, branch, old.pk, by, "Finished for this test")

    new = make(place, customer_name="Vijay", contact_number="9000000003")

    assert new.car == old.car
    assert customer_of(old).name == "Arun"
    assert customer_of(new).name == "Vijay"


# The rows.


def test_job_36_emptied_words_remove_a_saved_row(place):
    card = make(
        place, concerns=[concern_row("Brake noise")], job_lines=[{"text": "Brake disc skim"}]
    )
    concern = card.concerns.get()
    line = card.job_lines.get()

    change(
        place,
        card,
        saved_concerns=[(concern.pk, {"text": "  "})],
        saved_lines=[(line.pk, {"text": ""})],
    )

    assert not card.concerns.exists()
    assert not card.job_lines.exists()


def test_job_37_a_new_row_that_repeats_one_is_left_out_with_no_error(place):
    card = make(place, concerns=[concern_row("Oil leak")], job_lines=[{"text": "Oil changed"}])

    change(
        place,
        card,
        new_concerns=[concern_row("OIL  LEAK"), concern_row("AC not cooling")],
        new_lines=[{"text": "oil changed"}],
    )

    assert [row.text for row in card.concerns.all()] == ["Oil leak", "AC not cooling"]
    assert [row.text for row in card.job_lines.all()] == ["Oil changed"]


def test_job_37_two_new_rows_with_the_same_words_are_one(place):
    card = make(place, concerns=[concern_row("Oil leak"), concern_row("oil leak")])

    assert card.concerns.count() == 1


def test_job_37_a_saved_row_changed_to_repeat_another_is_refused(place):
    card = make(place, concerns=[concern_row("Oil leak"), concern_row("AC not cooling")])
    second = card.concerns.get(text="AC not cooling")

    with pytest.raises(RowRefused) as refused:
        change(place, card, saved_concerns=[(second.pk, {"text": "OIL LEAK"})])

    assert refused.value.key == second.pk
    assert second.__class__.objects.get(pk=second.pk).text == "AC not cooling"


@pytest.mark.parametrize("renamed_first", [True, False])
def test_job_37_a_row_may_take_the_words_of_a_row_emptied_in_the_same_save(place, renamed_first):
    card = make(place, concerns=[concern_row("Brake"), concern_row("Oil")])
    brake, oil = card.concerns.all()
    saved = [(brake.pk, {"text": "Oil"}), (oil.pk, {"text": ""})]

    change(place, card, saved_concerns=saved if renamed_first else saved[::-1])

    assert [row.text for row in card.concerns.all()] == ["Oil"]


def test_job_37_a_job_line_may_take_the_words_of_a_line_emptied_in_the_same_save(place):
    card = make(place, job_lines=[{"text": "Brake"}, {"text": "Oil"}])
    brake, oil = card.job_lines.all()

    change(place, card, saved_lines=[(brake.pk, {"text": "Oil"}), (oil.pk, {"text": ""})])

    assert [row.text for row in card.job_lines.all()] == ["Oil"]


def test_job_37_a_saved_row_may_change_its_own_capitals(place):
    card = make(place, concerns=[concern_row("oil leak")])
    row = card.concerns.get()

    change(place, card, saved_concerns=[(row.pk, {"text": "Oil Leak"})])

    assert card.concerns.get().text == "Oil Leak"


def test_job_43_emptying_a_row_someone_else_removed_changes_nothing(place):
    card = make(place, concerns=[concern_row("Oil leak")], job_lines=[{"text": "Oil changed"}])
    concern = card.concerns.get()
    line = card.job_lines.get()
    concern_key, line_key = concern.pk, line.pk
    concern.delete()
    line.delete()

    change(
        place,
        card,
        saved_concerns=[(concern_key, {"text": ""})],
        saved_lines=[(line_key, {"text": ""})],
    )

    assert not card.concerns.exists()
    assert not card.job_lines.exists()


def test_job_43_a_row_someone_else_removed_stays_removed(place):
    card = make(place, concerns=[concern_row("Oil leak")], job_lines=[{"text": "Oil changed"}])
    concern = card.concerns.get()
    line = card.job_lines.get()
    concern_key, line_key = concern.pk, line.pk
    concern.delete()
    line.delete()

    change(
        place,
        card,
        saved_concerns=[(concern_key, {"status": ConcernStatus.FIXED})],
        saved_lines=[(line_key, {"text": "Changed words"})],
    )

    assert not card.concerns.exists()
    assert not card.job_lines.exists()


def test_a_row_of_another_card_is_never_changed(place):
    card = make(place)
    theirs = ConcernFactory(workshop=place[0], text="Not this card's")

    change(place, card, saved_concerns=[(theirs.pk, {"text": "Changed"})])

    theirs.refresh_from_db()
    assert theirs.text == "Not this card's"


def test_job_38_new_rows_come_after_the_saved_ones(place):
    card = make(place, job_lines=[{"text": "First"}])

    change(place, card, new_lines=[{"text": "Second"}])

    assert [row.text for row in card.job_lines.all()] == ["First", "Second"]


# History.


def test_job_39_a_new_card_has_its_car_in_step(place):
    workshop, _branch, by = place

    card = make(place)

    step = fresh(card).steps.get()
    assert step.kind == StepKind.CAR_IN
    assert step.at is not None
    assert step.by == by
    assert step.workshop == workshop


def test_job_39_each_change_of_a_concerns_status_is_a_row(place):
    card = make(place, concerns=[concern_row("Oil leak")])
    row = card.concerns.get()

    for status in (ConcernStatus.WORKING, ConcernStatus.FIXED, ConcernStatus.WORKING):
        change(place, card, saved_concerns=[(row.pk, {"status": status})])

    assert kinds(card) == [
        StepKind.CAR_IN,
        StepKind.CONCERN_WORKING,
        StepKind.CONCERN_FIXED,
        StepKind.CONCERN_WORKING,
    ]


def test_job_40_a_step_keeps_who_acted_and_the_mechanic_at_that_moment(place):
    workshop, _branch, by = place
    ajay = StaffMemberFactory(workshop=workshop, name="Ajay")
    biju = StaffMemberFactory(workshop=workshop, name="Biju")
    card = make(place, lead_mechanic=ajay, concerns=[concern_row("Oil leak")])
    row = card.concerns.get()

    change(place, card, saved_concerns=[(row.pk, {"status": ConcernStatus.WORKING})])
    change(
        place,
        card,
        changes={"lead_mechanic": biju},
        saved_concerns=[(row.pk, {"status": ConcernStatus.FIXED})],
    )

    steps = list(card.steps.all())
    assert [step.mechanic for step in steps] == [ajay, ajay, biju]
    assert {step.by for step in steps} == {by}


def test_job_41_a_new_concern_already_working_or_fixed_gets_its_step(place):
    card = make(
        place,
        concerns=[
            concern_row("Pending one"),
            concern_row("Working one", ConcernStatus.WORKING),
            concern_row("Fixed one", ConcernStatus.FIXED),
        ],
    )

    assert kinds(card) == [StepKind.CAR_IN, StepKind.CONCERN_WORKING, StepKind.CONCERN_FIXED]


def test_job_41_a_save_that_changes_no_status_adds_no_step(place):
    card = make(place, concerns=[concern_row("Oil leak", ConcernStatus.WORKING)])
    row = card.concerns.get()

    change(place, card, saved_concerns=[(row.pk, {"text": "Oil leak at the sump"})])
    # A repeat: the status is already set.
    change(place, card, saved_concerns=[(row.pk, {"status": ConcernStatus.WORKING})])

    assert kinds(card) == [StepKind.CAR_IN, StepKind.CONCERN_WORKING]


def test_job_41_a_concerns_status_and_its_newest_step_always_agree(place):
    card = make(place, concerns=[concern_row("Oil leak", ConcernStatus.WORKING)])
    row = card.concerns.get()

    for status in (
        ConcernStatus.FIXED,
        ConcernStatus.PENDING,
        ConcernStatus.PENDING,
        ConcernStatus.WORKING,
        ConcernStatus.FIXED,
    ):
        change(place, card, saved_concerns=[(row.pk, {"status": status})])
        row.refresh_from_db()
        assert row.steps.last().kind == f"concern_{row.status}"


def test_job_41_removing_a_concern_removes_its_steps(place):
    card = make(place, concerns=[concern_row("Oil leak", ConcernStatus.FIXED)])
    row = card.concerns.get()

    change(place, card, saved_concerns=[(row.pk, {"text": ""})])

    assert kinds(card) == [StepKind.CAR_IN]


# Cancelling.


def test_job_49_a_cancelled_card_keeps_everything_on_it(place):
    workshop, branch, by = place
    card = make(
        place,
        labour=Decimal("2950.00"),
        concerns=[concern_row("Oil leak")],
        job_lines=[{"text": "Oil changed"}],
    )

    cancel_job_card(workshop, branch, card.pk, by, "  Customer   took the car ")

    card = fresh(card)
    assert card.status == JobCardStatus.CANCELLED
    assert card.cancel_reason == "Customer took the car"
    assert card.labour == Decimal("2950.00")
    assert card.concerns.count() == 1
    assert card.job_lines.count() == 1


def test_job_51_it_says_who_and_when(place):
    workshop, branch, by = place
    another = make(place, plate="KL10AA1001")
    card = make(place)

    cancel_job_card(workshop, branch, another.pk, UserFactory(), "Another reason")
    cancel_job_card(workshop, branch, card.pk, by, "Customer left")

    step = cancelled_step(workshop, fresh(card))
    assert step.kind == StepKind.CANCELLED
    assert step.by == by


def test_job_51_a_repeat_changes_nothing(place):
    workshop, branch, by = place
    card = make(place)

    cancel_job_card(workshop, branch, card.pk, by, "First reason")
    cancel_job_card(workshop, branch, card.pk, by, "Second reason")

    assert fresh(card).cancel_reason == "First reason"
    assert kinds(card) == [StepKind.CAR_IN, StepKind.CANCELLED]


def test_job_51_a_cancelled_card_refuses_a_change(place):
    workshop, branch, by = place
    card = make(place)
    cancel_job_card(workshop, branch, card.pk, by, "Customer left")

    with pytest.raises(ValidationError):
        change(place, card, changes={"mileage": 5000})

    assert fresh(card).mileage is None


@pytest.mark.parametrize("act", ["change", "cancel"])
def test_job_2_a_card_of_another_branch_is_not_found(place, act):
    workshop, _branch, by = place
    there = BranchFactory(workshop=workshop)
    theirs = JobCardFactory(workshop=workshop, branch=there)

    with pytest.raises(Http404):
        if act == "change":
            change(place, theirs)
        else:
            cancel_job_card(workshop, _branch, theirs.pk, by, "Reason")

    assert fresh(theirs).is_open


def test_a_cards_car_customer_and_mechanic_come_with_it_in_one_query(
    place, django_assert_num_queries
):
    workshop, branch, _by = place
    mechanic = StaffMemberFactory(workshop=workshop, branch=branch)
    card = make(place, customer_name="Arun", lead_mechanic=mechanic)

    with django_assert_num_queries(1):
        found = job_card(workshop, branch, card.pk)
        assert found.car.name == "BMW 520d"
        assert found.customer.name == "Arun"
        assert found.lead_mechanic == mechanic


# The first live board.


def test_job_61_the_board_lists_this_branchs_open_cards_newest_first(place):
    workshop, branch, by = place
    older = make(place, plate="KL10AA1000")
    newer = make(place, plate="KL10AA1001")
    gone = make(place, plate="KL10AA1002")
    cancel_job_card(workshop, branch, gone.pk, by, "Customer left")
    JobCardFactory(workshop=workshop, branch=BranchFactory(workshop=workshop))
    JobCardFactory()

    assert list(open_job_cards(workshop, branch)) == [newer, older]


def test_a_job_line_belongs_to_its_card():
    line = JobLineFactory()

    assert line in line.job_card.job_lines.all()

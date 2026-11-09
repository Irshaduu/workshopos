"""What a save asks before it uses one car's record for another, and moving an open job card
to the right car (docs/rules/known-plate.md, KNOWN-1, KNOWN-2 and KNOWN-10 to KNOWN-17;
apps/jobs/services.py). The page's wiring: test_pages.py."""

import threading
import time
import uuid
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.utils import timezone

from apps.jobs import services
from apps.jobs.models import JobCard, JobCardStatus, NumberCounter, StepKind
from apps.jobs.selectors import known_car
from apps.jobs.services import CarHasOpenCard, Question
from apps.jobs.tests.cards import change, fresh, make, said
from apps.jobs.tests.cards import visit as a_visit
from apps.jobs.tests.factories import ConcernFactory, JobCardFactory
from apps.vehicles.models import Car, Colour
from apps.vehicles.services import car_brand_for, car_model_for
from apps.vehicles.tests.factories import CarFactory

pytestmark = pytest.mark.django_db

VIN = "WBA8E9C50GK123456"
OTHER_VIN = "WBA8E9C50GK654321"


def a_car(place, plate, brand="BMW", model="520d", **values):
    """A car of this workshop, on its lists of brands and models."""
    workshop = place[0]
    on_the_list = car_model_for(workshop, car_brand_for(workshop, brand), model)
    return CarFactory(workshop=workshop, plate=plate, car_model=on_the_list, **values)


def visit(place, car, plate=None, **values):
    return a_visit(place[0], car, plate, **values)


def cars(place):
    return Car.objects.for_workshop(place[0])


def again(car):
    return Car.objects.get(pk=car.pk)


def numbers_used(place):
    counter = NumberCounter.objects.for_workshop(place[0]).first()
    return counter.last_number if counter else 0


# JOB-14: a plate typed on a new card finds its car, and what was typed is the car in front of
# you.


def test_job_14_what_was_typed_replaces_what_the_record_says(place):
    known = a_car(place, "KL10AA1000", chassis_code="F30")

    card = make(place, plate="KL10AA1000", chassis_code="G20", car_model="530d")

    assert card.car == known
    assert (again(known).chassis_code, again(known).name) == ("G20", "BMW 530d")


def test_job_14_a_box_left_empty_changes_nothing(place):
    known = a_car(
        place,
        "KL10AA1000",
        chassis_code="F30",
        vin=VIN,
        colour=Colour.OTHER,
        colour_other="#7f1d1d",
    )

    make(place, plate="KL10AA1000", chassis_code="", vin="", colour="", colour_other="")

    known.refresh_from_db()
    assert (known.chassis_code, known.vin) == ("F30", VIN)
    assert (known.colour, known.colour_other) == (Colour.OTHER, "#7f1d1d")


# KNOWN-1 and KNOWN-2: a plate finds its car, by its plate today or an old one.


def test_known_1_an_old_plate_always_asks_even_with_the_same_brand(place):
    car = a_car(place, "KL10AA1000")
    visit(place, car, plate="KA01AB1234")

    with pytest.raises(Question) as asked:
        make(place, plate="KA01AB1234")

    assert (asked.value.kind, asked.value.car, asked.value.old) == ("brand", car, True)
    assert again(car).plate == "KL10AA1000"


def test_known_1_an_old_plate_of_the_same_car_is_its_plate_again(place):
    car = a_car(place, "KL10AA1000")
    earlier = visit(place, car, plate="KA01AB1234")

    card = make(place, plate="ka 01 ab 1234", answers={said("brand", "same", car)})

    assert card.car == car
    assert again(car).plate == "KA01AB1234"
    assert fresh(earlier).plate == "KA01AB1234"
    assert cars(place).count() == 1


def test_known_1_a_plate_today_comes_before_an_old_one(place):
    had_it = a_car(place, "KL10AA1000")
    visit(place, had_it, plate="KA01AB1234")
    has_it = a_car(place, "KA01AB1234")

    assert make(place, plate="KA01AB1234").car == has_it


def test_known_1_the_newest_card_with_an_old_plate_names_the_car(place):
    first = a_car(place, "KL10AA1000")
    second = a_car(place, "KL10AA2000")
    visit(place, first, plate="KA01AB1234", days_ago=90)
    visit(place, second, plate="KA01AB1234", days_ago=10)

    with pytest.raises(Question) as asked:
        make(place, plate="KA01AB1234")

    assert asked.value.car == second


@pytest.mark.parametrize("plate", ["KL10AA1000", "KA01AB1234"])
def test_known_2_the_fill_and_the_save_find_the_same_car(place, plate):
    car = a_car(place, "KL10AA1000")
    visit(place, car, plate="KA01AB1234")

    known = known_car(place[0], plate, with_customer=False)
    card = make(place, plate=plate, answers={said("brand", "same", car)})

    assert known.car == card.car == car


# KNOWN-10: a known plate with another brand, or an old plate, asks first.


def test_known_10_another_brand_asks_first_and_saves_nothing(place):
    toyota = a_car(place, "KL10AA1000", brand="Toyota", model="Innova")

    with pytest.raises(Question) as asked:
        make(place, plate="KL10AA1000")

    assert (asked.value.kind, asked.value.car, asked.value.plate) == ("brand", toyota, "KL10AA1000")
    assert asked.value.old is False
    assert not JobCard.objects.for_workshop(place[0]).exists()
    assert again(toyota).name == "Toyota Innova"
    assert numbers_used(place) == 0


def test_known_10_the_same_brand_in_other_capitals_asks_nothing(place):
    bmw = a_car(place, "KL10AA1000")

    assert make(place, plate="KL10AA1000", brand="bmw").car == bmw


def test_known_10_same_car_takes_the_brand_and_model_typed(place):
    toyota = a_car(place, "KL10AA1000", brand="Toyota", model="Innova")

    card = make(place, plate="KL10AA1000", answers={said("brand", "same", toyota)})

    assert card.car == toyota
    assert again(toyota).name == "BMW 520d"


def test_known_10_another_car_takes_the_plate_and_the_other_keeps_its_visits(place):
    toyota = a_car(place, "KL10AA1000", brand="Toyota", model="Innova")
    earlier = visit(place, toyota)

    card = make(place, plate="KL10AA1000", answers={said("brand", "another", toyota)})

    assert card.car != toyota
    assert (card.car.plate, card.car.name) == ("KL10AA1000", "BMW 520d")
    assert again(toyota).plate == ""
    assert (fresh(earlier).car, fresh(earlier).plate) == (toyota, "KL10AA1000")


def test_known_10_another_car_takes_none_of_what_the_other_car_holds(place):
    # The fill wrote the Toyota's chassis code, VIN and colour, and the person typed over only
    # the brand and the model.
    toyota = a_car(
        place,
        "KL10AA1000",
        brand="Toyota",
        model="Innova",
        chassis_code="AN140",
        vin=VIN,
        colour=Colour.OTHER,
        colour_other="#7f1d1d",
    )

    card = make(
        place,
        plate="KL10AA1000",
        chassis_code="AN140",
        vin=VIN,
        colour=Colour.OTHER,
        colour_other="#7f1d1d",
        answers={said("brand", "another", toyota)},
    )

    new = again(card.car)
    assert (new.chassis_code, new.vin, new.colour, new.colour_other) == ("", "", "", "")
    assert again(toyota).vin == VIN


def test_known_10_another_car_keeps_what_was_typed_for_it(place):
    toyota = a_car(
        place, "KL10AA1000", brand="Toyota", model="Innova", chassis_code="AN140", vin=VIN
    )

    card = make(
        place,
        plate="KL10AA1000",
        chassis_code="G30",
        vin=OTHER_VIN,
        colour=Colour.RED,
        answers={said("brand", "another", toyota)},
    )

    new = again(card.car)
    assert (new.chassis_code, new.vin, new.colour) == ("G30", OTHER_VIN, Colour.RED)


def test_known_10_another_car_on_an_old_plate_takes_nothing_from_its_car(place):
    toyota = a_car(place, "KL10AA2000", brand="Toyota", model="Innova")
    visit(place, toyota, plate="KL10AA1000")

    card = make(place, plate="KL10AA1000", answers={said("brand", "another", toyota)})

    assert card.car != toyota
    assert again(toyota).plate == "KL10AA2000"


def test_known_10_a_car_with_that_plate_today_and_an_open_card_is_refused_first(place):
    toyota = a_car(place, "KL10AA1000", brand="Toyota", model="Innova")
    open_card = JobCardFactory(workshop=place[0], car=toyota)

    with pytest.raises(CarHasOpenCard) as refused:
        make(place, plate="KL10AA1000", answers={said("brand", "another", toyota)})

    assert refused.value.card == open_card
    assert again(toyota).plate == "KL10AA1000"


def test_known_10_an_old_plate_of_a_car_with_an_open_card_asks_and_another_car_is_free(place):
    audi = a_car(place, "KL10AA2000", brand="Audi", model="A4")
    visit(place, audi, plate="KL10AA1000")
    open_card = JobCardFactory(workshop=place[0], car=audi)

    with pytest.raises(Question):
        make(place, plate="KL10AA1000")
    with pytest.raises(CarHasOpenCard) as refused:
        make(place, plate="KL10AA1000", answers={said("brand", "same", audi)})
    card = make(place, plate="KL10AA1000", answers={said("brand", "another", audi)})

    assert refused.value.card == open_card
    assert (card.car.plate, again(audi).plate) == ("KL10AA1000", "KL10AA2000")


# KNOWN-11: a VIN saved on another car asks first.


def test_known_11_a_vin_on_a_car_of_the_same_brand_asks_whether_it_is_that_car(place):
    bmw = a_car(place, "KA01AB1234", vin=VIN)
    visit(place, bmw)

    with pytest.raises(Question) as asked:
        make(place, plate="KL10AA1000", vin=VIN)

    assert (asked.value.kind, asked.value.car, asked.value.same) == ("vin", bmw, True)
    assert asked.value.last_in == timezone.localdate() - timedelta(days=30)
    assert numbers_used(place) == 0


def test_known_11_same_car_puts_the_card_on_it_with_its_new_plate(place):
    bmw = a_car(place, "KA01AB1234", vin=VIN)
    earlier = visit(place, bmw)

    card = make(place, plate="KL10AA1000", vin=VIN, answers={said("vin", "same", bmw)})

    assert card.car == bmw
    assert (card.plate, again(bmw).plate) == ("KL10AA1000", "KL10AA1000")
    assert fresh(earlier).plate == "KA01AB1234"
    assert cars(place).count() == 1


def test_known_11_another_car_keeps_the_vin_and_the_other_car_is_asked_again(place):
    bmw = a_car(place, "KA01AB1234", vin=VIN)

    card = make(place, plate="KL10AA1000", vin=VIN, answers={said("vin", "keep", bmw)})

    assert card.car != bmw
    assert again(card.car).vin == VIN
    assert again(bmw).vin == ""


def test_known_11_another_brand_only_asks_to_check_the_vin(place):
    toyota = a_car(place, "KA01AB1234", brand="Toyota", model="Innova", vin=VIN)

    with pytest.raises(Question) as asked:
        make(place, plate="KL10AA1000", vin=VIN, answers={said("vin", "same", toyota)})

    assert (asked.value.kind, asked.value.same) == ("vin", False)


def test_known_11_a_car_found_by_its_plate_is_never_joined_to_another(place):
    bmw = a_car(place, "KL10AA1000")
    other = a_car(place, "KA01AB1234", vin=VIN)

    with pytest.raises(Question) as asked:
        make(place, plate="KL10AA1000", vin=VIN, answers={said("vin", "same", other)})

    assert (asked.value.car, asked.value.same) == (other, False)
    card = make(place, plate="KL10AA1000", vin=VIN, answers={said("vin", "keep", other)})
    assert card.car == bmw
    assert (again(bmw).vin, again(other).vin) == (VIN, "")


def test_known_11_a_cars_own_vin_typed_again_on_a_card_that_leaves_it_is_asked(place):
    # Typed in groups, so the box changed, and "another car" has already been answered. The
    # car's open card is this very card, so nothing is refused.
    card = make(place, plate="KL10AA1000", vin=VIN)
    first = card.car
    visit(place, first)
    another = said("plate", "another", first)
    changes = {"plate": "KL10AA1001", "vin": VIN}

    with pytest.raises(Question) as asked:
        change(place, card, changes=changes, answers={another})
    assert (asked.value.kind, asked.value.car, asked.value.same) == ("vin", first, True)

    change(place, card, changes=changes, answers={another, said("vin", "keep", first)})

    moved = fresh(card).car
    assert moved != first
    assert (moved.plate, moved.vin) == ("KL10AA1001", VIN)
    assert (again(first).plate, again(first).vin) == ("KL10AA1000", "")


def test_known_11_same_car_keeps_the_card_on_it_with_the_new_plate(place):
    card = make(place, plate="KL10AA1000", vin=VIN)
    first = card.car
    visit(place, first)

    change(
        place,
        card,
        changes={"plate": "KL10AA1001", "vin": VIN},
        answers={said("plate", "another", first), said("vin", "same", first)},
    )

    assert fresh(card).car == first
    assert (again(first).plate, again(first).vin) == ("KL10AA1001", VIN)


def test_known_11_a_vin_a_move_brings_asks_about_the_car_that_holds_it(place):
    target = a_car(place, "KL10AB2000", brand="Audi", model="A4")
    visit(place, target)
    holder = a_car(place, "KA01AB1234", vin=VIN)
    card = make(place, plate="KL10AA1000")
    move = said("move", "move", target)
    changes = {"plate": "KL10AB2000", "vin": VIN}

    with pytest.raises(Question) as asked:
        change(place, card, changes=changes, answers={move})
    assert (asked.value.kind, asked.value.car, asked.value.same) == ("vin", holder, False)

    change(place, card, changes=changes, answers={move, said("vin", "keep", holder)})

    assert fresh(card).car == target
    assert (again(target).vin, again(holder).vin) == (VIN, "")


def test_known_11_a_vin_that_stays_behind_on_a_move_asks_nothing(place):
    # The car the card moves onto keeps its own VIN, so the typed one goes nowhere.
    target = a_car(place, "KL10AB2000", brand="Audi", model="A4", vin=OTHER_VIN)
    visit(place, target)
    holder = a_car(place, "KA01AB1234", vin=VIN)
    card = make(place, plate="KL10AA1000")

    change(
        place,
        card,
        changes={"plate": "KL10AB2000", "vin": VIN},
        answers={said("move", "move", target)},
    )

    assert fresh(card).car == target
    assert (again(target).vin, again(holder).vin) == (OTHER_VIN, VIN)


# KNOWN-12: nothing is taken from a car with an open job card.


def test_known_12_a_vin_is_never_taken_from_a_car_with_an_open_card(place):
    other = a_car(place, "KA01AB1234", vin=VIN)
    open_card = JobCardFactory(workshop=place[0], car=other)

    with pytest.raises(CarHasOpenCard) as refused:
        make(place, plate="KL10AA1000", vin=VIN, answers={said("vin", "keep", other)})

    assert (refused.value.card, refused.value.box) == (open_card, "vin")
    assert refused.value.message_dict == {
        "vin": [
            f"This VIN is on BMW 520d, KA01AB1234, which has an open job card, {open_card.number}."
        ]
    }
    assert again(other).vin == VIN


def test_known_12_a_move_never_brings_a_vin_from_a_car_with_an_open_card(place):
    target = a_car(place, "KL10AB2000", brand="Audi", model="A4")
    visit(place, target)
    holder = a_car(place, "KA01AB1234", vin=VIN)
    open_card = JobCardFactory(workshop=place[0], car=holder)
    card = make(place, plate="KL10AA1000")

    with pytest.raises(CarHasOpenCard) as refused:
        change(
            place,
            card,
            changes={"plate": "KL10AB2000", "vin": VIN},
            answers={said("move", "move", target), said("vin", "keep", holder)},
        )

    assert (refused.value.card, refused.value.box) == (open_card, "vin")
    assert again(holder).vin == VIN


# KNOWN-13: one question at a time, each about one car.


def test_known_13_an_answer_about_another_car_is_no_answer(place):
    a_car(place, "KL10AA1000", brand="Toyota", model="Innova")

    with pytest.raises(Question):
        make(place, plate="KL10AA1000", answers={f"brand:same:{uuid.uuid7()}"})


def test_known_13_a_made_up_answer_is_no_answer(place):
    toyota = a_car(place, "KL10AA1000", brand="Toyota", model="Innova")

    with pytest.raises(Question):
        make(place, plate="KL10AA1000", answers={f"brand:maybe:{toyota.pk}", "nonsense", ""})


def test_known_13_two_questions_come_one_at_a_time_and_an_answer_stays(place):
    toyota = a_car(place, "KL10AA1000", brand="Toyota", model="Innova")
    bmw = a_car(place, "KA01AB1234", vin=VIN)
    first = said("brand", "another", toyota)

    with pytest.raises(Question) as asked:
        make(place, plate="KL10AA1000", vin=VIN, answers={first})
    assert (asked.value.kind, asked.value.car, asked.value.same) == ("vin", bmw, True)

    card = make(place, plate="KL10AA1000", vin=VIN, answers={first, said("vin", "same", bmw)})

    assert card.car == bmw
    assert (again(bmw).plate, again(toyota).plate) == ("KL10AA1000", "")


def test_known_13_a_question_uses_no_number(place):
    a_car(place, "KL10AA1000", brand="Toyota", model="Innova")
    with pytest.raises(Question):
        make(place, plate="KL10AA1000")

    assert make(place, plate="KL10AA2000").number == "JC-0001"


# KNOWN-14: a plate that names another car moves the card there.


def test_known_14_move_puts_the_card_on_that_car_with_everything_on_it(place):
    audi = a_car(place, "KL10AB2000", brand="Audi", model="A4")
    visit(place, audi)
    card = make(place, plate="KL10AA1000")
    made_with_it = card.car
    ConcernFactory(workshop=place[0], job_card=card, text="Brake noise")

    change(place, card, changes={"plate": "KL10AB2000"}, answers={said("move", "move", audi)})

    card = fresh(card)
    assert (card.car, card.plate) == (audi, "KL10AB2000")
    assert card.number == "JC-0001"
    assert [row.text for row in card.concerns.all()] == ["Brake noise"]
    assert [step.kind for step in card.steps.all()] == [StepKind.CAR_IN]
    # KNOWN-16: the car this card made by mistake had nothing else, so it went.
    assert not Car.objects.filter(pk=made_with_it.pk).exists()


def test_known_14_a_move_puts_nothing_else_typed_on_that_car(place):
    audi = a_car(
        place, "KL10AB2000", brand="Audi", model="A4", chassis_code="B8", vin=VIN, colour="red"
    )
    visit(place, audi)
    card = make(place, plate="KL10AA1000", chassis_code="G30", vin=OTHER_VIN, colour="blue")
    visit(place, card.car)

    change(
        place,
        card,
        changes={"plate": "KL10AB2000", "car_model": "530d", "vin": "", "chassis_code": ""},
        answers={said("move", "move", audi)},
    )

    audi = again(audi)
    assert fresh(card).car == audi
    assert (audi.name, audi.chassis_code, audi.vin, audi.colour) == ("Audi A4", "B8", VIN, "red")


def test_known_14_an_old_plate_of_another_car_moves_there_and_is_its_plate_again(place):
    audi = a_car(place, "KL10AB2000", brand="Audi", model="A4")
    visit(place, audi, plate="KA01AB1234")
    card = make(place, plate="KL10AA1000")

    with pytest.raises(Question) as asked:
        change(place, card, changes={"plate": "KA01AB1234"})
    assert (asked.value.kind, asked.value.car, asked.value.old) == ("move", audi, True)

    change(place, card, changes={"plate": "KA01AB1234"}, answers={said("move", "move", audi)})

    assert fresh(card).car == audi
    assert again(audi).plate == "KA01AB1234"


def test_known_14_another_car_on_an_old_plate_keeps_the_card_where_it_is(place):
    audi = a_car(place, "KL10AB2000", brand="Audi", model="A4")
    visit(place, audi, plate="KA01AB1234")
    card = make(place, plate="KL10AA1000")
    first = card.car

    change(place, card, changes={"plate": "KA01AB1234"}, answers={said("move", "another", audi)})

    assert (fresh(card).car, fresh(card).plate) == (first, "KA01AB1234")
    assert again(first).plate == "KA01AB1234"
    assert again(audi).plate == "KL10AB2000"


def test_known_14_a_card_never_moves_onto_a_car_with_an_open_card(place):
    audi = a_car(place, "KL10AB2000", brand="Audi", model="A4")
    open_card = JobCardFactory(workshop=place[0], car=audi)
    card = make(place, plate="KL10AA1000")

    with pytest.raises(CarHasOpenCard) as refused:
        change(place, card, changes={"plate": "KL10AB2000"}, answers={said("move", "move", audi)})

    assert refused.value.card == open_card
    assert fresh(card).plate == "KL10AA1000"


def test_job_4_a_move_that_loses_a_race_is_refused_not_a_crash(place, monkeypatch):
    # Another send makes an open card for the car after this save has checked: the checks see
    # nothing, and only PostgreSQL's rule stops it.
    audi = a_car(place, "KL10AB2000", brand="Audi", model="A4")
    open_card = JobCardFactory(workshop=place[0], car=audi)
    card = make(place, plate="KL10AA1000")
    real = services.open_card_of
    calls = []

    def blind_at_first(workshop, car):
        calls.append(car)
        return None if len(calls) == 1 else real(workshop, car)

    monkeypatch.setattr(services, "open_card_of", blind_at_first)
    monkeypatch.setattr(JobCard, "full_clean", lambda self: None)

    with pytest.raises(CarHasOpenCard) as refused:
        change(place, card, changes={"plate": "KL10AB2000"}, answers={said("move", "move", audi)})

    assert refused.value.card == open_card


# Two saves at one moment: a save that waited for the card's lock sees what the first one did.


def until_a_save_waits():
    with connection.cursor() as cursor:
        for _try in range(500):
            cursor.execute(
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE datname = current_database() AND wait_event_type = 'Lock'"
            )
            if cursor.fetchone()[0]:
                return
            time.sleep(0.01)
    raise AssertionError("No save waited for the lock.")


def held_until_a_save_waits(first_save):
    """Runs a save on its own connection, and commits it only when another save waits for its
    lock, so the two meet the same way every time."""
    saved = threading.Event()

    def run():
        try:
            with transaction.atomic():
                first_save()
                saved.set()
                until_a_save_waits()
        finally:
            saved.set()
            connection.close()

    thread = threading.Thread(target=run)
    thread.start()
    saved.wait(timeout=10)
    return thread


@pytest.mark.django_db(transaction=True)
def test_job_43_a_save_that_waited_for_a_move_finds_the_card_on_its_new_car(place):
    audi = a_car(place, "KL10AB2000", brand="Audi", model="A4")
    visit(place, audi)
    card = make(place, plate="KL10AA1000")

    first = held_until_a_save_waits(
        lambda: change(
            place, card, changes={"plate": "KL10AB2000"}, answers={said("move", "move", audi)}
        )
    )
    change(place, card, changes={"note": "Brake noise"})
    first.join()

    card = fresh(card)
    assert (card.car, card.plate, card.note) == (audi, "KL10AB2000", "Brake noise")


@pytest.mark.django_db(transaction=True)
def test_job_43_a_save_that_waited_never_undoes_what_the_first_one_changed(place):
    card = make(place, plate="KL10AA1000")

    first = held_until_a_save_waits(lambda: change(place, card, changes={"plate": "KL10AA1001"}))
    change(place, card, changes={"colour": Colour.RED})
    first.join()

    card = fresh(card)
    assert (card.plate, card.car.plate, card.car.colour) == ("KL10AA1001", "KL10AA1001", Colour.RED)


# KNOWN-15: a plate that names no car.


def test_known_15_a_car_with_no_other_visit_takes_a_new_plate_with_no_question(place):
    card = make(place, plate="KL10AA1000")

    change(place, card, changes={"plate": "KL10AA1001"})

    assert fresh(card).car.plate == "KL10AA1001"


def test_known_15_a_car_with_another_visit_asks_whether_it_has_a_new_plate(place):
    card = make(place, plate="KL10AA1000")
    visit(place, card.car)

    with pytest.raises(Question) as asked:
        change(place, card, changes={"plate": "KL10AA1001"})

    assert (asked.value.kind, asked.value.car) == ("plate", card.car)
    assert fresh(card).plate == "KL10AA1000"


def test_known_15_a_plate_only_the_cars_own_old_card_came_with_is_no_move(place):
    card = make(place, plate="KL10AA1000")
    car = card.car
    visit(place, car, plate="KA01AB1234")

    with pytest.raises(Question) as asked:
        change(place, card, changes={"plate": "KA01AB1234"})

    assert (asked.value.kind, asked.value.car) == ("plate", car)


def test_known_15_another_car_moves_the_card_to_a_new_car(place):
    card = make(place, plate="KL10AA1000", vin=VIN, chassis_code="G30")
    first = card.car
    visit(place, first)

    change(place, card, changes={"plate": "KL10AA1001"}, answers={said("plate", "another", first)})

    moved = fresh(card).car
    assert moved != first
    assert (moved.plate, moved.name) == ("KL10AA1001", "BMW 520d")
    assert (again(first).plate, again(first).vin) == ("KL10AA1000", VIN)


# KNOWN-16: what a car made by a move takes, and what a car a move leaves gives.


def test_known_16_a_new_car_takes_only_what_was_typed(place):
    card = make(place, plate="KL10AA1000", vin=VIN, chassis_code="G30", colour="red")
    first = card.car
    visit(place, first)

    change(
        place,
        card,
        changes={"plate": "KL10AA1001", "chassis_code": "F10"},
        answers={said("plate", "another", first)},
    )

    moved = fresh(card).car
    assert (moved.chassis_code, moved.vin, moved.colour) == ("F10", "", "")


def test_known_16_a_car_a_move_leaves_alone_gives_what_it_holds_to_the_empty_boxes(place):
    target = a_car(place, "KL10AB2000", brand="Audi", model="A4")
    visit(place, target)
    card = make(
        place,
        plate="KL10AA1000",
        vin=VIN,
        chassis_code="G30",
        colour=Colour.OTHER,
        colour_other="#7f1d1d",
    )

    change(place, card, changes={"plate": "KL10AB2000"}, answers={said("move", "move", target)})

    target = again(target)
    assert (target.vin, target.chassis_code) == (VIN, "G30")
    assert (target.colour, target.colour_other) == (Colour.OTHER, "#7f1d1d")


def test_known_16_it_never_writes_over_what_the_car_holds(place):
    target = a_car(
        place,
        "KL10AB2000",
        brand="Audi",
        model="A4",
        vin=OTHER_VIN,
        chassis_code="B8",
        colour="red",
    )
    visit(place, target)
    card = make(place, plate="KL10AA1000", vin=VIN, chassis_code="G30", colour="blue")

    change(place, card, changes={"plate": "KL10AB2000"}, answers={said("move", "move", target)})

    target = again(target)
    assert (target.vin, target.chassis_code, target.colour) == (OTHER_VIN, "B8", "red")


def test_known_16_a_car_with_other_visits_stays_and_gives_nothing(place):
    audi = a_car(place, "KL10AB2000", brand="Audi", model="A4")
    bmw = a_car(place, "KL10AA1000", vin=VIN, chassis_code="G30")
    visit(place, bmw)
    card = make(place, plate="KL10AA1000")

    change(place, card, changes={"plate": "KL10AB2000"}, answers={said("move", "move", audi)})

    assert fresh(card).car == audi
    assert (again(bmw).plate, again(bmw).vin) == ("KL10AA1000", VIN)
    assert (again(audi).vin, again(audi).chassis_code) == ("", "")


# KNOWN-10 on a saved card: another brand on a car with other visits.


def test_known_10_a_brand_change_on_a_lone_car_asks_nothing(place):
    card = make(place)

    change(place, card, changes={"brand": "Toyota"})

    assert fresh(card).car.name == "Toyota 520d"


def test_known_10_a_brand_change_on_a_car_with_visits_asks(place):
    card = make(place)
    visit(place, card.car)

    with pytest.raises(Question) as asked:
        change(place, card, changes={"brand": "Toyota"})

    assert (asked.value.kind, asked.value.car) == ("brand", card.car)


def test_known_10_same_car_changes_the_brand_of_a_car_with_visits(place):
    card = make(place)
    visit(place, card.car)

    change(place, card, changes={"brand": "Toyota"}, answers={said("brand", "same", card.car)})

    assert fresh(card).car.name == "Toyota 520d"


def test_known_10_another_car_moves_the_card_and_takes_the_plate(place):
    card = make(place, plate="KL10AA1000")
    first = card.car
    earlier = visit(place, first)

    change(place, card, changes={"brand": "Toyota"}, answers={said("brand", "another", first)})

    moved = fresh(card).car
    assert moved != first
    assert (moved.plate, moved.name) == ("KL10AA1000", "Toyota 520d")
    assert again(first).plate == ""
    assert fresh(earlier).car == first


# KNOWN-11 on a saved card.


def test_known_11_a_lone_card_moves_to_the_car_its_vin_names(place):
    bmw = a_car(place, "KA01AB1234", vin=VIN)
    visit(place, bmw)
    card = make(place, plate="KL10AA1000")
    made_with_it = card.car

    with pytest.raises(Question) as asked:
        change(place, card, changes={"vin": VIN})
    assert (asked.value.kind, asked.value.car, asked.value.same) == ("vin", bmw, True)

    change(place, card, changes={"vin": VIN}, answers={said("vin", "same", bmw)})

    assert fresh(card).car == bmw
    assert again(bmw).plate == "KL10AA1000"
    assert not Car.objects.filter(pk=made_with_it.pk).exists()


def test_known_11_a_car_with_visits_only_checks_the_vin(place):
    other = a_car(place, "KA01AB1234", vin=VIN)
    card = make(place, plate="KL10AA1000")
    visit(place, card.car)

    with pytest.raises(Question) as asked:
        change(place, card, changes={"vin": VIN})
    assert asked.value.same is False

    change(place, card, changes={"vin": VIN}, answers={said("vin", "keep", other)})

    assert (fresh(card).car.vin, again(other).vin) == (VIN, "")


# KNOWN-17: a cancelled card never moves.


def test_known_17_a_cancelled_card_never_moves(place):
    audi = a_car(place, "KL10AB2000", brand="Audi", model="A4")
    card = JobCardFactory(
        workshop=place[0], status=JobCardStatus.CANCELLED, cancel_reason="Customer left"
    )

    with pytest.raises(ValidationError, match="cancelled"):
        change(place, card, changes={"plate": "KL10AB2000"}, answers={said("move", "move", audi)})

    assert fresh(card).car != audi

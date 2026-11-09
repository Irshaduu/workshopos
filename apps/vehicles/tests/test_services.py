"""Finding and changing cars and customers (apps/vehicles/services.py)."""

import threading

import pytest
from django.core.exceptions import ValidationError
from django.db import connection, models

from apps.vehicles.models import Car, CarBrand, CarModel, Colour, Customer
from apps.vehicles.services import (
    car_brand_for,
    car_model_for,
    change_car,
    customer_for,
    empty_plate,
    empty_vin,
    new_car,
    remove_if_unused,
)
from apps.vehicles.tests.factories import (
    CarBrandFactory,
    CarFactory,
    CarModelFactory,
    CustomerFactory,
)
from apps.workshops.tests.factories import WorkshopFactory

pytestmark = pytest.mark.django_db

GOOD_VIN = "WBA8E9C50GK123456"


def errors_of(refused):
    return {box: " ".join(words) for box, words in refused.value.message_dict.items()}


# The lists.


def test_job_17_a_typed_word_finds_its_entry_and_the_lists_spelling_wins():
    brand = CarBrandFactory(name="BMW")

    assert car_brand_for(brand.workshop, "bmw") == brand
    assert car_brand_for(brand.workshop, "  BmW ") == brand


def test_job_17_a_new_brand_joins_the_list_tidied_like_a_name():
    workshop = WorkshopFactory()

    assert car_brand_for(workshop, "land  rover").name == "Land Rover"
    assert car_brand_for(workshop, "BYD").name == "BYD"
    assert CarBrand.objects.for_workshop(workshop).count() == 2


def test_job_17_another_workshops_list_is_never_touched():
    theirs = CarBrandFactory(name="BMW")
    ours = WorkshopFactory()

    assert car_brand_for(ours, "BMW") != theirs
    assert CarBrand.objects.for_workshop(theirs.workshop).count() == 1


def test_job_17_a_new_model_keeps_its_shape_under_its_brand():
    brand = CarBrandFactory()

    assert car_model_for(brand.workshop, brand, " CR-V ").name == "CR-V"
    assert car_model_for(brand.workshop, brand, "cr-v").name == "CR-V"
    assert CarModel.objects.for_workshop(brand.workshop).count() == 1


def test_job_17_a_word_too_long_for_the_list_is_refused_not_cut():
    with pytest.raises(ValidationError):
        car_brand_for(WorkshopFactory(), "x" * 101)


@pytest.mark.django_db(transaction=True)
def test_job_17_two_sends_at_one_moment_make_one_entry():
    workshop = WorkshopFactory()
    barrier = threading.Barrier(2)
    found = []

    def send():
        barrier.wait()
        try:
            found.append(car_brand_for(workshop, "Porsche"))
        finally:
            connection.close()

    threads = [threading.Thread(target=send) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(found) == 2
    assert found[0] == found[1]
    assert CarBrand.objects.for_workshop(workshop).count() == 1


# A new car, and what another car gives up for the car in front of you.


def test_job_14_a_new_car_finds_its_brand_and_model_on_their_lists():
    brand = CarBrandFactory(name="BMW")
    workshop = brand.workshop

    car = new_car(workshop, "kl-10 aa 1000", "bmw", "520d")
    change_car(workshop, car, {"chassis_code": "f 30", "vin": GOOD_VIN, "colour": Colour.RED})

    car = Car.objects.get(pk=car.pk)
    assert car.plate == "KL10AA1000"
    assert car.car_model.brand == brand
    assert car.name == "BMW 520d"
    assert (car.chassis_code, car.vin, car.colour) == ("F30", GOOD_VIN, Colour.RED)


def test_known_3_a_car_that_gave_up_its_plate_keeps_everything_else():
    car = CarFactory(plate="KL10AA1000", vin=GOOD_VIN)

    empty_plate(car.workshop, car)

    car.refresh_from_db()
    assert (car.plate, car.vin) == ("", GOOD_VIN)


def test_known_11_a_car_that_gave_up_its_vin_keeps_everything_else():
    car = CarFactory(plate="KL10AA1000", vin=GOOD_VIN)

    empty_vin(car.workshop, car)

    car.refresh_from_db()
    assert (car.plate, car.vin) == ("KL10AA1000", "")


def test_known_16_a_car_nothing_holds_is_removed():
    car = CarFactory()

    remove_if_unused(car.workshop, car)

    assert not Car.objects.filter(pk=car.pk).exists()


def test_known_16_another_workshop_never_removes_or_empties_a_car():
    car = CarFactory(plate="KL10AA1000", vin=GOOD_VIN)
    other = WorkshopFactory()

    remove_if_unused(other, car)
    empty_plate(other, Car.objects.get(pk=car.pk))
    empty_vin(other, Car.objects.get(pk=car.pk))

    assert (Car.objects.get(pk=car.pk).plate, Car.objects.get(pk=car.pk).vin) == (
        "KL10AA1000",
        GOOD_VIN,
    )


def test_known_16_every_link_to_a_car_refuses_its_delete():
    # remove_if_unused trusts this: a link that lets a car go would lose its rows with no error.
    links = [link for link in Car._meta.related_objects if link.on_delete is not None]

    assert links
    assert {link.on_delete for link in links} == {models.PROTECT}


def test_job_16_a_car_is_never_saved_with_no_plate():
    workshop = WorkshopFactory()

    with pytest.raises(ValidationError) as refused:
        change_car(workshop, new_car(workshop, "", "BMW", "520d"), {})

    assert "plate" in errors_of(refused)
    assert not Car.objects.for_workshop(workshop).exists()


# Changing a car.


def test_job_12_only_what_changed_changes():
    car = CarFactory(chassis_code="F30")
    name = car.name

    change_car(car.workshop, car, {"vin": GOOD_VIN})

    car.refresh_from_db()
    assert (car.chassis_code, car.vin, car.name) == ("F30", GOOD_VIN, name)


def test_job_12_a_change_of_model_keeps_the_brand():
    car = CarFactory(car_model__brand__name="BMW", car_model__name="520d")

    change_car(car.workshop, car, {"car_model": "530d"})

    assert Car.objects.get(pk=car.pk).name == "BMW 530d"


def test_job_12_a_change_of_brand_keeps_the_models_word():
    car = CarFactory(car_model__brand__name="Toyta", car_model__name="Corolla")

    change_car(car.workshop, car, {"brand": "Toyota"})

    assert Car.objects.get(pk=car.pk).name == "Toyota Corolla"


def test_job_15_a_free_plate_becomes_the_cars_plate():
    car = CarFactory(plate="KL10AA1000")

    change_car(car.workshop, car, {"plate": "kl 10 ab 2000"})

    assert Car.objects.get(pk=car.pk).plate == "KL10AB2000"


def test_job_16_a_plate_is_never_put_on_two_cars_and_the_refusal_names_the_other():
    # The last guard, under the questions that come first (KNOWN-14).
    other = CarFactory(plate="KL10AA1000", car_model__brand__name="BMW", car_model__name="520d")
    car = CarFactory(workshop=other.workshop, plate="KL10AB2000")

    with pytest.raises(ValidationError) as refused:
        change_car(car.workshop, car, {"plate": "KL10AA1000"})

    assert errors_of(refused) == {"plate": "This plate is on another car, BMW 520d."}
    assert Car.objects.get(pk=car.pk).plate == "KL10AB2000"


def test_job_20_a_vin_is_never_put_on_two_cars_and_the_refusal_names_the_other():
    # The last guard, under the questions that come first (KNOWN-11).
    other = CarFactory(
        plate="KL10AA1000", vin=GOOD_VIN, car_model__brand__name="BMW", car_model__name="520d"
    )
    car = CarFactory(workshop=other.workshop)

    with pytest.raises(ValidationError) as refused:
        change_car(car.workshop, car, {"vin": GOOD_VIN.lower()})

    assert errors_of(refused) == {"vin": "This VIN is on another car, BMW 520d (KL10AA1000)."}


def test_job_20_a_car_keeps_its_own_vin():
    car = CarFactory(vin=GOOD_VIN)

    change_car(car.workshop, car, {"vin": GOOD_VIN, "chassis_code": "F30"})

    assert Car.objects.get(pk=car.pk).chassis_code == "F30"


def test_a_wrong_box_is_refused_in_plain_words_by_the_model():
    car = CarFactory()

    with pytest.raises(ValidationError):
        change_car(car.workshop, car, {"vin": "WBA"})


def test_a_model_of_this_workshop_only_is_used():
    theirs = CarModelFactory(brand__name="BMW", name="520d")
    car = CarFactory()

    change_car(car.workshop, car, {"brand": "BMW", "car_model": "520d"})

    assert Car.objects.get(pk=car.pk).car_model != theirs


# Customers.


def test_job_27_the_same_two_boxes_find_the_same_record():
    workshop = WorkshopFactory()

    first = customer_for(workshop, "arun k", "+91 90000 00001")

    assert first.name == "Arun K"
    assert first.contact_number == "9000000001"
    assert customer_for(workshop, "ARUN K", "9000000001") == first
    assert Customer.objects.for_workshop(workshop).count() == 1


def test_job_27_another_name_with_the_same_number_is_another_record():
    workshop = WorkshopFactory()

    arun = customer_for(workshop, "Arun", "9000000001")
    vijay = customer_for(workshop, "Vijay", "9000000001")

    assert arun != vijay
    arun.refresh_from_db()
    assert arun.name == "Arun"


def test_job_27_a_name_alone_or_a_number_alone_is_a_customer():
    workshop = WorkshopFactory()

    assert customer_for(workshop, "Arun", "").contact_number == ""
    assert customer_for(workshop, "", "9000000001").name == ""


def test_job_27_two_empty_boxes_are_no_customer():
    workshop = WorkshopFactory()

    assert customer_for(workshop, "", "") is None
    assert customer_for(workshop, "  ", " ") is None
    assert not Customer.objects.for_workshop(workshop).exists()


def test_job_27_another_workshops_customer_is_never_found():
    theirs = CustomerFactory(name="Arun", contact_number="9000000001")

    assert customer_for(WorkshopFactory(), "Arun", "9000000001") != theirs


def test_job_28_capitals_typed_on_purpose_correct_the_record():
    customer = CustomerFactory(name="Arun Kp", contact_number="9000000001")

    found = customer_for(customer.workshop, "Arun KP", "9000000001")

    assert found == customer
    customer.refresh_from_db()
    assert customer.name == "Arun KP"


def test_job_28_no_capitals_typed_never_undo_them():
    customer = CustomerFactory(name="Arun KP", contact_number="9000000001")

    customer_for(customer.workshop, "arun kp", "9000000001")

    customer.refresh_from_db()
    assert customer.name == "Arun KP"


def test_job_30_a_wrong_number_is_refused():
    with pytest.raises(ValidationError):
        customer_for(WorkshopFactory(), "Arun", "abc")

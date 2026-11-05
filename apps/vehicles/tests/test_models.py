"""What a car and a customer may hold, by the tidy steps and by PostgreSQL itself
(apps/vehicles/models.py). The examples come from v1's tests."""

import pytest
from django.db import IntegrityError, connection, transaction

from apps.vehicles.models import (
    Car,
    CarBrand,
    CarModel,
    Colour,
    Customer,
    contact_number_problem,
    plate_problem,
    tidy_chassis_code,
    tidy_contact_number,
    tidy_plate,
    tidy_vin,
    vin_problem,
)
from apps.vehicles.tests.factories import (
    CarBrandFactory,
    CarFactory,
    CarModelFactory,
    CustomerFactory,
)
from apps.workshops.tests.factories import WorkshopFactory

GOOD_VIN = "WBA8E9C50GK123456"


def refused_by_postgresql(make):
    """Asks at once for the checks that wait for the end of the transaction, like a link's."""
    with pytest.raises(IntegrityError), transaction.atomic():
        make()
        connection.check_constraints()


# The plate.


@pytest.mark.parametrize(
    ("typed", "saved"),
    [
        ("kl-10 aa 1000", "KL10AA1000"),
        ("KL 10 AA 1000", "KL10AA1000"),
        ("KL10AA1000", "KL10AA1000"),
        (" kl.10/aa 1000 ", "KL10AA1000"),
        ("22BH1234AA", "22BH1234AA"),
        ("UAE 12345", "UAE12345"),
    ],
)
def test_job_16_a_plate_has_one_spelling(typed, saved):
    assert tidy_plate(typed) == saved
    assert not plate_problem(tidy_plate(typed))


@pytest.mark.parametrize("plate", ["", "KL10@1000", "കെഎൽ10", "A" * 21])
def test_job_16_anything_but_letters_and_digits_is_refused(plate):
    assert plate_problem(plate)


def test_job_16_a_vin_fits_in_the_plate_box_for_a_car_with_no_plate_yet():
    assert not plate_problem(GOOD_VIN)


@pytest.mark.django_db
@pytest.mark.parametrize("plate", ["KL 10", "kl10", "", "KL-10"])
def test_job_16_postgresql_holds_the_plates_form(plate):
    refused_by_postgresql(lambda: CarFactory(plate=plate))


@pytest.mark.django_db
def test_job_16_a_plate_belongs_to_one_car_in_a_workshop():
    workshop = WorkshopFactory()
    CarFactory(workshop=workshop, plate="KL10AA1000")

    refused_by_postgresql(lambda: CarFactory(workshop=workshop, plate="KL10AA1000"))


@pytest.mark.django_db
def test_job_11_the_same_plate_in_another_workshop_is_another_car():
    CarFactory(plate="KL10AA1000")
    CarFactory(plate="KL10AA1000")

    assert Car.objects.filter(plate="KL10AA1000").count() == 2


# The brand and the model.


@pytest.mark.django_db
def test_job_17_one_brand_per_workshop_whatever_the_capitals():
    workshop = WorkshopFactory()
    CarBrandFactory(workshop=workshop, name="BMW")

    refused_by_postgresql(lambda: CarBrandFactory(workshop=workshop, name="bmw"))
    assert CarBrandFactory(name="bmw").name == "bmw"


@pytest.mark.django_db
def test_job_17_one_model_per_brand_whatever_the_capitals():
    brand = CarBrandFactory(name="Toyota")
    CarModelFactory(workshop=brand.workshop, brand=brand, name="Corolla")

    refused_by_postgresql(
        lambda: CarModelFactory(workshop=brand.workshop, brand=brand, name="COROLLA")
    )


@pytest.mark.django_db
def test_job_17_the_same_model_under_another_brand_is_another_model():
    workshop = WorkshopFactory()
    one = CarModelFactory(workshop=workshop, name="Corolla")
    other = CarModelFactory(workshop=workshop, name="Corolla")

    assert one.brand != other.brand


@pytest.mark.django_db
def test_job_17_a_blank_brand_or_model_is_refused():
    refused_by_postgresql(lambda: CarBrandFactory(name="  "))
    refused_by_postgresql(lambda: CarModelFactory(name=""))


@pytest.mark.django_db
def test_job_17_a_model_keeps_its_own_shape_and_a_brand_is_tidied_like_a_name():
    brand = CarBrand(workshop=WorkshopFactory(), name="  land   rover ")
    car_model = CarModel(workshop=brand.workshop, brand=brand, name="  CR-V  i20 ")

    brand.clean()
    car_model.clean()

    assert brand.name == "Land Rover"
    assert car_model.name == "CR-V i20"


@pytest.mark.django_db
def test_a_model_of_another_workshops_brand_is_refused():
    theirs = CarBrandFactory()

    refused_by_postgresql(lambda: CarModelFactory(workshop=WorkshopFactory(), brand=theirs))


# The chassis code.


@pytest.mark.parametrize(
    ("typed", "saved"),
    [("f 30", "F30"), ("991.2", "991.2"), ("L494", "L494"), ("  w205 ", "W205")],
)
def test_job_18_a_chassis_code_loses_its_spaces_and_keeps_real_characters(typed, saved):
    assert tidy_chassis_code(typed) == saved


@pytest.mark.django_db
@pytest.mark.parametrize("code", ["f30", "F 30"])
def test_job_18_postgresql_holds_the_chassis_codes_form(code):
    refused_by_postgresql(lambda: CarFactory(chassis_code=code))


# The VIN.


def test_job_19_a_vin_typed_in_groups_is_one_vin():
    assert tidy_vin("wba 8e9c-50gk 123456") == GOOD_VIN


def test_job_19_a_real_european_vin_passes_because_there_is_no_check_digit_test():
    assert not vin_problem(GOOD_VIN)
    assert not vin_problem("")


@pytest.mark.parametrize(
    ("vin", "words"),
    [
        ("WBA8E9C50GK", "this one has 11"),
        ("WBA8E9C50GK1234567", "this one has 18"),
        ("WBA8E9C50GK12345I", "never uses the letters"),
        ("WBA8E9C50GK12345O", "never uses the letters"),
        ("WBA8E9C50GK12345Q", "never uses the letters"),
        ("WBA8E9C50GK12345.", "letters and digits only"),
    ],
)
def test_job_19_each_slip_is_refused_with_its_rule(vin, words):
    assert words in str(vin_problem(vin))


@pytest.mark.django_db
@pytest.mark.parametrize("vin", ["WBA8E9C50GK", "WBA8E9C50GK12345I", "wba8e9c50gk123456"])
def test_job_19_postgresql_holds_the_vins_form(vin):
    refused_by_postgresql(lambda: CarFactory(vin=vin))


@pytest.mark.django_db
def test_job_20_a_vin_belongs_to_one_car_in_a_workshop():
    workshop = WorkshopFactory()
    CarFactory(workshop=workshop, vin=GOOD_VIN)

    refused_by_postgresql(lambda: CarFactory(workshop=workshop, vin=GOOD_VIN))


@pytest.mark.django_db
def test_job_20_many_cars_may_have_no_vin():
    workshop = WorkshopFactory()

    CarFactory(workshop=workshop)
    CarFactory(workshop=workshop)


# The colour.


@pytest.mark.django_db
def test_job_21_a_colour_is_from_the_list():
    refused_by_postgresql(lambda: CarFactory(colour="purple"))
    assert CarFactory(colour=Colour.LIGHT_BLUE).paint == "light-blue"


@pytest.mark.django_db
def test_job_21_no_colour_has_its_own_paint_never_grey():
    assert CarFactory().paint == "unset"


@pytest.mark.django_db
def test_job_21_other_has_its_own_colour_and_nothing_else_has_one():
    assert CarFactory(colour=Colour.OTHER, colour_other="#7f1d1d").paint == "other"

    refused_by_postgresql(lambda: CarFactory(colour=Colour.OTHER))
    refused_by_postgresql(lambda: CarFactory(colour=Colour.OTHER, colour_other="red"))
    refused_by_postgresql(lambda: CarFactory(colour=Colour.RED, colour_other="#7f1d1d"))


# The customer.


@pytest.mark.parametrize(
    ("typed", "saved"),
    [
        ("9000000001", "9000000001"),
        ("09000000001", "09000000001"),
        ("080 40000001", "08040000001"),
        ("+91 90000 00001", "9000000001"),
        ("91-9000000001", "9000000001"),
        ("(+91) 90000.00001", "9000000001"),
        ("+971 50 000 0001", "+971500000001"),
        ("0471 2000001", "04712000001"),
        ("", ""),
    ],
)
def test_job_30_a_number_has_one_spelling(typed, saved):
    assert tidy_contact_number(typed) == saved
    assert not contact_number_problem(tidy_contact_number(typed))


@pytest.mark.parametrize("number", ["abc", "98765x4321", "12345", "1234567890123456", "+"])
def test_job_30_letters_and_wrong_lengths_are_refused(number):
    assert contact_number_problem(number)


@pytest.mark.django_db
def test_job_27_a_customer_needs_a_name_or_a_number():
    refused_by_postgresql(lambda: CustomerFactory(name="", contact_number=""))

    assert CustomerFactory(name="Arun", contact_number="").name == "Arun"
    assert CustomerFactory(name="", contact_number="9000000001").contact_number


@pytest.mark.django_db
def test_job_27_one_record_per_name_and_number_whatever_the_capitals():
    workshop = WorkshopFactory()
    CustomerFactory(workshop=workshop, name="Arun", contact_number="9000000001")

    refused_by_postgresql(
        lambda: CustomerFactory(workshop=workshop, name="ARUN", contact_number="9000000001")
    )


@pytest.mark.django_db
def test_job_27_another_name_with_the_same_number_is_another_record():
    workshop = WorkshopFactory()
    CustomerFactory(workshop=workshop, name="Arun", contact_number="9000000001")
    CustomerFactory(workshop=workshop, name="Vijay", contact_number="9000000001")

    assert Customer.objects.for_workshop(workshop).count() == 2


@pytest.mark.django_db
def test_job_30_postgresql_holds_the_numbers_form():
    refused_by_postgresql(lambda: CustomerFactory(contact_number="90000 00001"))
    refused_by_postgresql(lambda: CustomerFactory(contact_number="123"))


@pytest.mark.django_db
def test_a_car_tidies_itself_for_a_service_with_no_form():
    car = CarFactory.build(
        workshop=WorkshopFactory(),
        plate="kl-10 aa 1000",
        chassis_code="f 30",
        vin="wba 8e9c-50gk 123456",
    )

    car.clean()

    assert (car.plate, car.chassis_code, car.vin) == ("KL10AA1000", "F30", GOOD_VIN)


@pytest.mark.django_db
def test_a_customer_tidies_itself_for_a_service_with_no_form():
    customer = Customer(workshop=WorkshopFactory(), name="anil KP", contact_number="+91 9000000001")

    customer.clean()

    assert (customer.name, customer.contact_number) == ("Anil KP", "9000000001")

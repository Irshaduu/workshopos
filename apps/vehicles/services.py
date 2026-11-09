"""Changes in vehicles: rules that change data (ADR-0005)."""

from contextlib import suppress

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils.translation import gettext as _

from apps.core.text import tidy_name, tidy_spaces
from apps.vehicles.models import (
    Car,
    CarBrand,
    CarModel,
    Customer,
    plate_problem,
    tidy_contact_number,
    tidy_plate,
)
from apps.vehicles.selectors import car_brand_named, car_with_plate, car_with_vin


def _saved_or_found(record, found):
    """Saves a new list entry or customer. If another send made the same one at this
    moment, PostgreSQL refuses this one, and the other is the answer."""
    try:
        record.full_clean()
        # Its own savepoint, so a refused save leaves a bigger transaction working.
        with transaction.atomic():
            record.save(force_insert=True)
    except ValidationError, IntegrityError:
        other = found()
        if other is None:
            raise
        return other
    return record


def car_brand_for(workshop, typed):
    """The brand these words name, whatever the capitals; a new word joins the list, and
    the list's spelling wins (JOB-17)."""
    name = tidy_name(typed)

    def found():
        return car_brand_named(workshop, name)

    return found() or _saved_or_found(CarBrand(workshop=workshop, name=name), found)


def car_model_for(workshop, brand, typed):
    """The model of this brand these words name, the same way (JOB-17)."""
    name = tidy_spaces(typed)

    def found():
        return (
            CarModel.objects.for_workshop(workshop).filter(brand=brand, name__iexact=name).first()
        )

    new = CarModel(workshop=workshop, brand=brand, name=name)
    return found() or _saved_or_found(new, found)


def _refuse_a_taken_plate_or_vin(car):
    """A plate or a VIN is never put on two cars, and the refusal names the other car (JOB-16,
    JOB-20). The last guard, under the questions a job card's save asks first (KNOWN-11,
    KNOWN-14)."""
    other = car_with_plate(car.workshop, car.plate, besides=car)
    if other is not None:
        words = _("This plate is on another car, %(car)s.") % {"car": other.name}
        raise ValidationError({"plate": words})
    other = car_with_vin(car.workshop, car.vin, besides=car)
    if other is not None:
        words = _("This VIN is on another car, %(car)s (%(plate)s).") % {
            "car": other.name,
            "plate": other.plate or _("no plate now"),
        }
        raise ValidationError({"vin": words})


def _save(car):
    """Checks a car and saves it, new or not. A car saved here always has a plate: only
    empty_plate() leaves one without (KNOWN-3)."""
    car.clean()
    if problem := plate_problem(car.plate):
        raise ValidationError({"plate": problem})
    _refuse_a_taken_plate_or_vin(car)
    try:
        car.full_clean()
        # Its own savepoint, so a refused save leaves a bigger transaction working.
        with transaction.atomic():
            car.save()
    except IntegrityError:
        # The plate or the VIN was free when it was checked, then another send took it.
        _refuse_a_taken_plate_or_vin(car)
        raise


def change_car(workshop, car, changes):
    """Changes what is true of the car, so it is right on the next visit (JOB-12).

    Only the boxes in changes change (JOB-43). Brand and model are one answer: a change of
    either finds the model of the brand on the page's other box or on the record.
    """
    if {"brand", "car_model"} & changes.keys():
        brand = car_brand_for(workshop, changes.get("brand", car.car_model.brand.name))
        car.car_model = car_model_for(workshop, brand, changes.get("car_model", car.car_model.name))
    for box in ("plate", "chassis_code", "vin"):
        if box in changes:
            setattr(car, box, changes[box])
    # One answer too: only Other has a colour of its own (JOB-21).
    if "colour" in changes:
        car.colour = changes["colour"]
        car.colour_other = changes.get("colour_other", "")
    _save(car)
    return car


def new_car(workshop, plate, brand, car_model):
    """A car the workshop has never seen, not saved yet: `change_car()` saves it. Its brand
    and model are found on their lists, or join them (JOB-14, JOB-17)."""
    car = Car(workshop=workshop, plate=tidy_plate(plate))
    car.car_model = car_model_for(workshop, car_brand_for(workshop, brand), car_model)
    return car


def empty_plate(workshop, car):
    """The car in front of you took this car's plate. It keeps its visits, and its VIN finds
    it again (KNOWN-3, KNOWN-10)."""
    Car.objects.for_workshop(workshop).filter(pk=car.pk).update(plate="")
    car.plate = ""


def empty_vin(workshop, car):
    """The car in front of you keeps this VIN, checked against its RC, so this car's empty
    box asks for it again at its next visit (KNOWN-11)."""
    Car.objects.for_workshop(workshop).filter(pk=car.pk).update(vin="")
    car.vin = ""


def remove_if_unused(workshop, car):
    """Removes a car that a move left with no job card: it was made by mistake (KNOWN-16).

    It asks no job card: Django's PROTECT refuses to delete a car that anything still points
    to, so a car with any job card is never removed. A test holds every link to a car to
    PROTECT.
    """
    with suppress(ProtectedError):
        Car.objects.for_workshop(workshop).filter(pk=car.pk).delete()


def customer_for(workshop, name, contact_number):
    """The record these two boxes name, made when it is new; None when both are empty
    (JOB-27, JOB-28).

    A name typed with its own capitals corrects the record's. A name typed with none says
    nothing about them, so "arun kp" never undoes "Arun KP".
    """
    tidied = tidy_name(name)
    number = tidy_contact_number(contact_number)
    if not tidied and not number:
        return None

    def found():
        return (
            Customer.objects.for_workshop(workshop)
            .filter(name__iexact=tidied, contact_number=number)
            .first()
        )

    customer = found()
    if customer is None:
        new = Customer(workshop=workshop, name=tidied, contact_number=number)
        return _saved_or_found(new, found)
    if customer.name != tidied and not tidy_spaces(name).islower():
        customer.name = tidied
        customer.save(update_fields=["name"])
    return customer

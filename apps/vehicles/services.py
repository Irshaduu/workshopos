"""Changes in vehicles: rules that change data (ADR-0005)."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext as _

from apps.core.text import tidy_name, tidy_spaces
from apps.vehicles.models import (
    Car,
    CarBrand,
    CarModel,
    Customer,
    tidy_contact_number,
    tidy_plate,
)
from apps.vehicles.selectors import car_with_plate


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
        return CarBrand.objects.for_workshop(workshop).filter(name__iexact=name).first()

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
    """A plate or a VIN on another car is refused next to its box, naming that car
    (JOB-15, JOB-20)."""
    words = {
        "plate": _("This plate is on another car, %(car)s."),
        "vin": _("This VIN is on another car, %(car)s (%(plate)s)."),
    }
    for box, taken in words.items():
        if value := getattr(car, box):
            other = (
                Car.objects.for_workshop(car.workshop)
                .filter(**{box: value})
                .exclude(pk=car.pk)
                .select_related("car_model__brand")
                .first()
            )
            if other is not None:
                raise ValidationError({box: taken % {"car": other.name, "plate": other.plate}})


def _save(car):
    """Checks a car and saves it, new or not."""
    car.clean()
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


def car_on_a_new_card(workshop, *, plate, brand, car_model, **changes):
    """The car a new job card is for (JOB-14).

    A plate the workshop knows finds its car, and a plate it has never seen makes a new
    one. What was typed is the car in front of you, so it replaces what the record says,
    and a box left empty changes nothing.
    """
    plate = tidy_plate(plate)
    filled = {box: value for box, value in changes.items() if value}
    car = car_with_plate(workshop, plate)
    if car is None:
        car = Car(workshop=workshop, plate=plate)
        car.car_model = car_model_for(workshop, car_brand_for(workshop, brand), car_model)
        return change_car(workshop, car, filled)
    return change_car(workshop, car, {"brand": brand, "car_model": car_model, **filled})


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

"""Reads for vehicles: rules that read data, never change it (ADR-0005)."""

from apps.core.text import tidy_name
from apps.vehicles.models import Car, CarBrand


def car_brand_named(workshop, typed):
    """The brand on the workshop's list that these words name, whatever the capitals; None when
    the list has none (JOB-17)."""
    return CarBrand.objects.for_workshop(workshop).filter(name__iexact=tidy_name(typed)).first()


def _car_with(workshop, box, value, besides):
    # No value names no car: a car can be left with no plate for a while (KNOWN-3), and many
    # have no VIN.
    if not value:
        return None
    cars = (
        Car.objects.for_workshop(workshop).filter(**{box: value}).select_related("car_model__brand")
    )
    if besides is not None:
        cars = cars.exclude(pk=besides.pk)
    return cars.first()


def car_with_plate(workshop, plate, *, besides=None):
    """The car other than `besides` that has this tidied plate today; None when no car has."""
    return _car_with(workshop, "plate", plate, besides)


def car_with_vin(workshop, vin, *, besides=None):
    """The car other than `besides` that has this tidied VIN; None when no car has."""
    return _car_with(workshop, "vin", vin, besides)

"""Reads for vehicles: rules that read data, never change it (ADR-0005)."""

from apps.vehicles.models import Car


def car_with_plate(workshop, plate):
    """The car that has this tidied plate today; None when no car has."""
    return (
        Car.objects.for_workshop(workshop)
        .filter(plate=plate)
        .select_related("car_model__brand")
        .first()
    )

"""Test data for vehicles (factory-boy, ADR-0013)."""

import factory
from factory.django import DjangoModelFactory

from apps.vehicles.models import Car, CarBrand, CarModel, Customer
from apps.workshops.tests.factories import WorkshopFactory


class CarBrandFactory(DjangoModelFactory):
    class Meta:
        model = CarBrand

    workshop = factory.SubFactory(WorkshopFactory)
    name = factory.Sequence(lambda n: f"Brand {n}")


class CarModelFactory(DjangoModelFactory):
    """A model of a brand in the same workshop."""

    class Meta:
        model = CarModel

    workshop = factory.SubFactory(WorkshopFactory)
    brand = factory.SubFactory(CarBrandFactory, workshop=factory.SelfAttribute("..workshop"))
    name = factory.Sequence(lambda n: f"Model {n}")


class CarFactory(DjangoModelFactory):
    """A car with a plate and a model, and nothing else filled."""

    class Meta:
        model = Car

    workshop = factory.SubFactory(WorkshopFactory)
    plate = factory.Sequence(lambda n: f"KL00AA{n:04}")
    car_model = factory.SubFactory(CarModelFactory, workshop=factory.SelfAttribute("..workshop"))


class CustomerFactory(DjangoModelFactory):
    class Meta:
        model = Customer

    workshop = factory.SubFactory(WorkshopFactory)
    name = factory.Sequence(lambda n: f"Customer {n}")
    contact_number = factory.Sequence(lambda n: f"90000{n:05}")

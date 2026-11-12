"""Test data for billing (factory-boy, ADR-0013)."""

from decimal import Decimal

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.accounts.tests.factories import UserFactory
from apps.billing.models import Bill, BillCounter, Payment, PaymentMethod
from apps.jobs.models import JobCardStatus
from apps.jobs.tests.factories import JobCardFactory
from apps.workshops.tests.factories import WorkshopFactory, first_branch


class BillCounterFactory(DjangoModelFactory):
    class Meta:
        model = BillCounter

    workshop = factory.SubFactory(WorkshopFactory)
    branch = factory.LazyAttribute(first_branch)
    financial_year = 2026


class BillFactory(DjangoModelFactory):
    """A settled bill, with its own settled job card in the same branch. To choose the branch,
    give the workshop too."""

    class Meta:
        model = Bill

    workshop = factory.SubFactory(WorkshopFactory)
    branch = factory.LazyAttribute(first_branch)
    job_card = factory.SubFactory(
        JobCardFactory,
        workshop=factory.SelfAttribute("..workshop"),
        branch=factory.SelfAttribute("..branch"),
        status=JobCardStatus.SETTLED,
    )
    # A year no settle gives, like JobCardFactory's numbers, so the two never clash.
    number = factory.Sequence(lambda n: f"INV-99-00-{n:04d}")
    date = factory.LazyFunction(timezone.localdate)
    settled_by = factory.SubFactory(UserFactory)
    discount = Decimal("0")
    brand = "BMW"
    car_model = "520d"


class PaymentFactory(DjangoModelFactory):
    class Meta:
        model = Payment

    workshop = factory.SubFactory(WorkshopFactory)
    bill = factory.SubFactory(BillFactory, workshop=factory.SelfAttribute("..workshop"))
    method = PaymentMethod.CASH
    amount = Decimal("1000.00")

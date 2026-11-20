"""Test data for audit (factory-boy, ADR-0013)."""

import uuid

import factory
from factory.django import DjangoModelFactory

from apps.accounts.tests.factories import UserFactory
from apps.audit.models import AuditSettings, Change, ChangedRecord
from apps.workshops.tests.factories import WorkshopFactory, first_branch


class AuditSettingsFactory(DjangoModelFactory):
    class Meta:
        model = AuditSettings

    workshop = factory.SubFactory(WorkshopFactory)


class ChangeFactory(DjangoModelFactory):
    """A kept change to a bill's cash. To keep a real one, use keep_change()."""

    class Meta:
        model = Change

    workshop = factory.SubFactory(WorkshopFactory)
    branch = factory.LazyAttribute(first_branch)
    what = ChangedRecord.BILL
    record_key = factory.LazyFunction(uuid.uuid7)
    label = "INV-99-00-0001, KL00AA0001"
    figures = factory.LazyFunction(
        lambda: [{"figure": "cash", "kind": "money", "before": "40000.00", "after": "38000.00"}]
    )
    reason = "Typed the wrong amount"
    by = factory.SubFactory(UserFactory)

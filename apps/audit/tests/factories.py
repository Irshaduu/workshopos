"""Test data for audit (factory-boy, ADR-0013)."""

import factory
from factory.django import DjangoModelFactory

from apps.audit.models import AuditSettings
from apps.workshops.tests.factories import WorkshopFactory


class AuditSettingsFactory(DjangoModelFactory):
    class Meta:
        model = AuditSettings

    workshop = factory.SubFactory(WorkshopFactory)

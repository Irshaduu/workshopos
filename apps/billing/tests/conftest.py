"""What the billing tests share."""

import uuid
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import Role
from apps.accounts.tests.factories import MembershipFactory
from apps.billing.services import settle_bill
from apps.jobs.tests.factories import ConcernFactory, JobCardFactory, JobLineFactory
from apps.staff.tests.factories import StaffMemberFactory
from apps.workshops.models import Branch


class Place:
    """A workshop, its first branch, and who acts there."""

    def __init__(self, role):
        member = MembershipFactory(role=role)
        self.workshop = member.workshop
        self.branch = Branch.objects.for_workshop(self.workshop).first()
        self.by = member.user

    def card(self, labour="43000", **more):
        """An open job card worth `labour`, with one job and a lead mechanic, so it has
        nothing left to fill but its mileage and its concerns."""
        card = JobCardFactory(
            workshop=self.workshop,
            branch=more.pop("branch", self.branch),
            labour=Decimal(labour),
            lead_mechanic=StaffMemberFactory(workshop=self.workshop),
            mileage=more.pop("mileage", 45230),
            **more,
        )
        JobLineFactory(workshop=self.workshop, job_card=card, text="Clutch plate replaced")
        return card

    def concern(self, card, **more):
        return ConcernFactory(workshop=self.workshop, job_card=card, **more)

    def settle(self, job_card, total_seen=None, key=None, paid_on=None, **payments):
        """Settles through the service, as the settle box does, with Cash 40000 unless told.
        Each payment is named by its method, like cash="20000"."""
        payments = {method: Decimal(amount) for method, amount in payments.items()} or {
            "cash": Decimal("40000")
        }
        return settle_bill(
            self.workshop,
            job_card.branch,
            job_card.pk,
            key or uuid.uuid7(),
            self.by,
            paid_on=paid_on or timezone.localdate(),
            payments=payments,
            total_seen=job_card.labour if total_seen is None else Decimal(total_seen),
        )


@pytest.fixture
def office(db):
    return Place(Role.OFFICE)


@pytest.fixture
def owner(db):
    return Place(Role.OWNER)

"""What the billing tests share."""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import Role
from apps.accounts.tests.factories import MembershipFactory
from apps.audit.models import Change
from apps.billing.models import Bill, Payment
from apps.billing.selectors import BOXES, bill_figures
from apps.billing.services import change_payments, settle_bill
from apps.jobs.tests.factories import ConcernFactory, JobCardFactory, JobLineFactory
from apps.staff.tests.factories import StaffMemberFactory
from apps.workshops.models import Branch


class Place:
    """A workshop, its first branch, and who acts there: a new workshop, or one given."""

    def __init__(self, role, workshop=None):
        member = MembershipFactory(role=role, **({"workshop": workshop} if workshop else {}))
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

    def bill_of(self, job_card):
        return Bill.objects.for_workshop(self.workshop).get(job_card=job_card)

    def change(
        self,
        job_card,
        reason="UPI was part of it",
        opening=None,
        paid_on=None,
        total_seen=None,
        key=None,
        **payments,
    ):
        """Changes the card's settled bill through the service, as the change box does: with a
        new change key, and with the bill as saved for what the box opened with, unless told.
        Each payment is named by its method, like upi="2000"; a method not named is left
        empty."""
        saved = bill_figures(self.workshop, self.bill_of(job_card))
        return change_payments(
            self.workshop,
            job_card.branch,
            job_card.pk,
            key or uuid.uuid7(),
            self.by,
            paid_on=saved["paid_on"] if paid_on is None else paid_on,
            payments={method: Decimal(amount) for method, amount in payments.items()},
            opening={box: saved[box] for box in BOXES} if opening is None else opening,
            reason=reason,
            total_seen=job_card.labour if total_seen is None else Decimal(total_seen),
        )


def refused(send):
    """The words of each box a settle or a change was refused for; nothing is saved."""
    with pytest.raises(ValidationError) as caught:
        send()
    return (
        caught.value.message_dict if hasattr(caught.value, "error_dict") else caught.value.messages
    )


def payments(bill):
    """A bill's payments as saved, by method."""
    return {payment.method: payment.amount for payment in Payment.objects.filter(bill=bill)}


def changes(place):
    """The changes kept in this place's workshop."""
    return Change.objects.for_workshop(place.workshop)


def settled(place, **payments):
    """A card worth 43,000, settled today with these payments (Cash 40,000 unless told)."""
    card = place.card(labour="43000")
    place.settle(card, **payments)
    return card


def settled_hours_ago(card, hours):
    """As if the card's bill was settled that many hours ago, for the edit window."""
    Bill.objects.filter(job_card=card).update(settled_at=timezone.now() - timedelta(hours=hours))


@pytest.fixture
def office(db):
    return Place(Role.OFFICE)


@pytest.fixture
def owner(db):
    return Place(Role.OWNER)

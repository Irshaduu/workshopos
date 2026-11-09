"""What the job card tests share."""

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.workshops.models import Branch
from apps.workshops.tests.factories import WorkshopFactory


@pytest.fixture
def place():
    """A workshop, its first branch, and who acts."""
    workshop = WorkshopFactory()
    return workshop, Branch.objects.for_workshop(workshop).first(), UserFactory()

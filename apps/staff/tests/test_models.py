"""What PostgreSQL holds for a staff member (docs/rules/staff-list.md)."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction

from apps.staff.models import Designation, StaffMember
from apps.staff.tests.factories import StaffMemberFactory
from apps.workshops.tests.factories import BranchFactory, WorkshopFactory

pytestmark = pytest.mark.django_db


def test_staff_3_the_designations_are_v1s_in_v1s_order():
    assert Designation.labels == [
        "Mechanic",
        "Assistant Mechanic",
        "Office Staff",
        "General Helper",
    ]


def test_staff_3_postgresql_refuses_any_other_designation():
    with (
        pytest.raises(IntegrityError, match="designation_known"),
        transaction.atomic(),
    ):
        StaffMemberFactory(designation="painter")


@pytest.mark.parametrize("name", ["", "   "])
def test_staff_5_postgresql_refuses_a_name_with_nothing_in_it(name):
    with pytest.raises(IntegrityError, match="name_given"), transaction.atomic():
        StaffMemberFactory(name=name)


def test_staff_5_a_name_stops_at_100_characters():
    member = StaffMemberFactory.build(workshop=WorkshopFactory(), name="A" * 101)

    with pytest.raises(ValidationError) as refused:
        member.full_clean()

    assert list(refused.value.message_dict) == ["name"]


@pytest.mark.parametrize("second", ["Anil Kumar", "anil kumar", "ANIL KUMAR"])
def test_staff_7_postgresql_refuses_a_second_copy_of_a_name_whatever_the_capitals(second):
    first = StaffMemberFactory(name="Anil Kumar")

    with pytest.raises(IntegrityError, match="name_once"), transaction.atomic():
        StaffMemberFactory(workshop=first.workshop, branch=first.branch, name=second)


def test_staff_7_a_turned_off_persons_name_still_counts():
    first = StaffMemberFactory(name="Anil Kumar", is_active=False)

    with pytest.raises(IntegrityError, match="name_once"), transaction.atomic():
        StaffMemberFactory(workshop=first.workshop, branch=first.branch, name="Anil Kumar")


def test_staff_7_the_same_name_in_another_branch_or_another_workshop_is_fine():
    first = StaffMemberFactory(name="Anil Kumar")

    other_branch = BranchFactory(workshop=first.workshop)
    StaffMemberFactory(workshop=first.workshop, branch=other_branch, name="Anil Kumar")
    StaffMemberFactory(name="Anil Kumar")

    connection.check_constraints()
    assert StaffMember.objects.filter(name="Anil Kumar").count() == 3


def test_staff_7_the_check_before_saving_says_it_in_plain_words():
    first = StaffMemberFactory(name="Anil Kumar")
    second = StaffMemberFactory.build(
        workshop=first.workshop, branch=first.branch, name="anil kumar"
    )

    with pytest.raises(ValidationError, match="already on the staff list"):
        second.full_clean()


def test_staff_4_postgresql_keeps_the_branch_inside_the_workshop():
    # The first real link of this kind (ADR-0023). PostgreSQL checks at the end of the
    # transaction, so the check is asked for here.
    theirs = BranchFactory()

    with pytest.raises(IntegrityError, match="branch_same_workshop"), transaction.atomic():
        StaffMemberFactory(workshop=WorkshopFactory(), branch=theirs)
        connection.check_constraints()


def test_staff_8_a_new_person_starts_turned_on_even_for_a_row_added_outside_django():
    assert StaffMemberFactory().is_active is True
    assert StaffMember._meta.get_field("is_active").db_default is True


def test_a_staff_member_reads_as_their_name():
    assert str(StaffMember(name="Anil Kumar")) == "Anil Kumar"

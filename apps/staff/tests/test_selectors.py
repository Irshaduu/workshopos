"""What the Staff list reads (apps/staff/selectors.py)."""

import uuid

import pytest
from django.db import connection
from django.http import Http404
from django.test.utils import CaptureQueriesContext

from apps.staff.models import Designation
from apps.staff.selectors import may_lead, saved_staff_member, staff_by_designation, staff_member
from apps.staff.tests.factories import StaffMemberFactory
from apps.workshops.models import Branch
from apps.workshops.tests.factories import BranchFactory, WorkshopFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def workshop():
    return WorkshopFactory()


@pytest.fixture
def branch(workshop):
    return Branch.objects.for_workshop(workshop).get()


def names_in(groups, designation):
    return [member.name for member in dict(groups)[designation]]


def test_staff_15_mechanics_then_assistants_each_by_name_and_only_people_turned_on(
    workshop, branch
):
    made = {"workshop": workshop, "branch": branch}
    StaffMemberFactory(name="zaid", **made)
    StaffMemberFactory(name="Ajay", **made)
    StaffMemberFactory(name="Biju", designation=Designation.ASSISTANT_MECHANIC, **made)
    StaffMemberFactory(name="Aarav", designation=Designation.ASSISTANT_MECHANIC, **made)
    StaffMemberFactory(name="Priya", designation=Designation.OFFICE_STAFF, **made)
    StaffMemberFactory(name="Suresh", designation=Designation.GENERAL_HELPER, **made)
    StaffMemberFactory(name="Gone", is_active=False, **made)

    assert [member.name for member in may_lead(workshop, branch)] == [
        "Ajay",
        "zaid",
        "Aarav",
        "Biju",
    ]


def test_staff_15_a_cards_own_person_comes_last_whatever_has_changed(workshop, branch):
    made = {"workshop": workshop, "branch": branch}
    StaffMemberFactory(name="Zaid", **made)
    gone = StaffMemberFactory(name="Anil", is_active=False, **made)
    moved = StaffMemberFactory(name="Biju", designation=Designation.GENERAL_HELPER, **made)

    assert [member.name for member in may_lead(workshop, branch, gone.pk)] == ["Zaid", "Anil"]
    assert [member.name for member in may_lead(workshop, branch, moved.pk)] == ["Zaid", "Biju"]


def test_staff_15_another_branchs_person_is_never_picked(workshop, branch):
    there = BranchFactory(workshop=workshop)
    theirs = StaffMemberFactory(workshop=workshop, branch=there)

    assert not may_lead(workshop, branch).exists()
    assert not may_lead(workshop, branch, theirs.pk).exists()


def test_staff_15_a_person_says_whether_a_new_card_can_pick_them(workshop, branch):
    made = {"workshop": workshop, "branch": branch}

    assert StaffMemberFactory(**made).may_lead
    assert StaffMemberFactory(designation=Designation.ASSISTANT_MECHANIC, **made).may_lead
    assert not StaffMemberFactory(designation=Designation.OFFICE_STAFF, **made).may_lead
    assert not StaffMemberFactory(is_active=False, **made).may_lead


def test_staff_20_every_designation_comes_in_order_even_with_no_one_in_it(workshop, branch):
    groups = staff_by_designation(workshop, branch)

    assert groups == [
        (Designation.MECHANIC, []),
        (Designation.ASSISTANT_MECHANIC, []),
        (Designation.OFFICE_STAFF, []),
        (Designation.GENERAL_HELPER, []),
    ]


def test_staff_20_each_person_is_under_their_own_designation(workshop, branch):
    StaffMemberFactory(workshop=workshop, name="Suresh", designation=Designation.GENERAL_HELPER)
    StaffMemberFactory(workshop=workshop, name="Nisha", designation=Designation.OFFICE_STAFF)

    groups = staff_by_designation(workshop, branch)

    assert names_in(groups, Designation.GENERAL_HELPER) == ["Suresh"]
    assert names_in(groups, Designation.OFFICE_STAFF) == ["Nisha"]
    assert names_in(groups, Designation.MECHANIC) == []


def test_staff_20_and_12_turned_on_first_then_by_name_whatever_the_capitals(workshop, branch):
    for name, is_active in [
        ("Zubair", True),
        ("biju", True),
        ("Anil", False),
        ("Arun", True),
        ("Ravi", False),
    ]:
        StaffMemberFactory(workshop=workshop, name=name, is_active=is_active)

    groups = staff_by_designation(workshop, branch)

    assert names_in(groups, Designation.MECHANIC) == ["Arun", "biju", "Zubair", "Anil", "Ravi"]


def test_staff_20_the_order_does_not_depend_on_the_servers_own_language_setting(workshop, branch):
    # This server's setting already ignores capitals, so the test above passes either
    # way. Another server's may not: there, "biju" would come after "Zubair". So the
    # query itself must ask.
    with CaptureQueriesContext(connection) as queries:
        staff_by_designation(workshop, branch)

    (sql,) = [query["sql"] for query in queries.captured_queries]
    assert 'ORDER BY "staff_staffmember"."is_active" DESC, LOWER("staff_staffmember"."name")' in sql


def test_staff_4_the_list_shows_only_this_branch(workshop, branch):
    StaffMemberFactory(workshop=workshop, name="Here")
    StaffMemberFactory(workshop=workshop, branch=BranchFactory(workshop=workshop), name="There")
    StaffMemberFactory(name="Other workshop")

    assert names_in(staff_by_designation(workshop, branch), Designation.MECHANIC) == ["Here"]


def test_staff_4_a_person_is_found_in_their_own_branch(workshop, branch):
    member = StaffMemberFactory(workshop=workshop)

    assert staff_member(workshop, branch, member.pk) == member


@pytest.mark.parametrize(
    "make_other",
    [
        pytest.param(lambda workshop: StaffMemberFactory().pk, id="another workshop"),
        pytest.param(
            lambda workshop: (
                StaffMemberFactory(workshop=workshop, branch=BranchFactory(workshop=workshop)).pk
            ),
            id="another branch",
        ),
        pytest.param(lambda workshop: uuid.uuid7(), id="no such person"),
    ],
)
def test_staff_4_anyone_else_is_not_found(workshop, branch, make_other):
    key = make_other(workshop)

    with pytest.raises(Http404):
        staff_member(workshop, branch, key)
    assert saved_staff_member(workshop, branch, key) is None


def test_staff_9_a_saved_person_is_found_by_their_key(workshop, branch):
    member = StaffMemberFactory(workshop=workshop)

    assert saved_staff_member(workshop, branch, member.pk) == member

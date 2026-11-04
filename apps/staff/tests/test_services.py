"""What changes a staff member (apps/staff/services.py)."""

import threading
import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.http import Http404
from django.test.utils import CaptureQueriesContext

from apps.staff.models import Designation, StaffMember
from apps.staff.services import add_staff_member, change_staff_member, turn_off, turn_on
from apps.staff.tests.factories import StaffMemberFactory
from apps.workshops.models import Branch
from apps.workshops.tests.factories import BranchFactory, WorkshopFactory


@pytest.fixture
def workshop(db):
    return WorkshopFactory()


@pytest.fixture
def branch(workshop):
    return Branch.objects.for_workshop(workshop).get()


def add(workshop, branch, key=None, name="Anil Kumar", designation=Designation.MECHANIC):
    return add_staff_member(
        workshop, branch, key or uuid.uuid7(), name=name, designation=designation
    )


def people_in(workshop):
    return StaffMember.objects.for_workshop(workshop)


def test_staff_8_a_new_person_is_saved_in_the_branch_and_turned_on(workshop, branch):
    key = uuid.uuid7()

    member = add(workshop, branch, key, designation=Designation.OFFICE_STAFF)

    member.refresh_from_db()
    assert member.pk == key
    assert member.workshop == workshop
    assert member.branch == branch
    assert member.name == "Anil Kumar"
    assert member.designation == Designation.OFFICE_STAFF
    assert member.is_active is True


def test_staff_6_a_new_name_is_tidied_with_no_form_in_front(workshop, branch):
    assert add(workshop, branch, name="  anil   kumar ").name == "Anil Kumar"


def test_staff_6_and_7_double_spaces_cannot_hide_a_second_copy(workshop, branch):
    add(workshop, branch, name="Anil Kumar")

    with pytest.raises(ValidationError, match="already on the staff list"):
        add(workshop, branch, name="Anil   Kumar")


def test_staff_6_a_changed_name_is_tidied_with_no_form_in_front(workshop, branch):
    member = StaffMemberFactory(workshop=workshop)

    changed = change_staff_member(
        workshop, branch, member.pk, name="  new   name ", designation=Designation.MECHANIC
    )

    member.refresh_from_db()
    assert changed.name == member.name == "New Name"


def test_staff_9_a_repeat_saves_once_and_gets_the_person_saved_first(workshop, branch):
    key = uuid.uuid7()
    add(workshop, branch, key, name="Anil Kumar")

    repeat = add(workshop, branch, key, name="Typed Again")

    assert repeat.pk == key
    assert repeat.name == "Anil Kumar"
    assert people_in(workshop).count() == 1


@pytest.mark.django_db(transaction=True)
def test_staff_9_two_sends_at_the_same_moment_save_one_person():
    # Two connections each need a real commit. Which send wins is left to chance, so
    # a few pairs run: every order must end the same way.
    workshop = WorkshopFactory()
    branch = Branch.objects.for_workshop(workshop).get()

    def send(key, start, answers):
        start.wait()
        try:
            answers.append(add(workshop, branch, key, name=f"Same {key}").pk)
        finally:
            connection.close()

    for _ in range(5):
        key = uuid.uuid7()
        start = threading.Barrier(2)
        answers = []
        sends = [threading.Thread(target=send, args=(key, start, answers)) for _ in range(2)]
        for each in sends:
            each.start()
        for each in sends:
            each.join()

        assert answers == [key, key]
        assert people_in(workshop).filter(pk=key).count() == 1


def test_staff_7_a_taken_name_is_refused_with_a_new_key(workshop, branch):
    add(workshop, branch, name="Anil Kumar")

    with pytest.raises(ValidationError, match="already on the staff list"):
        add(workshop, branch, name="anil kumar")

    assert people_in(workshop).count() == 1


def test_staff_7_two_people_typing_one_name_at_once_get_the_same_answer(
    workshop, branch, monkeypatch
):
    # The name was free when it was checked, then another person took it. The answer is
    # the plain refusal, not a server error page.
    add(workshop, branch, name="Anil Kumar")
    monkeypatch.setattr(StaffMember, "full_clean", lambda *args, **kwargs: None)

    with pytest.raises(ValidationError, match="already on the staff list"):
        add(workshop, branch, name="Anil Kumar")

    # The refused save left the test's own transaction working.
    assert people_in(workshop).count() == 1


def test_staff_9_a_key_taken_in_another_workshop_is_not_found_and_changes_nothing(workshop, branch):
    theirs = StaffMemberFactory(name="Theirs")

    with pytest.raises(Http404):
        add(workshop, branch, theirs.pk, name="Ours")

    assert not people_in(workshop).exists()
    theirs.refresh_from_db()
    assert theirs.name == "Theirs"


def test_staff_10_a_change_keeps_the_same_record(workshop, branch):
    member = StaffMemberFactory(workshop=workshop, name="Old Name")

    changed = change_staff_member(
        workshop, branch, member.pk, name="New Name", designation=Designation.OFFICE_STAFF
    )

    assert changed.pk == member.pk
    member.refresh_from_db()
    assert member.name == "New Name"
    assert member.designation == Designation.OFFICE_STAFF
    assert people_in(workshop).count() == 1


def test_staff_10_a_person_can_fix_the_capitals_of_their_own_name(workshop, branch):
    member = StaffMemberFactory(workshop=workshop, name="anil kp")

    change_staff_member(
        workshop, branch, member.pk, name="Anil KP", designation=Designation.MECHANIC
    )

    member.refresh_from_db()
    assert member.name == "Anil KP"


def test_staff_10_a_repeat_saves_the_same_values_again(workshop, branch):
    member = StaffMemberFactory(workshop=workshop, name="Old Name")

    for _ in range(2):
        change_staff_member(
            workshop, branch, member.pk, name="New Name", designation=Designation.MECHANIC
        )

    member.refresh_from_db()
    assert member.name == "New Name"


def test_staff_10_a_change_keeps_a_turned_off_person_turned_off(workshop, branch):
    member = StaffMemberFactory(workshop=workshop, is_active=False)

    change_staff_member(
        workshop, branch, member.pk, name="New Name", designation=Designation.MECHANIC
    )

    member.refresh_from_db()
    assert member.is_active is False


def test_staff_7_a_change_to_a_taken_name_is_refused_and_changes_nothing(workshop, branch):
    StaffMemberFactory(workshop=workshop, name="Anil Kumar")
    member = StaffMemberFactory(workshop=workshop, name="Bilal Rahman")

    with pytest.raises(ValidationError, match="already on the staff list"):
        change_staff_member(
            workshop, branch, member.pk, name="anil kumar", designation=Designation.OFFICE_STAFF
        )

    member.refresh_from_db()
    assert member.name == "Bilal Rahman"
    assert member.designation == Designation.MECHANIC


def test_staff_7_a_change_racing_for_one_name_gets_the_same_answer(workshop, branch, monkeypatch):
    StaffMemberFactory(workshop=workshop, name="Anil Kumar")
    member = StaffMemberFactory(workshop=workshop, name="Bilal Rahman")
    monkeypatch.setattr(StaffMember, "full_clean", lambda *args, **kwargs: None)

    with pytest.raises(ValidationError, match="already on the staff list"):
        change_staff_member(
            workshop, branch, member.pk, name="Anil Kumar", designation=Designation.MECHANIC
        )

    member.refresh_from_db()
    assert member.name == "Bilal Rahman"


def test_a_change_checks_every_rule_before_it_saves(workshop, branch):
    # A service called with no form in front of it, like a future import tool, gets the
    # plain refusal of the rule it broke, not the database's.
    member = StaffMemberFactory(workshop=workshop)

    with pytest.raises(ValidationError) as refused:
        change_staff_member(workshop, branch, member.pk, name="New Name", designation="painter")

    assert list(refused.value.message_dict) == ["designation"]


@pytest.mark.parametrize(
    "change",
    [
        pytest.param(turn_off, id="turn off"),
        pytest.param(turn_on, id="turn on"),
        pytest.param(
            lambda workshop, branch, key: change_staff_member(
                workshop, branch, key, name="New Name", designation=Designation.MECHANIC
            ),
            id="edit",
        ),
    ],
)
def test_a_change_to_a_saved_record_locks_its_row(workshop, branch, change):
    # docs: CONTRIBUTING.md, a change runs in one locked transaction.
    member = StaffMemberFactory(workshop=workshop)

    with CaptureQueriesContext(connection) as queries:
        change(workshop, branch, member.pk)

    assert [q["sql"] for q in queries.captured_queries if "FOR UPDATE" in q["sql"]]


def test_staff_11_turning_off_keeps_the_record(workshop, branch):
    member = StaffMemberFactory(workshop=workshop)

    turned = turn_off(workshop, branch, member.pk)

    assert turned.is_active is False
    member.refresh_from_db()
    assert member.is_active is False


def test_staff_13_a_repeated_turn_off_ends_turned_off(workshop, branch):
    member = StaffMemberFactory(workshop=workshop)

    turn_off(workshop, branch, member.pk)
    turn_off(workshop, branch, member.pk)

    member.refresh_from_db()
    assert member.is_active is False


def test_staff_13_a_repeated_turn_on_ends_turned_on(workshop, branch):
    member = StaffMemberFactory(workshop=workshop, is_active=False)

    turn_on(workshop, branch, member.pk)
    turn_on(workshop, branch, member.pk)

    member.refresh_from_db()
    assert member.is_active is True


def test_staff_13_a_repeat_writes_nothing(workshop, branch, django_assert_num_queries):
    member = StaffMemberFactory(workshop=workshop, is_active=False)

    # The savepoint, the locked read, and its release: no write.
    with django_assert_num_queries(3):
        turn_off(workshop, branch, member.pk)


@pytest.mark.parametrize("change", [turn_off, turn_on])
def test_staff_4_a_person_of_another_workshop_is_not_found_and_stays_as_they_were(
    workshop, branch, change
):
    theirs = StaffMemberFactory(is_active=change is turn_on)

    with pytest.raises(Http404):
        change(workshop, branch, theirs.pk)

    before = theirs.is_active
    theirs.refresh_from_db()
    assert theirs.is_active is before


def test_staff_4_a_person_of_another_branch_cannot_be_changed(workshop, branch):
    there = StaffMemberFactory(
        workshop=workshop, branch=BranchFactory(workshop=workshop), name="There"
    )

    with pytest.raises(Http404):
        change_staff_member(
            workshop, branch, there.pk, name="Changed", designation=Designation.MECHANIC
        )

    there.refresh_from_db()
    assert there.name == "There"

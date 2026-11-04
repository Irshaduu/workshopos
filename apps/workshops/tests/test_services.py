"""A double tap never saves a record twice (apps/workshops/services.py, docs/PLAN.md).

The tests save branches, because a branch is a real record with a unique name. The
Staff list is the first page that uses this.
"""

import threading
import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection
from django.http import Http404

from apps.workshops.models import Branch
from apps.workshops.services import save_once
from apps.workshops.tests.factories import BranchFactory, WorkshopFactory


@pytest.fixture
def workshop(db):
    return WorkshopFactory(first_branch=None)


def new_branch(workshop, key=None, name="Main"):
    return Branch(id=key or uuid.uuid7(), workshop=workshop, name=name)


def test_a_new_record_is_saved_and_says_so(workshop):
    branch = new_branch(workshop)

    saved, saved_now = save_once(branch)

    assert saved_now is True
    assert saved is branch
    assert Branch.objects.for_workshop(workshop).get().pk == branch.pk


@pytest.mark.parametrize(
    "name",
    [
        pytest.param("Typed again", id="PostgreSQL refuses the key"),
        pytest.param("Main", id="full_clean refuses the name"),
    ],
)
def test_a_second_send_gets_the_saved_record_with_its_first_values(workshop, name):
    key = uuid.uuid7()
    save_once(new_branch(workshop, key, name="Main"))

    saved, saved_now = save_once(new_branch(workshop, key, name=name))

    assert saved_now is False
    assert saved.pk == key
    assert saved.name == "Main"
    # The refused save left the test's own transaction working.
    assert Branch.objects.for_workshop(workshop).get().name == "Main"


def test_a_second_send_that_fails_the_checks_still_gets_the_saved_record(workshop):
    # The first try was saved, its answer was lost, and the person then cleared a box.
    key = uuid.uuid7()
    save_once(new_branch(workshop, key, name="Main"))

    saved, saved_now = save_once(new_branch(workshop, key, name=""))

    assert saved_now is False
    assert saved.name == "Main"


def test_a_normal_save_costs_no_extra_look(workshop, django_assert_num_queries):
    # The two checks (the workshop exists, the name is free), then the save, inside its
    # savepoint and the release. No look for the key: that comes only after a refusal.
    with django_assert_num_queries(5):
        save_once(new_branch(workshop))


def two_sends_at_once(workshop, key):
    """What each of two sends at the same moment answers: did this one save it?"""
    start = threading.Barrier(2)
    answers = []

    def send():
        start.wait()
        try:
            answers.append(save_once(new_branch(workshop, key, name=f"Same {key}"))[1])
        finally:
            connection.close()

    sends = [threading.Thread(target=send) for _ in range(2)]
    for each in sends:
        each.start()
    for each in sends:
        each.join()
    return answers


@pytest.mark.django_db(transaction=True)
def test_two_sends_at_the_same_moment_save_one_record():
    # Two connections each need a real commit. Which send wins is left to chance, so
    # a few pairs run: every order must end the same way.
    workshop = WorkshopFactory(first_branch=None)

    for _ in range(5):
        key = uuid.uuid7()

        assert sorted(two_sends_at_once(workshop, key)) == [False, True]
        assert Branch.objects.for_workshop(workshop).filter(pk=key).count() == 1


def test_a_key_taken_in_another_workshop_is_not_found_and_changes_nothing(workshop):
    theirs = BranchFactory(name="Theirs")

    with pytest.raises(Http404):
        save_once(new_branch(workshop, theirs.pk, name="Ours"))

    assert not Branch.objects.for_workshop(workshop).exists()
    theirs.refresh_from_db()
    assert theirs.name == "Theirs"


def test_a_key_that_is_not_a_uuid7_is_not_found_and_saves_nothing(workshop):
    # An address typed by hand can hold any UUID.
    with pytest.raises(Http404):
        save_once(new_branch(workshop, uuid.uuid4()))

    assert not Branch.objects.for_workshop(workshop).exists()


def test_a_key_taken_in_another_branch_is_not_found(planted, workshop):
    here, there = BranchFactory(workshop=workshop), BranchFactory(workshop=workshop)
    key = uuid.uuid7()
    save_once(planted(id=key, workshop=workshop, branch=here))

    with pytest.raises(Http404):
        save_once(planted(id=key, workshop=workshop, branch=there))


def test_a_repeat_in_the_same_branch_gets_the_saved_record(planted, workshop):
    here = BranchFactory(workshop=workshop)
    key = uuid.uuid7()
    save_once(planted(id=key, workshop=workshop, branch=here))

    saved, saved_now = save_once(planted(id=key, workshop=workshop, branch=here))

    assert saved_now is False
    assert saved.pk == key


def test_a_real_rule_still_refuses_with_a_new_key(workshop):
    save_once(new_branch(workshop, name="Main"))

    with pytest.raises(ValidationError, match="already has a branch with this name"):
        save_once(new_branch(workshop, name="Main"))

    assert Branch.objects.for_workshop(workshop).count() == 1


def test_a_record_is_checked_before_it_is_saved(workshop):
    with pytest.raises(ValidationError) as refused:
        save_once(new_branch(workshop, name=""))

    assert list(refused.value.message_dict) == ["name"]
    assert not Branch.objects.for_workshop(workshop).exists()


def test_a_rule_only_postgresql_knows_still_refuses(workshop, monkeypatch):
    # The name was free when it was checked, then another person took it.
    save_once(new_branch(workshop, name="Main"))
    monkeypatch.setattr(Branch, "full_clean", lambda *args, **kwargs: None)

    with pytest.raises(IntegrityError):
        save_once(new_branch(workshop, name="Main"))

    # The refused save left the test's own transaction working.
    assert Branch.objects.for_workshop(workshop).count() == 1

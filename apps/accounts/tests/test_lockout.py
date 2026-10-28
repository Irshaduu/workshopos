"""The lockout for a password (apps/accounts/services.py and selectors.py)."""

import threading
from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone

from apps.accounts.selectors import minutes_locked
from apps.accounts.services import clear_wrong_passwords, count_wrong_password
from apps.accounts.tests.factories import UserFactory


def wrong(user, times):
    for _ in range(times):
        count_wrong_password(user)
    user.refresh_from_db()


def last_wrong_password_was(user, minutes_ago):
    user.last_wrong_password_at = timezone.now() - timedelta(minutes=minutes_ago)
    user.save(update_fields=["last_wrong_password_at"])


@pytest.mark.django_db
def test_sign_29_five_wrong_passwords_in_a_row_lock_the_account_for_15_minutes():
    user = UserFactory()

    wrong(user, 5)

    assert minutes_locked(user) == 15


@pytest.mark.django_db
def test_sign_29_four_wrong_passwords_do_not_lock_it():
    user = UserFactory()

    wrong(user, 4)

    assert minutes_locked(user) == 0


@pytest.mark.django_db
def test_sign_29_the_lock_ends_15_minutes_after_the_last_wrong_password():
    user = UserFactory()
    wrong(user, 5)

    last_wrong_password_was(user, minutes_ago=14.5)
    assert minutes_locked(user) == 1

    last_wrong_password_was(user, minutes_ago=15)
    assert minutes_locked(user) == 0


@pytest.mark.django_db
def test_sign_30_a_wrong_password_after_15_minutes_starts_the_count_again_at_one():
    user = UserFactory()
    wrong(user, 4)
    last_wrong_password_was(user, minutes_ago=16)

    wrong(user, 1)

    assert user.wrong_passwords == 1
    assert minutes_locked(user) == 0


@pytest.mark.django_db
def test_sign_31_one_accounts_wrong_passwords_never_lock_another():
    floor, office = UserFactory(), UserFactory()

    wrong(floor, 5)

    office.refresh_from_db()
    assert minutes_locked(floor) == 15
    assert minutes_locked(office) == 0


@pytest.mark.django_db
def test_sign_32_a_try_while_locked_is_not_counted_so_the_lock_never_grows():
    user = UserFactory()
    wrong(user, 5)
    last_wrong_password_was(user, minutes_ago=10)

    wrong(user, 3)

    assert user.wrong_passwords == 5
    assert minutes_locked(user) == 5


@pytest.mark.django_db
def test_sign_34_the_right_password_clears_the_count():
    user = UserFactory()
    wrong(user, 4)

    clear_wrong_passwords(user)

    user.refresh_from_db()
    assert (user.wrong_passwords, user.last_wrong_password_at) == (0, None)


@pytest.mark.django_db
def test_clearing_an_account_with_no_count_writes_nothing(django_assert_num_queries):
    user = UserFactory()

    with django_assert_num_queries(0):
        clear_wrong_passwords(user)


@pytest.mark.django_db(transaction=True)
def test_two_wrong_passwords_at_the_same_moment_count_as_two():
    # The one slow test: two connections each need a real commit. It hangs
    # on timing: without the row lock it failed 2 runs of 3 (2026-10-28), so
    # a pass alone proves less than a fail.
    user = UserFactory()
    start = threading.Barrier(2)

    def try_once():
        start.wait()
        try:
            count_wrong_password(user)
        finally:
            connection.close()

    tries = [threading.Thread(target=try_once) for _ in range(2)]
    for each in tries:
        each.start()
    for each in tries:
        each.join()

    user.refresh_from_db()
    assert user.wrong_passwords == 2

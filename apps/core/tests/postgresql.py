"""What the tests of every app share about PostgreSQL's own checks and locks."""

import time

import pytest
from django.db import IntegrityError, connection, transaction


def refused_by_postgresql(make, constraint=None):
    """PostgreSQL refuses it, by this constraint when one is named, so a test never passes
    for another rule's refusal. A link's check waits for the end of the transaction, so it
    is asked for here."""
    with pytest.raises(IntegrityError, match=constraint), transaction.atomic():
        make()
        connection.check_constraints()


def wait_for_a_lock(count=1, seconds=10):
    """Waits until `count` other sessions of this database wait for a lock, so a test that
    holds the lock knows they all reached it before it lets them go."""
    deadline = time.monotonic() + seconds
    with connection.cursor() as cursor:
        while time.monotonic() < deadline:
            # A transaction sees the same picture of the sessions each time it looks, unless
            # it asks for a new one, and the test looks from inside the one holding the lock.
            cursor.execute("SELECT pg_stat_clear_snapshot()")
            cursor.execute(
                "SELECT count(*) FROM pg_stat_activity"
                " WHERE datname = current_database() AND wait_event_type = 'Lock'"
            )
            if cursor.fetchone()[0] >= count:
                return
            time.sleep(0.05)
    raise AssertionError(f"{count} sessions never waited for a lock.")

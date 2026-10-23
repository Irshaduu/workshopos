"""The settings every machine shares (config/settings/base.py)."""

import pytest
from django.conf import settings
from django.db import connection

from config.settings import base


def test_debug_is_off_unless_a_machine_turns_it_on():
    assert base.DEBUG is False


def test_dates_use_india_time():
    assert settings.TIME_ZONE == "Asia/Kolkata"
    assert settings.USE_TZ is True


@pytest.mark.django_db
def test_the_database_is_postgresql_18_or_newer():
    assert connection.vendor == "postgresql"
    assert connection.pg_version >= 180000

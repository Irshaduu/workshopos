"""config/env.py: settings come from the environment, or from a local .env file."""

import os

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.env import env, load_env_file


@pytest.fixture(autouse=True)
def empty_environment(monkeypatch):
    """Each test starts with an empty environment; the real one comes back afterwards."""
    monkeypatch.setattr(os, "environ", {})


def test_a_set_value_is_returned():
    os.environ["DB_NAME"] = "workshopos"
    assert env("DB_NAME") == "workshopos"


def test_a_missing_required_value_stops_start_up():
    with pytest.raises(ImproperlyConfigured, match="DB_PASSWORD"):
        env("DB_PASSWORD")


def test_an_empty_required_value_stops_start_up():
    os.environ["DB_PASSWORD"] = ""
    with pytest.raises(ImproperlyConfigured, match="DB_PASSWORD"):
        env("DB_PASSWORD")


def test_the_default_is_used_when_the_value_is_missing():
    assert env("DB_PORT", default="5432") == "5432"


def test_the_env_file_fills_values_and_skips_comments_and_blank_lines(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# a comment\n\nDB_NAME=workshopos\nDB_HOST = localhost \n", encoding="utf-8"
    )
    load_env_file(env_file)
    assert os.environ["DB_NAME"] == "workshopos"
    assert os.environ["DB_HOST"] == "localhost"
    assert "# a comment" not in os.environ


def test_a_byte_order_mark_at_the_start_of_the_env_file_is_ignored(tmp_path):
    # Windows PowerShell 5.1 saves text files with one.
    env_file = tmp_path / ".env"
    env_file.write_text("DJANGO_SECRET_KEY=abc\n", encoding="utf-8-sig")
    load_env_file(env_file)
    assert os.environ["DJANGO_SECRET_KEY"] == "abc"


def test_a_real_environment_value_wins_over_the_env_file(tmp_path):
    os.environ["DB_HOST"] = "db.server"
    env_file = tmp_path / ".env"
    env_file.write_text("DB_HOST=localhost\n", encoding="utf-8")
    load_env_file(env_file)
    assert os.environ["DB_HOST"] == "db.server"


def test_a_missing_env_file_is_not_an_error(tmp_path):
    load_env_file(tmp_path / "no-such-file")
    assert "DB_NAME" not in os.environ

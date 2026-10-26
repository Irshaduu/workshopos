"""Every model's key (ADR-0022): a UUID7, made by Python, with PostgreSQL as backup."""

import uuid

import pytest
from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models
from django.db.models.functions import UUID7

from apps.accounts.models import User


def key_problem(model):
    """What is wrong with a model's key, or None when it is right."""
    key = model._meta.pk
    if not isinstance(key, models.UUIDField):
        return "its key is not a UUID"
    if key.default is not uuid.uuid7:
        return "Python does not make its key"
    if not isinstance(key.db_default, UUID7):
        return "PostgreSQL does not make its key"
    return None


def test_every_model_in_our_apps_has_the_uuid7_key(our_models):
    problems = {model._meta.label: key_problem(model) for model in our_models}

    assert {label: problem for label, problem in problems.items() if problem} == {}


def test_a_model_without_the_base_model_is_caught():
    assert key_problem(ContentType) == "its key is not a UUID"


def test_a_record_has_its_key_before_it_is_saved():
    assert User(username="new").pk.version == 7


@pytest.mark.django_db
def test_saving_keeps_the_same_key():
    user = User(username="new")
    key = user.pk

    user.save()
    user.refresh_from_db()

    assert user.pk == key


@pytest.mark.django_db
def test_a_link_made_before_saving_keeps_its_record():
    # With a key made only by PostgreSQL, this link was lost (ADR-0022).
    user = User(username="new")
    entry = LogEntry(user=user, action_flag=ADDITION, object_repr="a link made early")

    user.save()
    entry.save()
    entry.refresh_from_db()

    assert entry.user_id == user.pk


@pytest.mark.django_db
def test_postgresql_makes_a_key_for_a_row_added_outside_django():
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO accounts_user (password, is_superuser, username, first_name,"
            " last_name, email, is_staff, is_active, date_joined)"
            " VALUES ('', false, 'added-outside', '', '', '', false, true, now())"
            " RETURNING id"
        )
        (key,) = cursor.fetchone()

    assert key.version == 7

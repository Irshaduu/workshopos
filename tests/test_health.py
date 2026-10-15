"""The health check (config/health.py): hosts and uptime monitors call it."""

import pytest
from django.db import OperationalError, connection


@pytest.mark.django_db
def test_health_check_says_ok_when_the_database_answers(client):
    response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_health_check_says_unavailable_when_the_database_does_not_answer(
    client, monkeypatch, caplog
):
    def database_down(*args, **kwargs):
        raise OperationalError("connection refused")

    monkeypatch.setattr(connection, "cursor", database_down)

    response = client.get("/health/")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert "the database did not answer" in caplog.text


@pytest.mark.django_db
def test_health_check_is_never_cached(client):
    response = client.get("/health/")

    assert "no-store" in response["Cache-Control"]

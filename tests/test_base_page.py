"""The page base: the layout every page builds on, its notices, and the state pages."""

import pytest
from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.template import engines
from django.test import Client
from django.urls import path

PAGE = """{% extends "base.html" %}
{% block title %}A page{% endblock %}
{% block body %}{% include "components/notices.html" %}{% endblock %}"""


def render_page(request):
    return HttpResponse(engines["django"].from_string(PAGE).render({}, request))


# The pages below are public: they only test the layout and show nothing private.


@login_not_required
def plain_page(request):
    return render_page(request)


@login_not_required
def page_with_message(request, level):
    messages.add_message(request, level, "Saved, or not.")
    return render_page(request)


@login_not_required
def refused_with_reason(request):
    raise PermissionDenied("This workshop is suspended.")


@login_not_required
def refused(request):
    raise PermissionDenied


@login_not_required
def broken(request):
    raise RuntimeError("This page breaks on purpose.")


urlpatterns = [
    path("page/", plain_page),
    path("message/<int:level>/", page_with_message),
    path("refused-with-reason/", refused_with_reason),
    path("refused/", refused),
    path("broken/", broken),
]

pytestmark = pytest.mark.urls(__name__)


def test_a_page_on_the_base_layout_loads_the_shared_css_and_the_busy_button(client):
    html = client.get("/page/").content.decode()

    for file in ("css/tokens.css", "css/base.css", "css/components.css", "js/busy.js"):
        assert f"/static/{file}" in html
    assert "<title>A page | WorkshopOS</title>" in html


@pytest.mark.parametrize(
    ("level", "look", "role"),
    [
        (messages.ERROR, "notice notice--danger", "alert"),
        (messages.WARNING, "notice notice--warning", "alert"),
        (messages.SUCCESS, "notice notice--success", "status"),
        (messages.INFO, "notice", "status"),
    ],
)
def test_a_message_shows_as_a_notice_of_its_level(client, level, look, role):
    html = client.get(f"/message/{level}/").content.decode()

    assert f'<div class="{look}" role="{role}">' in html
    assert '<p class="notice__text">Saved, or not.</p>' in html


def test_an_unknown_address_shows_our_page_not_found(client):
    response = client.get("/no-such-page/")

    assert response.status_code == 404
    assert "Page not found" in response.content.decode()


def test_a_refusal_that_says_why_shows_its_reason(client):
    response = client.get("/refused-with-reason/")

    assert response.status_code == 403
    html = response.content.decode()
    assert "Not allowed" in html
    assert "This workshop is suspended." in html


def test_a_refusal_with_no_reason_says_the_page_is_for_other_roles(client):
    response = client.get("/refused/")

    assert response.status_code == 403
    assert "Not open to your role" in response.content.decode()


def test_a_server_failure_shows_our_page_and_says_nothing_was_saved():
    client = Client(raise_request_exception=False)

    response = client.get("/broken/")

    assert response.status_code == 500
    assert "Nothing was saved." in response.content.decode()

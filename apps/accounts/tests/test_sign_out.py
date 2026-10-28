"""Signing out (apps/accounts/views.py, the sign-out card and templates/403.html)."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.views.defaults import permission_denied

from apps.accounts.tests.factories import MembershipFactory
from apps.workshops.models import WorkshopStatus

SIGN_OUT = "/sign-out/"


def signed_in(client):
    return "_auth_user_id" in client.session


def page(response):
    return response.content.decode()


@pytest.mark.django_db
def test_sign_40_sign_out_first_opens_a_card_and_signs_nobody_out(client):
    client.force_login(MembershipFactory().user)

    html = page(client.get(SIGN_OUT))

    assert "Sign out?" in html
    assert signed_in(client)


@pytest.mark.django_db
def test_sign_41_the_cards_one_sign_out_button_sends_a_post(client):
    client.force_login(MembershipFactory().user)

    html = page(client.get(SIGN_OUT))

    assert html.count('method="post"') == 1
    assert html.count('type="submit"') == 1
    client.post(SIGN_OUT)
    assert not signed_in(client)


@pytest.mark.django_db
def test_sign_42_signing_out_works_when_the_workshop_is_suspended(client):
    member = MembershipFactory(workshop__status=WorkshopStatus.SUSPENDED)
    client.force_login(member.user)

    assert client.get(SIGN_OUT).status_code == 200
    client.post(SIGN_OUT)
    assert not signed_in(client)


@pytest.mark.django_db
def test_sign_42_the_not_allowed_page_offers_sign_out_to_a_signed_in_person(client):
    member = MembershipFactory(workshop__status=WorkshopStatus.SUSPENDED)
    client.force_login(member.user)

    response = client.get("/")

    assert response.status_code == 403
    assert f'href="{SIGN_OUT}"' in page(response)


def test_sign_42_a_visitor_gets_no_sign_out_on_the_not_allowed_page(rf):
    request = rf.get("/")
    request.user = AnonymousUser()

    response = permission_denied(request, PermissionDenied())

    assert SIGN_OUT not in page(response)


@pytest.mark.django_db
def test_sign_43_after_signing_out_the_sign_in_page_shows(client):
    client.force_login(MembershipFactory().user)

    assert client.post(SIGN_OUT).url == "/sign-in/"


@pytest.mark.django_db
def test_the_card_tells_an_owner_they_need_a_new_code(client):
    client.force_login(MembershipFactory(owner=True).user)

    assert "a new code from your email" in page(client.get(SIGN_OUT))


@pytest.mark.django_db
def test_the_card_tells_office_and_floor_they_need_their_password(client):
    client.force_login(MembershipFactory().user)

    assert "your username and password" in page(client.get(SIGN_OUT))


@pytest.mark.django_db
def test_the_home_page_has_a_way_to_sign_out(client):
    client.force_login(MembershipFactory().user)

    assert f'href="{SIGN_OUT}"' in page(client.get("/"))

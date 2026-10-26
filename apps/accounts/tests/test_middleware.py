"""Each request gets its workshop, and every page is guarded (apps/accounts/middleware.py)."""

import pytest
from django.contrib import admin
from django.contrib.auth.decorators import login_not_required
from django.http import HttpResponse
from django.urls import path

from apps.accounts.decorators import workshop_not_required
from apps.accounts.tests.factories import MembershipFactory, UserFactory
from apps.workshops.models import WorkshopStatus


def workshop_page(request):
    return HttpResponse(request.workshop.name)


@workshop_not_required  # Like signing out: it works without a workshop.
def account_page(request):
    return HttpResponse(request.membership.get_role_display() if request.membership else "none")


@login_not_required
def public_page(request):
    return HttpResponse("public")


urlpatterns = [
    path("workshop/", workshop_page),
    path("account/", account_page),
    path("public/", public_page),
    path("admin/", admin.site.urls),
]


@pytest.fixture(autouse=True)
def these_pages(settings):
    settings.ROOT_URLCONF = __name__


@pytest.mark.django_db
def test_a_member_reaches_a_page_with_their_workshop(client):
    member = MembershipFactory()
    client.force_login(member.user)

    response = client.get("/workshop/")

    assert response.status_code == 200
    assert response.text == member.workshop.name


@pytest.mark.django_db
def test_an_account_without_a_workshop_is_refused(client):
    client.force_login(UserFactory())

    assert client.get("/workshop/").status_code == 403


@pytest.mark.django_db
def test_a_suspended_workshop_is_refused_except_where_no_workshop_is_needed(client):
    member = MembershipFactory(workshop__status=WorkshopStatus.SUSPENDED)
    client.force_login(member.user)

    assert client.get("/workshop/").status_code == 403
    assert client.get("/account/").text == "Floor"


@pytest.mark.django_db
def test_a_superuser_gets_no_workshop_even_with_a_membership(client):
    member = MembershipFactory()
    member.user.is_superuser = True
    member.user.save()
    client.force_login(member.user)

    assert client.get("/workshop/").status_code == 403
    assert client.get("/account/").text == "none"


@pytest.mark.django_db
def test_the_admin_and_public_pages_need_no_workshop(client):
    assert client.get("/public/").text == "public"

    client.force_login(UserFactory(is_staff=True, is_superuser=True))
    assert client.get("/admin/").status_code == 200


@pytest.mark.django_db
def test_a_visitor_is_sent_to_sign_in_first(client, settings):
    response = client.get("/workshop/")

    assert response.status_code == 302
    assert response.url.startswith(settings.LOGIN_URL)


@pytest.mark.django_db
def test_a_page_costs_one_query_for_its_workshop(client, django_assert_num_queries):
    member = MembershipFactory()
    client.force_login(member.user)

    # The session, the account, then the membership with its workshop.
    with django_assert_num_queries(3):
        client.get("/workshop/")

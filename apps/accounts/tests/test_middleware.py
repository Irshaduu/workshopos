"""Each request gets its workshop, every page is guarded by its mark, and signed-in
pages stay out of the browser's cache (apps/accounts/middleware.py)."""

import pytest
from django.contrib import admin
from django.contrib.auth.decorators import login_not_required
from django.http import HttpResponse
from django.urls import path

from apps.accounts.decorators import page, workshop_not_required
from apps.accounts.models import Role
from apps.accounts.roles import PERMISSIONS
from apps.accounts.tests.factories import MembershipFactory, UserFactory
from apps.workshops.models import Branch, WorkshopStatus


@page("roles", "jobs.see_live_board")
def workshop_page(request):
    return HttpResponse(request.workshop.name)


@page("roles")
@workshop_not_required  # Like signing out: it works without a workshop.
def account_page(request):
    return HttpResponse(request.membership.get_role_display() if request.membership else "none")


@login_not_required
def public_page(request):
    return HttpResponse("public")


def page_with_no_mark(request):
    return HttpResponse("nobody should see this")


@page("roles")
def workshop_page_with_no_permission(request):
    return HttpResponse("nobody should see this")


@page("no_such_module", "jobs.see_live_board")
def page_of_an_unknown_module(request):
    return HttpResponse("nobody should see this")


@page("roles", "tests.see_money")
def money_page(request):
    return HttpResponse("money")


@page("roles", "jobs.see_live_board")
def branch_page(request):
    # It asks twice, as a page with a list and a total would.
    names = [request.branch.name, request.branch.name]
    return HttpResponse(names[0])


@page("roles")
@workshop_not_required  # Like signing out: it works without a workshop.
def branch_or_none_page(request):
    return HttpResponse(request.branch.name if request.branch else "none")


urlpatterns = [
    path("workshop/", workshop_page),
    path("account/", account_page),
    path("branch/", branch_page),
    path("branch-or-none/", branch_or_none_page),
    path("public/", public_page),
    path("no-mark/", page_with_no_mark),
    path("no-permission/", workshop_page_with_no_permission),
    path("unknown-module/", page_of_an_unknown_module),
    path("money/", money_page),
    path("admin/", admin.site.urls),
]


@pytest.fixture(autouse=True)
def these_pages(settings, monkeypatch):
    settings.ROOT_URLCONF = __name__
    # A permission for these tests only: Owner and Office have it, Floor does not.
    monkeypatch.setitem(PERMISSIONS, "tests.see_money", frozenset({Role.OWNER, Role.OFFICE}))


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

    # The session, the account, then the membership with its workshop. Then
    # the session is saved again, to move its end date 40 days on (SIGN-36):
    # one update, inside a savepoint and its release.
    with django_assert_num_queries(6):
        client.get("/workshop/")


@pytest.mark.django_db
def test_a_member_reaches_a_page_with_their_workshops_branch(client):
    member = MembershipFactory()
    client.force_login(member.user)

    assert client.get("/branch/").text == Branch.objects.for_workshop(member.workshop).get().name


@pytest.mark.django_db
def test_a_page_that_asks_for_its_branch_costs_one_more_query_however_often_it_asks(
    client, django_assert_num_queries
):
    client.force_login(MembershipFactory().user)

    # The 6 of a page that never asks (test_a_page_costs_one_query_for_its_workshop),
    # and the branch.
    with django_assert_num_queries(7):
        client.get("/branch/")


@pytest.mark.django_db
def test_platform_staff_get_no_branch(client):
    client.force_login(UserFactory(is_staff=True))

    assert client.get("/branch-or-none/").text == "none"


@pytest.mark.django_db
def test_a_signed_in_page_is_never_kept_by_the_browser(client):
    # So Back, after signing out on a shared device, shows nothing private.
    client.force_login(MembershipFactory().user)

    cache_control = client.get("/workshop/")["Cache-Control"]

    assert "no-store" in cache_control
    assert "private" in cache_control


@pytest.mark.django_db
def test_a_refused_page_is_never_kept_either(client):
    client.force_login(UserFactory())

    response = client.get("/workshop/")

    assert response.status_code == 403
    assert "no-store" in response["Cache-Control"]


def test_a_page_for_visitors_is_left_alone(client):
    assert not client.get("/public/").has_header("Cache-Control")


@pytest.mark.django_db
def test_role_8_a_page_with_no_mark_is_refused_to_everyone(client):
    client.force_login(MembershipFactory(owner=True).user)

    assert client.get("/no-mark/").status_code == 403


@pytest.mark.django_db
def test_role_8_a_workshop_page_that_names_no_permission_is_refused(client):
    client.force_login(MembershipFactory(owner=True).user)

    assert client.get("/no-permission/").status_code == 403


@pytest.mark.django_db
def test_role_6_a_page_of_a_module_not_in_the_list_is_refused(client):
    client.force_login(MembershipFactory(owner=True).user)

    assert client.get("/unknown-module/").status_code == 403


@pytest.mark.django_db
def test_role_9_a_role_without_the_permission_is_told_the_page_is_not_for_it(client):
    client.force_login(MembershipFactory(role=Role.FLOOR).user)

    response = client.get("/money/")

    assert response.status_code == 403
    assert "Not open to your role" in response.text


@pytest.mark.django_db
def test_role_9_a_role_with_the_permission_gets_in(client):
    client.force_login(MembershipFactory(role=Role.OFFICE).user)

    assert client.get("/money/").text == "money"

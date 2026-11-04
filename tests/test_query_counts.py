"""A longer list never means more queries (docs/PLAN.md, Phase 5).

A page that asks the database once for each row gets slower with every row, and
nobody sees it until a workshop has thousands of them. So each page that shows rows
is opened with a few rows and with many, and must make the same number of queries.

Like the permission matrix, this test finds every page by itself, so a new page must
say here whether it shows rows.
"""

import pytest
from django.contrib.auth.decorators import login_not_required
from django.db import connection
from django.http import HttpResponse
from django.test.utils import CaptureQueriesContext
from django.urls import path, reverse
from test_permissions import PAGES

from apps.accounts.tests.factories import MembershipFactory
from apps.staff.tests.factories import StaffMemberFactory
from apps.workshops.models import Branch
from apps.workshops.tests.factories import BranchFactory

FEW = 2
MANY = 12

#: Pages that show no rows.
NO_ROWS = {
    "accounts:home",
    "accounts:sign_in",
    "accounts:sign_in_code",
    "accounts:sign_in_password",
    "accounts:sign_out",
    # These four answer a GET by going to the list. A refused send shows the list
    # through the same selector, and apps/staff/tests/test_pages.py opens it both ways.
    "staff:new",
    "staff:edit",
    "staff:turn_off",
    "staff:turn_on",
}


def staff_list_rows(member):
    return reverse("staff:list"), lambda: StaffMemberFactory(workshop=member.workshop)


#: Each page that shows rows. The function gets a signed-in owner's membership, and
#: answers with the page's address and a function that adds one row to it.
WITH_ROWS = {
    "staff:list": staff_list_rows,
}


def queries_of(client, address):
    """The SQL of one visit to this page, and the page."""
    with CaptureQueriesContext(connection) as queries:
        response = client.get(address)
    assert response.status_code == 200, f"{address} answered {response.status_code}."
    return [query["sql"] for query in queries.captured_queries], response.content


def assert_same_queries(client, address, add_row):
    """The page makes the same number of queries with a few rows and with many."""
    for _ in range(FEW):
        add_row()
    few, few_page = queries_of(client, address)
    for _ in range(MANY - FEW):
        add_row()
    many, many_page = queries_of(client, address)

    # So a row added where the page never looks cannot pass for a good page.
    assert len(many_page) > len(few_page), f"The new rows never reached {address}."
    assert len(many) == len(few), (
        f"{address} made {len(few)} queries with {FEW} rows and {len(many)} with {MANY}:\n"
        + "\n".join(many)
    )


def test_every_page_says_whether_it_shows_rows():
    assert PAGES, "The walk found no page."
    assert sorted(NO_ROWS | WITH_ROWS.keys()) == PAGES
    assert not NO_ROWS & WITH_ROWS.keys()


@pytest.mark.django_db
@pytest.mark.parametrize("name", sorted(WITH_ROWS))
def test_a_longer_list_means_no_more_queries(client, name):
    member = MembershipFactory(owner=True)
    client.force_login(member.user)

    address, add_row = WITH_ROWS[name](member)

    assert_same_queries(client, address, add_row)


# Planted pages, to prove the check catches what it must. They are public: they only
# test the check and show nothing private.


@login_not_required
def one_query_for_all_rows(request):
    return HttpResponse(", ".join(branch.name for branch in Branch.objects.order_by("name")))


@login_not_required
def one_query_for_each_row(request):
    keys = Branch.objects.values_list("pk", flat=True)
    return HttpResponse(", ".join(Branch.objects.get(pk=key).name for key in keys))


@login_not_required
def rows_never_shown(request):
    return HttpResponse("No rows here.")


urlpatterns = [
    path("good/", one_query_for_all_rows),
    path("bad/", one_query_for_each_row),
    path("empty/", rows_never_shown),
]


@pytest.mark.django_db
@pytest.mark.urls(__name__)
def test_a_page_with_one_query_for_all_rows_passes(client):
    assert_same_queries(client, "/good/", BranchFactory)


@pytest.mark.django_db
@pytest.mark.urls(__name__)
def test_a_page_with_one_query_for_each_row_is_caught(client):
    with pytest.raises(AssertionError, match="made 3 queries with 2 rows and 13 with 12"):
        assert_same_queries(client, "/bad/", BranchFactory)


@pytest.mark.django_db
@pytest.mark.urls(__name__)
def test_rows_that_never_reach_the_page_are_caught(client):
    with pytest.raises(AssertionError, match="never reached"):
        assert_same_queries(client, "/empty/", BranchFactory)


@pytest.mark.django_db
@pytest.mark.urls(__name__)
def test_a_page_that_is_refused_is_caught(client):
    with pytest.raises(AssertionError, match="answered 404"):
        assert_same_queries(client, "/no-such-page/", BranchFactory)

"""The permission matrix: every page, for every kind of visitor (ADR-0026).

It finds every page by itself, from the project's own list of addresses, so
a new page with no row fails here. Each answer is typed by hand, never read
from the permission lists: this test is the second opinion on them.

A page that shows a record will also be asked for a record of another
workshop, and must answer "Not found" (ROLE-10). The first such page is the
Staff list (Slice 1, step 4); its row brings that part of the test.
"""

from urllib.parse import urlsplit

import pytest
from django.urls import URLPattern, URLResolver, get_resolver, resolve, reverse

from apps.accounts.models import Role
from apps.accounts.tests.factories import MembershipFactory, UserFactory
from apps.workshops.modules import MODULES

#: Addresses that are not pages of the app, and why.
NOT_PAGES = {
    "admin": "the Django admin: for platform staff only, with its own checks (ADR-0023)",
    "health": "the host's health check: public, and part of no module (ADR-0014)",
}

SIGNED_OUT = "signed out"
OWNER = "owner"
OFFICE = "office"
FLOOR = "floor"
STAFF = "platform staff"
SUPERUSER = "superuser"
VISITORS = (SIGNED_OUT, OWNER, OFFICE, FLOOR, STAFF, SUPERUSER)

#: Where a visitor is sent: the sign-in page, or the home page.
TO_SIGN_IN = "/sign-in/"
TO_HOME = "/"

#: Each page's answer for each visitor: a status code, or the page it sends
#: them to. Typed by hand.
MATRIX = {
    "accounts:home": {
        SIGNED_OUT: TO_SIGN_IN,
        OWNER: 200,
        OFFICE: 200,
        FLOOR: 200,
        STAFF: 403,
        SUPERUSER: 403,
    },
    # The sign-in steps: public; a signed-in person goes home (SIGN-12), and a
    # later step opened first goes back to step 1 (SIGN-26).
    "accounts:sign_in": {
        SIGNED_OUT: 200,
        OWNER: TO_HOME,
        OFFICE: TO_HOME,
        FLOOR: TO_HOME,
        STAFF: TO_HOME,
        SUPERUSER: TO_HOME,
    },
    "accounts:sign_in_code": {
        SIGNED_OUT: TO_SIGN_IN,
        OWNER: TO_HOME,
        OFFICE: TO_HOME,
        FLOOR: TO_HOME,
        STAFF: TO_HOME,
        SUPERUSER: TO_HOME,
    },
    "accounts:sign_in_password": {
        SIGNED_OUT: TO_SIGN_IN,
        OWNER: TO_HOME,
        OFFICE: TO_HOME,
        FLOOR: TO_HOME,
        STAFF: TO_HOME,
        SUPERUSER: TO_HOME,
    },
    # Signing out works for every account, with or without a workshop (SIGN-42).
    "accounts:sign_out": {
        SIGNED_OUT: TO_SIGN_IN,
        OWNER: 200,
        OFFICE: 200,
        FLOOR: 200,
        STAFF: 200,
        SUPERUSER: 200,
    },
}


def found_pages(resolver=None, prefix=""):
    """Every address in the project, by name, like "accounts:home"."""
    for item in (resolver or get_resolver()).url_patterns:
        if isinstance(item, URLResolver):
            if item.namespace in NOT_PAGES:
                continue
            yield from found_pages(item, f"{prefix}{item.namespace}:" if item.namespace else prefix)
        elif isinstance(item, URLPattern):
            assert item.name, f"Give every page a name: {item.pattern} has none."
            if item.name not in NOT_PAGES:
                yield f"{prefix}{item.name}"


PAGES = sorted(found_pages())


def view_of(name):
    return resolve(reverse(name)).func


def visitor_account(visitor):
    """A signed-in account for this kind of visitor; None when signed out."""
    if visitor == SIGNED_OUT:
        return None
    if visitor == STAFF:
        return UserFactory(is_staff=True)
    if visitor == SUPERUSER:
        return UserFactory(is_staff=True, is_superuser=True)
    return MembershipFactory(role=Role(visitor)).user


def test_every_page_has_a_row_and_every_row_a_page():
    assert PAGES, "The walk found no page."
    assert sorted(MATRIX) == PAGES


@pytest.mark.parametrize("name", PAGES)
def test_role_6_every_page_names_a_module_from_the_list(name):
    mark = getattr(view_of(name), "page_mark", None)

    assert mark is not None, f"{name} has no page mark."
    assert mark.module in MODULES, f"{name} names {mark.module!r}, which is not in the list."


@pytest.mark.parametrize("name", PAGES)
def test_role_8_every_page_that_needs_a_workshop_names_a_permission(name):
    view = view_of(name)
    public = not getattr(view, "login_required", True)
    needs_a_workshop = getattr(view, "workshop_required", True)

    if not public and needs_a_workshop:
        assert view.page_mark.permission, f"{name} needs a workshop but names no permission."


@pytest.mark.django_db
@pytest.mark.parametrize("visitor", VISITORS)
@pytest.mark.parametrize("name", PAGES)
def test_role_9_each_visitor_gets_in_or_is_refused(client, name, visitor):
    account = visitor_account(visitor)
    if account is not None:
        client.force_login(account)

    response = client.get(reverse(name))

    expected = MATRIX[name][visitor]
    if isinstance(expected, int):
        assert response.status_code == expected
    else:
        assert response.status_code == 302
        assert urlsplit(response.url).path == expected

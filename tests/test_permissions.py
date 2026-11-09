"""The permission matrix: every page, for every kind of visitor (ADR-0026).

It finds every page by itself, from the project's own list of addresses, so
a new page with no row fails here. Each answer is typed by hand, never read
from the permission lists: this test is the second opinion on them.

A page with a record's key in its address is also asked for a record of another
workshop, of another branch, and for a key that does not exist. Each must answer
"Not found" and change nothing (ROLE-10). The first such pages are the Staff list's.

A page that only shows refuses a save, so a read-only role added later can never
save (ROLE-5). A form never hides a field a role may not change (ROLE-13).
"""

import uuid
from functools import partial
from urllib.parse import urlsplit

import pytest
from django import forms
from django.forms.models import model_to_dict
from django.urls import URLPattern, URLResolver, get_resolver, reverse
from test_queries import form_classes

from apps.accounts.models import Role
from apps.accounts.selectors import membership_of
from apps.accounts.tests.factories import MembershipFactory, UserFactory
from apps.jobs.tests.factories import JobCardFactory
from apps.staff.tests.factories import StaffMemberFactory
from apps.workshops.models import Branch
from apps.workshops.modules import MODULES
from apps.workshops.tests.factories import BranchFactory, WorkshopFactory

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

#: Where a visitor is sent: the sign-in page, the home page, or the Staff list.
TO_SIGN_IN = "/sign-in/"
TO_HOME = "/"
TO_STAFF_LIST = "/staff/"
TO_NEW_JOB_CARD = "/job-cards/new/"

#: A page's answer when only owners may in, and a GET goes on to this page.
ONLY_OWNERS_GO_TO_STAFF_LIST = {
    SIGNED_OUT: TO_SIGN_IN,
    OWNER: TO_STAFF_LIST,
    OFFICE: 403,
    FLOOR: 403,
    STAFF: 403,
    SUPERUSER: 403,
}

#: A page's answer when every role of a workshop may in.
EVERY_ROLE_OPENS = {
    SIGNED_OUT: TO_SIGN_IN,
    OWNER: 200,
    OFFICE: 200,
    FLOOR: 200,
    STAFF: 403,
    SUPERUSER: 403,
}

#: Each page's answer for each visitor: a status code, or the page it sends
#: them to. Typed by hand.
MATRIX = {
    # The home page, and a job card's pages: every role makes and changes job cards
    # (JOB-53).
    "jobs:live_board": EVERY_ROLE_OPENS,
    "jobs:new": EVERY_ROLE_OPENS,
    "jobs:edit": EVERY_ROLE_OPENS,
    # A known plate fills a new card for every role (KNOWN-18).
    "jobs:known_plate": EVERY_ROLE_OPENS,
    # A GET on a new key that is not saved goes back to the form, so a session that ended
    # while someone saved comes back to a real page (SIGN-38).
    "jobs:create": {
        SIGNED_OUT: TO_SIGN_IN,
        OWNER: TO_NEW_JOB_CARD,
        OFFICE: TO_NEW_JOB_CARD,
        FLOOR: TO_NEW_JOB_CARD,
        STAFF: 403,
        SUPERUSER: 403,
    },
    # Only Office and owners cancel (JOB-50).
    "jobs:cancel": {
        SIGNED_OUT: TO_SIGN_IN,
        OWNER: 200,
        OFFICE: 200,
        FLOOR: 403,
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
    # Only owners open the Staff list (STAFF-18).
    "staff:list": {
        SIGNED_OUT: TO_SIGN_IN,
        OWNER: 200,
        OFFICE: 403,
        FLOOR: 403,
        STAFF: 403,
        SUPERUSER: 403,
    },
    # The addresses that save. A GET goes to the list, so a session that ended while
    # someone saved comes back to a real page (SIGN-38).
    "staff:new": ONLY_OWNERS_GO_TO_STAFF_LIST,
    "staff:edit": ONLY_OWNERS_GO_TO_STAFF_LIST,
    "staff:turn_off": ONLY_OWNERS_GO_TO_STAFF_LIST,
    "staff:turn_on": ONLY_OWNERS_GO_TO_STAFF_LIST,
}

#: Each page that finds a record by the key in its address, and how to make such a
#: record, in the state the page would change. A new one adds its line here.
RECORD_PAGES = {
    "jobs:edit": JobCardFactory,
    "jobs:cancel": JobCardFactory,
    "staff:edit": StaffMemberFactory,
    "staff:turn_off": StaffMemberFactory,
    "staff:turn_on": partial(StaffMemberFactory, is_active=False),
}

#: Each page whose key is a new record's, not yet saved (ADR-0022).
NEW_KEY_PAGES = {"staff:new", "jobs:create"}

#: A permission that starts with one of these only shows (ROLE-5).
SHOWING_WORDS = ("see_", "open_")


def found_pages(resolver=None, prefix=""):
    """Every address in the project, by name, like "staff:list", with its view."""
    for item in (resolver or get_resolver()).url_patterns:
        if isinstance(item, URLResolver):
            if item.namespace in NOT_PAGES:
                continue
            yield from found_pages(item, f"{prefix}{item.namespace}:" if item.namespace else prefix)
        elif isinstance(item, URLPattern):
            assert item.name, f"Give every page a name: {item.pattern} has none."
            if item.name not in NOT_PAGES:
                yield f"{prefix}{item.name}", item


FOUND = dict(found_pages())
PAGES = sorted(FOUND)
VIEWS = {name: found.callback for name, found in FOUND.items()}


def address_of(name, workshop):
    """The page's address, with a key of this workshop's when the page has one."""
    if name in NEW_KEY_PAGES:
        return reverse(name, kwargs={"key": uuid.uuid7()})
    if name in RECORD_PAGES:
        return reverse(name, kwargs={"key": RECORD_PAGES[name](workshop=workshop).pk})
    return reverse(name)


def only_shows(name):
    # A page with no mark is reported by its own test, not here.
    mark = getattr(VIEWS[name], "page_mark", None)
    return mark is not None and bool(mark.permission) and showing(mark.permission)


def showing(permission):
    return permission.split(".")[1].startswith(SHOWING_WORDS)


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
    mark = getattr(VIEWS[name], "page_mark", None)

    assert mark is not None, f"{name} has no page mark."
    assert mark.module in MODULES, f"{name} names {mark.module!r}, which is not in the list."


@pytest.mark.parametrize("name", PAGES)
def test_role_8_every_page_that_needs_a_workshop_names_a_permission(name):
    view = VIEWS[name]
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
    # A key of the visitor's own workshop, so only the role decides the answer.
    membership = membership_of(account) if account is not None else None
    workshop = membership.workshop if membership else WorkshopFactory()

    response = client.get(address_of(name, workshop))

    expected = MATRIX[name][visitor]
    if isinstance(expected, int):
        assert response.status_code == expected
    else:
        assert response.status_code == 302
        assert urlsplit(response.url).path == expected


def test_role_10_every_page_with_a_key_says_what_its_key_is():
    with_a_key = {name for name, found in FOUND.items() if found.pattern.converters}

    assert with_a_key == RECORD_PAGES.keys() | NEW_KEY_PAGES


def changed_by_a_send(client, name, key):
    """The answer to a GET and a POST for this key. A POST carries what the page's form
    would, so nothing but the key can refuse it."""
    address = reverse(name, kwargs={"key": key})
    typed = {"name": "Changed", "designation": "general_helper"}
    return client.get(address).status_code, client.post(address, typed).status_code


@pytest.mark.django_db
@pytest.mark.parametrize("name", sorted(RECORD_PAGES))
def test_role_10_a_record_of_another_workshop_is_not_found_and_stays_as_it_was(client, name):
    client.force_login(MembershipFactory(owner=True).user)
    theirs = RECORD_PAGES[name]()
    before = model_to_dict(theirs)

    assert changed_by_a_send(client, name, theirs.pk) == (404, 404)

    theirs.refresh_from_db()
    assert model_to_dict(theirs) == before


@pytest.mark.django_db
@pytest.mark.parametrize("name", sorted(RECORD_PAGES))
def test_role_10_a_record_of_another_branch_is_not_found_and_stays_as_it_was(client, name):
    # Today every page works in the workshop's first branch (branch_of()).
    member = MembershipFactory(owner=True)
    client.force_login(member.user)
    there = BranchFactory(workshop=member.workshop)
    assert Branch.objects.for_workshop(member.workshop).first() != there
    other = RECORD_PAGES[name](workshop=member.workshop, branch=there)
    before = model_to_dict(other)

    assert changed_by_a_send(client, name, other.pk) == (404, 404)

    other.refresh_from_db()
    assert model_to_dict(other) == before


@pytest.mark.django_db
@pytest.mark.parametrize("name", sorted(RECORD_PAGES))
def test_role_10_a_key_that_does_not_exist_answers_the_same(client, name):
    client.force_login(MembershipFactory(owner=True).user)

    assert changed_by_a_send(client, name, uuid.uuid7()) == (404, 404)


def test_role_5_a_showing_page_exists_to_check():
    assert [name for name in PAGES if only_shows(name)]


@pytest.mark.django_db
@pytest.mark.parametrize("name", [name for name in PAGES if only_shows(name)])
def test_role_5_a_page_that_only_shows_refuses_a_save(client, name):
    member = MembershipFactory(owner=True)
    client.force_login(member.user)

    assert client.post(address_of(name, member.workshop)).status_code == 405


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name",
    [
        name
        for name in PAGES
        if getattr(VIEWS[name], "page_mark", None)
        and VIEWS[name].page_mark.permission
        and not only_shows(name)
    ],
)
def test_role_5_a_page_with_any_other_permission_really_takes_a_save(client, name):
    # So a page that only shows cannot pass for a saving one under another word, like
    # list_staff, and get past the test above.
    member = MembershipFactory(owner=True)
    client.force_login(member.user)

    assert client.post(address_of(name, member.workshop)).status_code != 405


def hidden_fields(form_class):
    return [name for name, field in form_class.base_fields.items() if field.widget.is_hidden]


def test_role_13_no_form_hides_a_field():
    found_forms = form_classes()
    # A floor, so a search that found nothing cannot pass for being clean.
    assert found_forms

    found = {form: names for form in found_forms if (names := hidden_fields(form))}

    assert found == {}, "Leave the field out of this role's form, never hide it."


def test_role_13_a_hidden_field_is_caught():
    class PlantedForm(forms.Form):
        shown = forms.CharField()
        price = forms.CharField(widget=forms.HiddenInput)

    assert hidden_fields(PlantedForm) == ["price"]

"""Roles: fixed in the code, and asked through Django's has_perm (ADR-0026).

Every page is checked once, for every kind of visitor, by the permission
matrix (tests/test_permissions.py). These tests check the parts under it.
"""

import re
from pathlib import Path

import pytest
from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.auth.models import Permission

from apps.accounts.models import Role, User
from apps.accounts.roles import PERMISSIONS, add_permissions
from apps.accounts.tests.factories import MembershipFactory, UserFactory


@pytest.fixture
def see_money(monkeypatch):
    """A permission for these tests only: Owner and Office have it, Floor does not."""
    monkeypatch.setitem(PERMISSIONS, "tests.see_money", frozenset({Role.OWNER, Role.OFFICE}))
    return "tests.see_money"


def fresh(user):
    """The account loaded again, as each request loads it."""
    return User.objects.get(pk=user.pk)


def test_role_1_a_workshop_has_three_roles_fixed_in_the_code():
    assert Role.values == ["owner", "office", "floor"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role", "has_it"), [(Role.OWNER, True), (Role.OFFICE, True), (Role.FLOOR, False)]
)
def test_role_7_a_member_has_the_permissions_listed_for_their_role(see_money, role, has_it):
    member = MembershipFactory(role=role)

    assert fresh(member.user).has_perm(see_money) is has_it


@pytest.mark.django_db
def test_role_7_a_permission_nobody_listed_is_a_no(see_money):
    owner = fresh(MembershipFactory(owner=True).user)

    assert not owner.has_perm("tests.see_everything")


@pytest.mark.django_db
def test_role_7_templates_ask_the_same_list(see_money):
    office = fresh(MembershipFactory(role=Role.OFFICE).user)

    assert office.has_module_perms("tests")
    assert not office.has_module_perms("billing")


@pytest.mark.django_db
def test_a_turned_off_account_has_no_permission(see_money):
    member = MembershipFactory(owner=True, user__is_active=False)

    account = fresh(member.user)
    assert not account.has_perm(see_money)
    assert account.get_all_permissions() == set()


@pytest.mark.django_db
def test_djangos_async_check_reads_the_same_list(see_money):
    office = fresh(MembershipFactory(role=Role.OFFICE).user)
    office.has_perm(see_money)  # reads the membership here, in the test's own thread

    assert async_to_sync(office.ahas_perm)(see_money)


@pytest.mark.django_db
def test_role_4_an_account_with_no_workshop_has_no_permission(see_money):
    assert not fresh(UserFactory()).has_perm(see_money)


@pytest.mark.django_db
def test_role_4_platform_staff_keep_djangos_own_permissions_for_the_admin(see_money):
    staff = UserFactory(is_staff=True)
    staff.user_permissions.add(Permission.objects.get(codename="view_user"))

    staff = fresh(staff)
    assert staff.has_perm("accounts.view_user")
    assert not staff.has_perm(see_money)


@pytest.mark.django_db
def test_role_4_a_member_never_gets_djangos_own_permissions():
    member = MembershipFactory(owner=True)
    member.user.user_permissions.add(Permission.objects.get(codename="view_user"))

    assert not fresh(member.user).has_perm("accounts.view_user")


@pytest.mark.django_db
def test_role_11_asking_twenty_times_costs_what_asking_once_costs(
    see_money, django_assert_num_queries
):
    office = fresh(MembershipFactory(role=Role.OFFICE).user)

    # The one query: the membership, with its workshop.
    with django_assert_num_queries(1):
        for _ in range(20):
            office.has_perm(see_money)


def test_a_permission_never_starts_with_djangos_own_words():
    with pytest.raises(ValueError, match="Django's own words"):
        add_permissions("tests", {"view_bills": {Role.OWNER}})


def test_a_permission_names_at_least_one_known_role():
    with pytest.raises(ValueError, match="No role"):
        add_permissions("tests", {"see_bills": set()})
    with pytest.raises(ValueError):
        add_permissions("tests", {"see_bills": {"storekeeper"}})


# ---------------------------------------------------------------------------
# Scans of the code: a role checked by its name is invisible to every other
# kind of test (v1's lesson, test_role_rule.py).

APPS = Path(settings.BASE_DIR) / "apps"

# A role compared, in Python or in a template: Role.OWNER, role == "owner",
# membership.role in [...], is_owner(...).
ROLE_CHECK = re.compile(r"\bRole\.[A-Z]+\b|\.role\s*(==|!=)|\.role\s+(not\s+)?in\b|\bis_owner\(")

# A shortcut for every role, which would hand a role added later every
# permission written with it.
EVERY_ROLE = re.compile(r"\bRole\.(values|choices|names|labels)\b|\(\s*Role\s*\)|\bin\s+Role\b")


def pages_code():
    """Every view, form and template: the code of the pages."""
    found = [*APPS.glob("*/views.py"), *APPS.glob("*/forms.py")]
    found += APPS.glob("*/templates/**/*.html")
    found += (Path(settings.BASE_DIR) / "templates").glob("**/*.html")
    return found


def test_role_7_no_page_checks_a_role_by_its_name():
    files = pages_code()
    # A floor, so a scan that read nothing cannot pass for being clean.
    assert len(files) >= 10, files

    found = [
        f"{path.relative_to(settings.BASE_DIR)}:{number}: {line.strip()}"
        for path in files
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if ROLE_CHECK.search(line)
    ]

    assert not found, "Ask a permission (has_perm, perms) instead:\n" + "\n".join(found)


def test_role_5_a_permission_list_names_each_role_one_by_one():
    files = list(APPS.glob("*/permissions.py"))
    assert files

    found = [
        f"{path.relative_to(settings.BASE_DIR)}:{number}: {line.strip()}"
        for path in files
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if EVERY_ROLE.search(line)
    ]

    assert not found, "Name each role, so a role added later starts with none:\n" + "\n".join(found)

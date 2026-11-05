"""The tab bar and the menu on every page of the app (apps/accounts/menu.py).

Opening and closing the menu needs a browser: that test comes with Playwright
(step 10 of Slice 1). Until then it is clicked through by hand.
"""

import pytest
from django.http import HttpResponse
from django.template import engines
from django.urls import include, path, resolve, reverse

from apps.accounts import menu
from apps.accounts.decorators import page
from apps.accounts.menu import ROLE_MENUS, Link, RoleMenu, Section
from apps.accounts.models import Role
from apps.accounts.roles import PERMISSIONS
from apps.accounts.tests.factories import MembershipFactory, UserFactory

APP_PAGE = """{% extends "app.html" %}
{% block title %}A page{% endblock %}
{% block content %}<p>A page</p>{% endblock %}"""


def render_app_page(request):
    return HttpResponse(engines["django"].from_string(APP_PAGE).render({}, request))


@page("roles", "tests.see_money")
def money_page(request):
    return render_app_page(request)


@page("roles", "tests.see_profit")
def profit_page(request):
    return render_app_page(request)


@page("roles", "tests.see_stock")
def stock_page(request):
    return render_app_page(request)


@page("roles", "tests.see_stock")
def home_page(request):
    return render_app_page(request)


urlpatterns = [
    path("", include("apps.accounts.urls")),
    path("", home_page, name="home"),
    path("money/", money_page, name="money"),
    path("profit/", profit_page, name="profit"),
    path("stock/", stock_page, name="stock"),
    path("stock/low/", stock_page, name="low_stock"),
    path("shops/", stock_page, name="shops"),
]

HOME = Link("home", "Home", "house")
MONEY = Link("money", "Money", "wallet")
STOCK = Link("stock", "Stock", "package")
LOW_STOCK = Link("low_stock", "Low stock", "triangle-alert")
SHOPS = Link("shops", "Shops", "cog")
PROFIT = Link("profit", "Profit", "trending-up")

#: Like v1: Owner and Office share one shape, and Floor has its own, where a
#: tab owns the stock pages.
OFFICE_SHAPE = RoleMenu(
    tabs=(HOME, MONEY),
    menu_word="Manage",
    sections=(
        Section("Stock", groups=((STOCK,), (SHOPS,))),
        Section("Insights", groups=((PROFIT,),)),
    ),
)
SAMPLE_MENUS = {
    Role.OWNER: OFFICE_SHAPE,
    Role.OFFICE: OFFICE_SHAPE,
    Role.FLOOR: RoleMenu(
        tabs=(HOME, STOCK),
        menu_word="Menu",
        sections=(Section("Stock", groups=((LOW_STOCK,),)),),
    ),
}


@pytest.fixture
def sample_app(settings, monkeypatch):
    """These pages and these tabs. Money is for Owner and Office, profit for owners,
    stock for every role."""
    settings.ROOT_URLCONF = __name__
    monkeypatch.setattr(menu, "ROLE_MENUS", SAMPLE_MENUS)
    monkeypatch.setitem(PERMISSIONS, "tests.see_money", frozenset({Role.OWNER, Role.OFFICE}))
    monkeypatch.setitem(PERMISSIONS, "tests.see_profit", frozenset({Role.OWNER}))
    monkeypatch.setitem(PERMISSIONS, "tests.see_stock", frozenset(set(Role)))


def signed_in(client, role):
    client.force_login(MembershipFactory(role=role).user)
    return client


def bar_of(response):
    html = response.text
    return html[html.index('<nav class="tab-bar"') : html.index("</nav>")]


def menu_of(response):
    html = response.text
    return html[html.index('<dialog class="menu"') : html.index("</dialog>")]


def test_role_5_every_role_has_its_tab_bar_and_menu():
    assert set(ROLE_MENUS) == set(Role)


def test_role_32_every_tab_and_row_names_a_page_that_exists_and_has_a_mark():
    for role_menu in ROLE_MENUS.values():
        rows = [row for section in role_menu.sections for group in section.groups for row in group]
        for link in [*role_menu.tabs, *rows]:
            assert resolve(reverse(link.page)).func.page_mark


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role", "word"), [(Role.OWNER, "Owner"), (Role.OFFICE, "Office"), (Role.FLOOR, "Floor")]
)
def test_role_25_the_home_tab_is_named_after_the_role(client, role, word):
    bar = bar_of(signed_in(client, role).get("/"))

    assert f'<span class="tab__label">{word}</span>' in bar
    assert "Admin" not in bar


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role", "word"), [(Role.OWNER, "Manage"), (Role.OFFICE, "Manage"), (Role.FLOOR, "Menu")]
)
def test_role_24_the_last_tab_opens_the_menu_with_v1s_word(client, role, word):
    bar = bar_of(signed_in(client, role).get("/"))

    assert 'aria-controls="app-menu"' in bar
    assert f'<span class="tab__label">{word}</span>' in bar


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role", "tab_shown", "row_shown"),
    [(Role.OWNER, True, True), (Role.OFFICE, True, False)],
)
def test_role_12_a_tab_or_row_shows_only_to_the_roles_its_page_lets_in(
    client, sample_app, role, tab_shown, row_shown
):
    response = signed_in(client, role).get("/")

    assert ('href="/money/"' in bar_of(response)) is tab_shown
    assert ('href="/profit/"' in menu_of(response)) is row_shown


@pytest.mark.django_db
def test_role_12_a_door_the_page_refuses_is_never_offered(client, sample_app):
    client = signed_in(client, Role.FLOOR)

    response = client.get("/")

    assert 'href="/money/"' not in response.text
    assert client.get("/money/").status_code == 403


@pytest.mark.django_db
def test_role_28_the_home_page_lights_its_own_tab_only(client, sample_app):
    bar = bar_of(signed_in(client, Role.OWNER).get("/"))

    assert '<a class="tab" href="/" aria-current="page">' in bar
    assert bar.count('aria-current="page"') == 1
    assert "data-lit" not in bar


@pytest.mark.django_db
def test_role_28_a_page_with_its_own_tab_lights_that_tab(client, sample_app):
    bar = bar_of(signed_in(client, Role.OWNER).get("/money/"))

    assert '<a class="tab" href="/money/" aria-current="page">' in bar
    assert bar.count('aria-current="page"') == 1
    assert "data-lit" not in bar


@pytest.mark.django_db
def test_role_28_and_37_a_page_from_the_menu_lights_the_menu_tab_and_its_row(client, sample_app):
    response = signed_in(client, Role.OWNER).get("/stock/")

    assert "aria-current" not in bar_of(response)
    assert "data-lit" in bar_of(response)
    assert '<a class="menu-link" href="/stock/" aria-current="page">' in menu_of(response)
    assert menu_of(response).count('aria-current="page"') == 1


@pytest.mark.django_db
def test_role_28_floors_stock_pages_light_its_stock_tab_not_the_menu_tab(client, sample_app):
    response = signed_in(client, Role.FLOOR).get("/stock/low/")

    assert '<a class="tab" href="/stock/" aria-current="page">' in bar_of(response)
    assert "data-lit" not in bar_of(response)
    assert '<a class="menu-link" href="/stock/low/" aria-current="page">' in menu_of(response)


@pytest.mark.django_db
def test_role_29_every_tab_has_its_word(client, sample_app):
    bar = bar_of(signed_in(client, Role.OWNER).get("/"))

    assert bar.count('class="tab"') == bar.count('class="tab__label"') == 3


@pytest.mark.django_db
def test_role_31_the_bar_holds_only_its_tabs_and_the_menu_tab(client):
    bar = bar_of(signed_in(client, Role.OWNER).get("/"))

    assert bar.count("<a ") == 1
    assert bar.count("<button") == 1


@pytest.mark.django_db
def test_role_36_a_thin_line_splits_the_groups_of_a_section(client, sample_app):
    html = menu_of(signed_in(client, Role.OWNER).get("/"))

    # The class is on the group's last row, the one before the line.
    assert html.count('class="menu-group-end"') == 1
    assert html.index("menu-group-end") < html.index("/stock/") < html.index("/shops/")


@pytest.mark.django_db
def test_role_36_a_section_with_no_row_for_this_role_does_not_show(client, sample_app):
    response = signed_in(client, Role.OFFICE).get("/")

    assert "Stock" in menu_of(response)
    assert "Insights" not in menu_of(response)


@pytest.mark.django_db
def test_staff_26_owners_see_the_staff_list_in_administration(client):
    html = menu_of(signed_in(client, Role.OWNER).get("/"))

    assert '<h2 class="menu-label">Administration</h2>' in html
    assert '<a class="menu-link" href="/staff/">' in html
    assert html.index("Administration") < html.index("Staff list")


@pytest.mark.django_db
@pytest.mark.parametrize("role", [Role.OFFICE, Role.FLOOR])
def test_staff_26_other_roles_see_no_door_to_the_staff_list(client, role):
    html = menu_of(signed_in(client, role).get("/"))

    assert "/staff/" not in html
    assert "Administration" not in html


@pytest.mark.django_db
def test_role_23_every_page_of_the_app_has_one_bar_and_one_menu(client):
    html = signed_in(client, Role.FLOOR).get("/").text

    assert html.count('class="tab-bar"') == 1
    assert html.count('<dialog class="menu"') == 1
    assert "css/app.css" in html
    assert "js/menu.js" in html
    assert "js/dialog.js" in html
    assert 'data-dialog-open="app-menu"' in html


@pytest.mark.django_db
def test_role_23_the_sign_in_steps_have_no_bar(client):
    assert "tab-bar" not in client.get("/sign-in/").text


@pytest.mark.django_db
def test_role_23_the_sign_out_card_has_no_bar(client):
    assert "tab-bar" not in signed_in(client, Role.FLOOR).get("/sign-out/").text


@pytest.mark.django_db
def test_role_23_the_state_pages_have_no_bar(client):
    assert "tab-bar" not in signed_in(client, Role.FLOOR).get("/no-such-page/").text
    client.force_login(UserFactory(is_staff=True))
    assert "tab-bar" not in client.get("/").text


@pytest.mark.django_db
def test_role_34_the_menus_head_shows_the_name_and_the_role(client):
    member = MembershipFactory(role=Role.OFFICE, user__first_name="Anil")
    client.force_login(member.user)

    html = menu_of(client.get("/"))

    assert '<span class="menu-account__name">Anil</span>' in html
    assert '<span class="menu-account__role">Office account</span>' in html


@pytest.mark.django_db
def test_role_34_an_account_with_no_name_shows_its_username(client):
    member = MembershipFactory(owner=True)
    client.force_login(member.user)

    html = menu_of(client.get("/"))

    assert f'<span class="menu-account__name">{member.user.username}</span>' in html
    assert '<span class="menu-account__role">Owner account</span>' in html


@pytest.mark.django_db
def test_role_34_the_menu_has_the_sounds_switch_with_both_its_words(client):
    html = menu_of(signed_in(client, Role.FLOOR).get("/"))

    assert 'role="switch"' in html
    assert "Sounds on" in html
    assert "Sounds off" in html


@pytest.mark.django_db
def test_role_35_a_page_of_the_app_has_one_link_to_sign_out(client):
    html = signed_in(client, Role.FLOOR).get("/").text

    assert html.count('href="/sign-out/"') == 1


@pytest.mark.django_db
def test_role_11_the_bar_and_the_menu_cost_no_query(client, sample_app, django_assert_num_queries):
    client = signed_in(client, Role.OWNER)

    # The same 6 as a page with no bar (test_middleware.py): the session, the
    # account, the membership, and saving the session.
    with django_assert_num_queries(6):
        client.get("/")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role", "has_new"), [(Role.OWNER, False), (Role.OFFICE, False), (Role.FLOOR, True)]
)
def test_role_26_only_floor_has_new_on_the_bar(client, role, has_new):
    bar = bar_of(signed_in(client, role).get("/"))

    assert ('href="/job-cards/new/"' in bar) is has_new

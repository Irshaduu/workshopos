"""Each role's tab bar and menu (ADR-0026, docs/rules/roles.md).

Written once, here, beside the roles. A tab or a menu row names its page by
the page's address name: text, never an import, so accounts stays under the
apps above it (ADR-0005). It shows only when that page's own mark lets this
person in, through the same check as the page, so the screen never offers a
door the page refuses (ROLE-12). A new page adds its line here in the same
pull request; a page that is not built has no line (ROLE-32).
"""

from dataclasses import dataclass

from django.urls import resolve, reverse
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Role
from apps.accounts.selectors import may_open


@dataclass(frozen=True)
class Link:
    """A tab or a menu row: a page by its address name, with its word and icon."""

    page: str
    word: str
    icon: str


@dataclass(frozen=True)
class Section:
    """A named part of the menu. A thin line splits its groups of rows (ROLE-36)."""

    word: str
    groups: tuple[tuple[Link, ...], ...]


@dataclass(frozen=True)
class RoleMenu:
    """One role's tab bar and menu (ROLE-24). The menu button's word is v1's."""

    tabs: tuple[Link, ...]
    menu_word: str
    sections: tuple[Section, ...] = ()


def _home(role):
    # The home tab is named after the role (ROLE-25).
    return Link("accounts:home", role.label, "house")


#: Every role's own tab bar and menu. A new role names its own here.
ROLE_MENUS = {
    Role.OWNER: RoleMenu(tabs=(_home(Role.OWNER),), menu_word=_("Manage")),
    Role.OFFICE: RoleMenu(tabs=(_home(Role.OFFICE),), menu_word=_("Manage")),
    Role.FLOOR: RoleMenu(tabs=(_home(Role.FLOOR),), menu_word=_("Menu")),
}


def _shown(links, request):
    """The links whose page lets this person in, each with its address and whether
    it is lit: the page open now, or a page under it. The home page's address, "/",
    is under nothing but itself."""
    found = []
    for link in links:
        address = reverse(link.page)
        if may_open(request.user, resolve(address).func):
            lit = request.path == address or (address != "/" and request.path.startswith(address))
            found.append({"address": address, "word": link.word, "icon": link.icon, "lit": lit})
    return found


def _sections(role_menu, request):
    """The menu's sections for this person, with no empty one. A row ends its group
    when another group follows it in the section."""
    sections = []
    for section in role_menu.sections:
        groups = [_shown(group, request) for group in section.groups]
        groups = [group for group in groups if group]
        if groups:
            for group in groups[:-1]:
                group[-1]["ends_group"] = True
            rows = [row for group in groups for row in group]
            sections.append({"word": section.word, "rows": rows})
    return sections


def tab_bar(request):
    """What the tab bar shows this person. One tab is lit: the page's own, or the
    menu button for a page reached from the menu (ROLE-28)."""
    role_menu = ROLE_MENUS[request.membership.role]
    tabs = _shown(role_menu.tabs, request)
    tab_lit = any(tab["lit"] for tab in tabs)
    row_lit = any(
        row["lit"] for section in _sections(role_menu, request) for row in section["rows"]
    )
    return {"tabs": tabs, "menu_word": role_menu.menu_word, "menu_lit": row_lit and not tab_lit}


def menu(request):
    """What the menu shows this person: who is signed in, and their rows (ROLE-34,
    ROLE-36). Its rows light the page open now (ROLE-37)."""
    role_menu = ROLE_MENUS[request.membership.role]
    return {
        "name": request.user.get_full_name() or request.user.username,
        "role": request.membership.get_role_display(),
        "menu_word": role_menu.menu_word,
        "sections": _sections(role_menu, request),
    }

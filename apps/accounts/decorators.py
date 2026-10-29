"""Marks for views (ADR-0023, ADR-0026)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PageMark:
    """A page's module, and the permission it needs."""

    module: str
    permission: str | None = None


def page(module, permission=None):
    """Marks a page with its module and the permission it needs (ADR-0026).

    Every page has this one mark, written first above its view. It only marks
    the view: the one check that reads it, may_open() in selectors.py, runs
    for every page from apps/accounts/middleware.py (ROLE-6). A page with no
    mark is refused to everyone (ROLE-8). Only a public page, or one that
    works without a workshop, names no permission.
    """
    mark = PageMark(module, permission)

    def decorator(view_func):
        view_func.page_mark = mark
        return view_func

    return decorator


def workshop_not_required(view_func):
    """Marks a view that works without a workshop, like signing out.

    Every other page needs a workshop that may work now
    (apps/accounts/middleware.py). Say why in a comment beside the mark.
    """
    view_func.workshop_required = False
    return view_func

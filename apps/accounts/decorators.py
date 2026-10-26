"""Marks for views (ADR-0023)."""


def workshop_not_required(view_func):
    """Marks a view that works without a workshop, like signing out.

    Every other page needs a workshop that may work now
    (apps/accounts/middleware.py). Say why in a comment beside the mark.
    """
    view_func.workshop_required = False
    return view_func

"""Gives each request its workshop, and guards every page (ADR-0023)."""

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _

from apps.accounts.selectors import membership_of
from apps.workshops.selectors import may_work


class WorkshopMiddleware:
    """Sets request.membership and request.workshop, once per request.

    Both are None for staff and superusers, for an account with no
    membership, and on pages that are public or in the Django admin, which
    never look one up. Every other page needs a workshop that may work now,
    unless its view is marked @workshop_not_required.

    It runs after LoginRequiredMiddleware, so a visitor who is not signed in
    is sent to sign in first.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.membership = None
        request.workshop = None
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        public = not getattr(view_func, "login_required", True)
        # The admin has its own staff check, and staff never have a workshop.
        if public or "admin" in request.resolver_match.app_names:
            return None

        request.membership = membership_of(request.user)
        request.workshop = request.membership.workshop if request.membership else None

        if not getattr(view_func, "workshop_required", True):
            return None
        if request.workshop is None:
            raise PermissionDenied(_("This account does not belong to a workshop."))
        if not may_work(request.workshop):
            raise PermissionDenied(_("This workshop is suspended."))
        return None

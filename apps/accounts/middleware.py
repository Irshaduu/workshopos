"""Sends a visitor to sign in first, gives each request its workshop, guards
every page (ADR-0023), and keeps signed-in pages out of the browser's cache."""

from django.contrib import messages
from django.contrib.auth.middleware import LoginRequiredMiddleware
from django.core.exceptions import PermissionDenied
from django.utils.cache import add_never_cache_headers
from django.utils.translation import gettext_lazy as _

from apps.accounts.selectors import membership_of
from apps.workshops.selectors import may_work


class SignInRequiredMiddleware(LoginRequiredMiddleware):
    """Django's own "sign in first", which also says when a change was lost (SIGN-38).

    A visitor whose session ended while saving sends a POST. They go to the
    sign-in page like anyone else, and back to the page after signing in;
    the sign-in page says that the change was not saved.
    """

    def handle_no_permission(self, request, view_func):
        if request.method == "POST":
            messages.warning(
                request,
                _(
                    "You were signed out after a long break, so your last change was not "
                    "saved. Sign in, then enter it again."
                ),
            )
        return super().handle_no_permission(request, view_func)


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


class NoStoreMiddleware:
    """Tells the browser never to keep a page it shows to a signed-in person.

    v1's lesson: after signing out on a shared laptop, Back showed a
    customer's bill again, from the browser's memory. A page the browser
    never kept cannot come back. Pages for visitors hold nothing private,
    so they are left alone.

    It reads request.user, so it runs after AuthenticationMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            add_never_cache_headers(response)
        return response

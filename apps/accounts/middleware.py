"""Sends a visitor to sign in first, gives each request its workshop, guards
every page (ADR-0023, ADR-0026), and keeps signed-in pages out of the
browser's cache."""

from urllib.parse import urlsplit

from django.contrib import messages
from django.contrib.auth.middleware import LoginRequiredMiddleware
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import resolve_url
from django.utils.cache import add_never_cache_headers
from django.utils.functional import SimpleLazyObject
from django.utils.translation import gettext_lazy as _

from apps.accounts.selectors import branch_of, may_open, membership_of, on_this_site
from apps.workshops.selectors import may_work


class SignInRequiredMiddleware(LoginRequiredMiddleware):
    """Django's own "sign in first", which also says when a change was lost (SIGN-38).

    A visitor whose session ended while saving sends a POST. They go to the
    sign-in page like anyone else, and back to the page after signing in;
    the sign-in page says that the change was not saved. A request from inside
    a page sends the whole page there (SIGN-39).
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
        if request.headers.get("HX-Request") == "true":
            return self._whole_page_to_sign_in(request, view_func)
        return super().handle_no_permission(request, view_func)

    def _whole_page_to_sign_in(self, request, view_func):
        """A request from inside a page (htmx) sends the whole page to the sign-in page,
        never just a part of it, and back to that page after signing in (SIGN-39).

        htmx's docs ask for a 2xx answer with HX-Redirect, and a 204 holds no part of a page.
        The page comes from htmx's HX-Current-URL, and only when it is an address of this site.
        """
        page = request.headers.get("HX-Current-URL", "")
        parts = urlsplit(page if on_this_site(request, page) else "")
        back_to = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        sign_in = redirect_to_login(
            back_to,
            resolve_url(self.get_login_url(view_func)),
            self.get_redirect_field_name(view_func),
        )
        response = HttpResponse(status=204)
        response["HX-Redirect"] = sign_in.url
        return response


class WorkshopMiddleware:
    """Sets request.membership, request.workshop and request.branch, once per request.

    All three are None for staff and superusers, for an account with no
    membership, and on pages that are public or in the Django admin, which
    never look one up. Every other page needs a workshop that may work now,
    unless its view is marked @workshop_not_required, and must let this
    account in by its page mark (may_open(), ADR-0026).

    request.branch is read only when a page first asks for it, like request.user,
    so a page that never asks costs no query for it.

    It runs after LoginRequiredMiddleware, so a visitor who is not signed in
    is sent to sign in first.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.membership = None
        request.workshop = None
        request.branch = None
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        public = not getattr(view_func, "login_required", True)
        # The admin has its own staff check, and staff never have a workshop.
        if public or "admin" in request.resolver_match.app_names:
            return None

        request.membership = membership_of(request.user)
        request.workshop = request.membership.workshop if request.membership else None
        if request.membership:
            request.branch = SimpleLazyObject(lambda: branch_of(request.membership))

        if getattr(view_func, "workshop_required", True):
            if request.workshop is None:
                raise PermissionDenied(_("This account does not belong to a workshop."))
            if not may_work(request.workshop):
                raise PermissionDenied(_("This workshop is suspended."))
        # Then the page's own mark: its module, and the permission it needs.
        # No reason is given, so the page says "Not open to your role" (ROLE-9).
        if not may_open(request.user, view_func):
            raise PermissionDenied
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

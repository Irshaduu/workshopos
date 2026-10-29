"""The one way to sign in (ADR-0025).

It is the only backend in AUTHENTICATION_BACKENDS, so every way in comes
through it: our sign-in page, the Django admin's sign-in page, and the tests.
"""

from asgiref.sync import sync_to_async
from django.contrib.auth.backends import ModelBackend

from apps.accounts.models import User
from apps.accounts.roles import permissions_of
from apps.accounts.selectors import account_by_username, is_owner, membership_of, minutes_locked
from apps.accounts.services import (
    check_sign_in_code,
    clear_wrong_passwords,
    count_wrong_password,
)


class SignInBackend(ModelBackend):
    """Django's own backend, with its sign-in check and its permissions replaced.

    Two ways in: an owner's sign-in code, or a username and a password for
    everyone else. A backend can only say yes or no, never why: the sign-in
    page asks minutes_locked() itself, only to say why (SIGN-33).

    has_perm and perms in templates stay Django's own; only the permissions
    they read change: a workshop member's come from the list in the code
    (ADR-0026).
    """

    def get_all_permissions(self, user_obj, obj=None):
        """A member's permissions come from the list, for their role (ADR-0026).

        Platform staff keep Django's own, from the database, for the admin; a
        member never gets those, so the two kinds never mix. A turned-off
        account has none. The role is read once per request (ROLE-11).
        """
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return set()
        if user_obj.is_platform_staff:
            return super().get_all_permissions(user_obj, obj)
        membership = membership_of(user_obj)
        return permissions_of(membership.role) if membership else set()

    async def aget_all_permissions(self, user_obj, obj=None):
        return await sync_to_async(self.get_all_permissions)(user_obj, obj)

    def authenticate(
        self, request, username=None, password=None, sign_in_code_id=None, code=None, **kwargs
    ):
        if sign_in_code_id is not None and code is not None:
            return self._with_code(sign_in_code_id, code)
        if username is not None and password is not None:
            return self._with_password(username, password)
        return None

    async def aauthenticate(self, request, **credentials):
        # Django's async sign-in goes through the same check, never around it.
        return await sync_to_async(self.authenticate)(request, **credentials)

    def _with_code(self, sign_in_code_id, code):
        """The code the browser holds, checked for an owner (SIGN-3, SIGN-16)."""
        owner = check_sign_in_code(sign_in_code_id, code)
        if owner is None or not is_owner(owner):
            return None
        return owner if self.user_can_authenticate(owner) else None

    def _with_password(self, username, password):
        account = account_by_username(username)
        # An owner signs in only with a code: their username finds no one,
        # and the try is not counted (SIGN-5).
        if account is not None and is_owner(account):
            account = None
        if account is None:
            # The password hasher runs anyway, so the answer takes as long as
            # a real check and never tells which usernames exist (SIGN-11).
            User().set_password(password)
            return None
        # Refused even with the right password, and not counted, so the lock
        # never grows longer (SIGN-32).
        if minutes_locked(account):
            return None
        if not account.check_password(password):
            count_wrong_password(account)
            return None
        clear_wrong_passwords(account)
        return account if self.user_can_authenticate(account) else None

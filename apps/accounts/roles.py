"""What each role may do: the permission list every app adds to (ADR-0026).

The roles themselves are fixed in the code (Role, in models.py). Each app
lists its permissions in its own permissions.py, each with the roles that
have it, and adds them from its AppConfig.ready(). Pages ask Django's
has_perm, which our backend answers from this list (backends.py).
"""

from apps.accounts.models import Role

#: Each permission, as "app.name", with the roles that have it.
PERMISSIONS: dict[str, frozenset[str]] = {}

#: Django's own words for its model permissions in the admin. Ours never
#: start with them, so the two kinds never mix (ADR-0026).
DJANGO_WORDS = ("add_", "change_", "delete_", "view_")


def add_permissions(app_label, permissions):
    """Adds an app's permissions: each name, with the roles that have it.

    Each role is named one by one, never through a shortcut for every role,
    so a role added later starts with no permission at all (ROLE-5). An
    unknown role, or a permission no role has, is refused.
    """
    for name, roles in permissions.items():
        if name.startswith(DJANGO_WORDS):
            raise ValueError(f"{name!r} starts with one of Django's own words {DJANGO_WORDS}.")
        if not roles:
            raise ValueError(f"No role has {name!r}: name at least one.")
        PERMISSIONS[f"{app_label}.{name}"] = frozenset(Role(role).value for role in roles)


def permissions_of(role):
    """Every permission this role has, as "app.name"."""
    return {name for name, roles in PERMISSIONS.items() if role in roles}

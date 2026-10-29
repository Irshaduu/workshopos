"""What each role may do in accounts (ADR-0026).

Each permission names its roles one by one, never "every role", so a role
added later starts with none of them (ROLE-5).
"""

from apps.accounts.models import Role

PERMISSIONS = {
    # The home page, until the live board takes its address (Phase 6).
    "open_home": {Role.OWNER, Role.OFFICE, Role.FLOOR},
}

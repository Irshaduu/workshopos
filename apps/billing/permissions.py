"""What each role may do in billing (ADR-0026, docs/rules/settle-bill.md).

Each permission names its roles one by one, never "every role", so a role added later
starts with none of them (ROLE-5).
"""

from apps.accounts.models import Role

PERMISSIONS = {
    # Office does the money (ROLE-19), and Floor never sees a price (ROLE-16, SETTLE-47).
    "see_bill": {Role.OWNER, Role.OFFICE},
    "settle_bill": {Role.OWNER, Role.OFFICE},
}

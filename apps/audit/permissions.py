"""What each role may do with money after the fact (ADR-0026, docs/rules/change-history.md).

Each permission names its roles one by one, never "every role", so a role added later
starts with none of them (ROLE-5).
"""

from apps.accounts.models import Role

PERMISSIONS = {
    # Only an owner dates money further back than the workshop's back-date limit
    # (CHANGE-15, CHANGE-16).
    "date_money_any_day": {Role.OWNER},
    # Only an owner changes money after the workshop's edit window (CHANGE-9, CHANGE-11).
    "money_change_any_time": {Role.OWNER},
}

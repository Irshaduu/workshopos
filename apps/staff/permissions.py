"""What each role may do in staff (ADR-0026, STAFF-18).

Each permission names its roles one by one, never "every role", so a role
added later starts with none of them (ROLE-5). Showing and saving are two
permissions, so a read-only role added later sees the list and can never save
(STAFF-19).
"""

from apps.accounts.models import Role

PERMISSIONS = {
    "see_staff_list": {Role.OWNER},
    "save_staff_member": {Role.OWNER},
}

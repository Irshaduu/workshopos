"""What each role may do in jobs (ADR-0026, docs/rules/job-card.md).

Each permission names its roles one by one, never "every role", so a role added later
starts with none of them (ROLE-5).
"""

from apps.accounts.models import Role

PERMISSIONS = {
    "see_live_board": {Role.OWNER, Role.OFFICE, Role.FLOOR},
    "save_job_card": {Role.OWNER, Role.OFFICE, Role.FLOOR},
    # Who the customer is, and the price of the work (ROLE-16, ROLE-17). It chooses the form.
    "save_customer_and_labour": {Role.OWNER, Role.OFFICE},
    "cancel_job_card": {Role.OWNER, Role.OFFICE},
}

# 0026: Roles: each app lists its permissions, and every page asks has_perm

**Status:** Proposed (2026-10-29)

## Context

- Slice 1's second step is Roles. Its rules come from v1:
  `docs/rules/roles.md`.
- ADR-0007 decided the three workshop roles, Owner, Office and Floor, with
  a membership for each account, and that permissions are checked in one
  place, with a test for every page. Its Floor line says "its own jobs",
  but v1's live board shows Floor the whole floor (ROLE-14), and the client
  will use one shared Floor login on the floor tablet.
- The roles are fixed in the code, never made by a workshop, and a new
  role must need no change to pages (ROLE-1, ROLE-5; his answers,
  2026-10-26).
- v1 had three checks named after a ladder of roles: `owner_required`,
  `office_required` (Office and owners) and `staff_required` (every role).
  Its templates asked `has_group:"Owner"`. A role off the ladder, like a
  read-only Accountant who sees the money but changes nothing, fits none
  of them.
- v1 wrote each page's check and its menu item apart, and they drifted:
  Control Hub showed in the menu to owners only, but Office could open it
  by its address (ROLE-12).
- v1 measured that asking the role on every line of a page cost a query
  each time: 32 of the job card form's 48 queries, until the answer was
  kept for the request (ROLE-11). v2's middleware already reads the
  membership once per request (ADR-0023).
- v1's tab bar and menu differ by role (ROLE-24, ROLE-36). Floor's bar has
  New and Inventory, pages that Office and owners may open too but reach
  another way, and Floor's menu has its own sections. So a role's menu is
  not simply "every page it may open".
- Each app adds its own modules to the module list (ADR-0011), and its own
  entries to the roles list (`docs/PLAN.md`). A lower app never imports an
  upper one (ADR-0005).
- Django's own way to ask is `user.has_perm("app.name")`, and `perms` in
  templates. Read in Django 6.1.2's code on 2026-10-29:
  - `has_perm` asks each backend in `AUTHENTICATION_BACKENDS`. Ours is
    `SignInBackend`, built on `ModelBackend` (ADR-0025). `ModelBackend`
    says yes when the name is in the account's `get_all_permissions()`,
    and `perms.app` asks whether the account has any permission of that
    app, from the same set.
  - `ModelBackend` reads that set from database tables: permissions given
    to an account or to its groups. Django makes four for each model (add,
    change, delete and view) for its admin.
  - A group belongs to an account, not to a membership in one workshop.
  - An active superuser gets yes for every permission, before any backend
    is asked.

## Options

**A. Django's groups and database permissions:** a group for each role,
with its permissions as rows, kept in step by data migrations.
- For: all Django's own; the admin can show them.
- Against: the role would live twice, in the membership and in the
  account's groups, and the two can drift (v1's empty group). A group
  belongs to the account, so it breaks when one person works in two
  workshops (SaaS). A change needs a data migration on every server. The
  admin invites a workshop to make its own roles, which ROLE-1 forbids.

**B. Each app lists its permissions in the code, and our backend answers
`has_perm` from those lists.**
- For: one home for each fact: the role in the membership, what a role
  may do in the code. A change is reviewed in a pull request, and is the
  same on every server (ADR-0003). Django's own words for asking
  (`has_perm`, `perms`), which every Django developer knows. No query.
- Against: `has_perm` says yes to a superuser for everything, so the
  workshop check must always run first, as it does (ROLE-4). Our names
  must stay clear of Django's own four for each model.

**C. Our own check function and template tag, without `has_perm`.**
- For: no surprise for superusers.
- Against: a second way to ask, which other Django developers would not
  know, and more code of our own.

## Decision

Option B.

- **The roles stay fixed in the code:** `Role` in
  `apps/accounts/models.py`. A member's role comes from their membership,
  read once per request and kept on the account for that request, so
  asking what a person may do costs no query (ROLE-11).
- **Each app lists its permissions** in its own `permissions.py`: each
  name, and the roles that have it. For example `jobs.see_prices`, for
  Owner and Office. The app's `ready()` adds its list to the full list in
  `apps/accounts/roles.py`, so the upper app hands its list down and
  `accounts` never imports it. A name never starts with Django's own
  words `add_`, `change_`, `delete_` or `view_`.
- **Our backend answers `has_perm`** for a workshop member from the full
  list: yes when the member's role has the permission, and no for a name
  the list does not know. It changes only `get_all_permissions()`, so
  Django's own `has_perm` and `perms` work unchanged. Platform staff keep
  Django's own answer from the database, for the admin.
- **The module list** lives in `apps/workshops/modules.py`, with each
  module's key, its name, whether it is core, and the modules it needs
  (ADR-0011). Each app adds its own modules from its own `modules.py`, in
  the same way. For now the list only names the modules; the switch per
  workshop comes when a workshop first needs a module off.
- **The page mark:** every page's view carries one mark,
  `@page(module, permission)`, in `apps/accounts/decorators.py`. It only
  marks the view. One check reads it, in the middleware that already gives
  each request its workshop (`apps/accounts/middleware.py`), right after
  the workshop check: the module must be in the module list, and the
  account must have the permission. Otherwise the answer is "Not open to
  your role" (403). A page with no mark is refused to everyone (ROLE-8).
  A public page, and signing out, name their module and no permission.
- **No page checks a role by its name** (ROLE-7). Templates ask `perms`;
  views and forms ask `has_perm`. A test reads every view, form and
  template, and fails when one compares a role.
- **The tab bar and the menu:** each role's tabs and menu sections are
  written once, beside the roles, in `apps/accounts/menu.py`. Each tab and
  item names its page by the page's address name (text, never an import).
  It shows only when that page's own mark lets the person in, through the
  same check as the page, so the menu can never offer a door the page
  refuses (ROLE-12). A new role names its own tabs and menu.
- **Floor**, in place of ADR-0007's Floor line: Floor sees the whole
  floor, every car and every mechanic's work, through one shared login on
  the floor tablet or a login per mechanic. It never sees prices or
  customer details (ROLE-16, ROLE-17). Who did the work comes from the
  mechanic picked on the job card (ROLE-3).
- **The permission matrix,** `tests/test_permissions.py`: it walks every
  address of the project by itself, so a page with no row fails. Each row
  types the expected answer for a visitor who is signed out, an owner,
  Office, Floor, a platform staff account and a superuser. The answers are
  never read from the permission lists. A page that shows a record is also
  asked for a record of another workshop, and must answer "Not found"
  (ROLE-10). The Django admin and the health check are not pages of the
  app; the test lists them, with why.
- **Not built now:** each page's permissions come with the page; the
  module switch, when a workshop first needs a module off; a new role,
  like a read-only Accountant, when a workshop asks for one.

## Consequences

- A new role is a new value of `Role`, its line in each app's permission
  list, and its own tabs and menu. No page changes.
- "Who may do this?" has one answer for each app, in its
  `permissions.py`, and the matrix proves it page by page with answers
  typed by hand.
- Every new page needs its mark and its matrix row in the same pull
  request, or a test fails.
- `has_perm` says yes to a superuser everywhere. This is safe only because
  no superuser is ever a member, and every workshop page checks the
  workshop first. The matrix asks every page as a superuser too.
- Platform staff in the Django admin use Django's database permissions,
  kept apart from the workshop roles.
- `apps/accounts/menu.py` names pages of every app by their address names,
  so each module's build adds its own rows there.
- ADR-0007's Floor line is replaced. Its status line says so when this
  ADR is accepted.

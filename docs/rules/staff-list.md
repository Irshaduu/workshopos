# Rules: staff list

The rules of the Staff list module (`docs/MODULES.md`), taken from v1 and
checked in v1's code (`Mechanic` in `workshop/models.py`, the three
`manage_*_mechanic` views in `workshop/management_views.py`, the staff section
of `manage_dashboard.html`, and their tests). Words: `docs/GLOSSARY.md`. The
code: `apps/staff/`.

- Each rule has an ID. A test names the ID of the rule it protects.
- An ID never changes. A new rule takes the next free number.
- Each rule says where it comes from: **v1** (kept as it was), **v1,
  changed** (and what changed), or **new** (v2 only).
- Every rule is built with this module, unless it says when.

## Who is on the list

- **STAFF-1** A staff member is a real person who works at the workshop, not a
  login. Nothing links the two: every mechanic can share one Floor login
  (ROLE-3), and a person with no login is still on the list. *v1: `Mechanic`,
  "Real people, not logins".*
- **STAFF-2** A staff member's designation is their job. It says nothing about
  what they may open; that is a login's role. *v1, changed: v1 called both of
  them "role", on one screen.*
- **STAFF-3** The designations are Mechanic, Assistant Mechanic, Office Staff
  and General Helper, in this order. They are fixed in the code, the same for
  every workshop, and PostgreSQL refuses any other. A new one is one line in the
  code and a migration. *v1: `ROLE_CHOICES`.*
- **STAFF-4** A staff member belongs to one branch, and the page shows only its
  own branch's people. A person of another workshop or another branch is never
  found: their pages answer "Not found" (ROLE-10). *New (ADR-0028).*

## The name

- **STAFF-5** A name is required, up to 100 characters. *v1.*
- **STAFF-6** A name is tidied when it is saved. Spaces at the ends and double
  spaces go. A name typed with no capitals gets one at the start of each word, so
  "c.k. rajan" is saved as "C.K. Rajan". A name typed with its own capitals keeps
  them, and only its first letter is raised, so "anil KP" is saved as "Anil KP"
  and "Mohammed bin Salim" stays. No capital is ever made small, so whatever is
  typed can be kept. *v1, changed: v1's `.title()` turned "Anil KP" into "Anil
  Kp", with no way to fix it, and "Anil  Kumar" with two spaces passed as a new
  name.*
- **STAFF-7** Two people in one branch never share a name, whatever the capitals,
  because a job card's picker and the live board's chips show only the name. A
  turned-off person's name counts too: someone who comes back is turned on, not
  added again. The same name in another branch or another workshop is fine.
  PostgreSQL holds this rule. *v1, changed: v1 checked it only in the view, with
  `name__iexact`, while its database rule looked at exact capitals.*

## Adding

- **STAFF-8** Adding takes a name and a designation, both required. No
  designation is chosen for you. The new person starts turned on. *v1.*
- **STAFF-9** A double tap or a slow network never adds a person twice. The form's
  address holds the new record's key, and a repeat shows the list with the person
  saved the first time, and the same notice. Another name sent with a key already
  used, like from a page brought back by Back, is not saved, and the notice says
  so. *New (`docs/PLAN.md`, Phase 5).*

## Changing

- **STAFF-10** Edit changes the name and the designation of the same record, so
  every job card that points to this person stays with them, and an old job card
  shows the new name. *v1: `manage_edit_mechanic`.*

## Turning off

- **STAFF-11** Someone who leaves is turned off, never deleted. There is no
  delete at all, because job cards and salary point to them. *v1: "deliberately
  no delete".*
- **STAFF-12** A turned-off person stays on the list, after the people turned
  on, with their name struck through and a "Turned off" tag. *v1: `-is_active`,
  and its "Retired" tag.*
- **STAFF-13** Turn off and Turn on are two buttons with two addresses, never one
  flip. A repeat changes nothing, so a double tap ends the way it was tapped.
  *v1, changed: v1's one toggle flipped on every send, so a double tap changed
  nothing and still said it had worked.*
- **STAFF-14** Turning off asks no question, because Turn on undoes it with one
  tap. *v1.*
- **STAFF-15** Only a Mechanic or an Assistant Mechanic who is turned on can be
  picked as a job card's lead mechanic. An old job card keeps the person it has,
  whatever has changed since. *v1: `JOBCARD_ELIGIBLE_ROLES`,
  `MechanicChoiceField`. Built with the job card.*
- **STAFF-16** When a person is turned off, owners get an alert. Turning on sends
  none. *v1: `ACCOUNT_ARCHIVED`. Built with the bell (Phase 6).*
- **STAFF-17** Turning off someone who has advances in a month not yet settled
  warns the owner, and never stops them. *v1: `_unsettled_advance_total`. Built
  with Salary advances (After).*

## Who may do what

- **STAFF-18** Only owners open the Staff list, and only they add, change or turn
  off (ROLE-21). *v1: `@owner_required`.*
- **STAFF-19** Showing and saving ask for different permissions, so a read-only
  role added later sees the list, gets no form and no button, and is refused if
  it sends one by hand (ROLE-5). *New (`docs/PLAN.md`, Phase 5).*

## The screen

- **STAFF-20** The page shows its title, the add form, and one card for each
  designation, in order, each with its count. In a card, the people turned on
  come first, then by name, whatever the capitals. *v1.*
- **STAFF-21** A card with no one in it says so. *v1: "None registered yet."*
- **STAFF-22** A row's Edit and Turn off stay behind its three-dot button. Only
  one row is open at a time. *v1.*
- **STAFF-23** Edit opens a card over the page, with the name and the
  designation. A refused edit opens it again by itself. *v1, changed: see
  STAFF-24.*
- **STAFF-24** A refused form shows its error next to the field, and what was
  typed stays. *v1, changed: v1 went back to the list with a message, and the
  typed text was lost.*
- **STAFF-25** A long card scrolls inside itself, so the other cards stay near.
  *v1: `.roster-list`.*
- **STAFF-26** The Staff list is a row of the menu, in Administration. There is
  no Control Hub page, so it has no back control, like v1's other pages opened
  from the menu. *v1, changed: a page of three tiles is a second menu (ROLE-23).*
- **STAFF-27** A longer list never means more queries
  (`tests/test_query_counts.py`). *New (`docs/PLAN.md`, Phase 5).*

## Left out for now

- A person's monthly salary (`current_salary` in v1) comes with Monthly salary
  (After), not here. The list shows no money.
- "Retired" and "Archived", v1's two words for one thing: now "Turned off"
  (`docs/GLOSSARY.md`).
- A designation's own colour, like v1's blue card for Mechanic: in v2 a colour
  means a status, never decoration (`docs/DESIGN.md`). Mechanic still comes first.

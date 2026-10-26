# 0023: Tenancy: the workshop passed by hand, links kept inside one workshop

**Status:** Accepted (2026-10-26)

## Context

- Many workshops may share one database later (ADR-0003). One workshop
  must never see another's data, not even a car's history (ADR-0006).
- The first workshop will probably run on its own server, with only its
  own data in the database.
- Every query has to know its workshop. Three ways were compared:
  - **By hand:** each request finds its workshop once, and every selector
    and service takes it as an argument. The flow is visible and works the
    same in pages, commands, background jobs and tests. A developer can
    forget the filter, so tests have to catch it.
  - **A hidden current workshop**, with a manager that filters by itself:
    harder to forget in a page, but the flow is hidden (v1's lesson with
    signals), it breaks in commands and background jobs, and Django's
    admin and its own code still need a manager that does not filter.
  - **PostgreSQL row-level security now:** the database refuses another
    workshop's rows even when the code forgets. It needs a second database
    user (the host's main user skips these rules), a transaction for every
    request, rules written as raw SQL, and a way around them for
    migrations and the admin. On a server with one workshop it guards
    nothing.
- A record can link to another workshop's record by mistake: a job card of
  workshop A pointing at a car or a branch of workshop B. Django 6.1
  cannot make a two-column foreign key from `models.py`: its
  `ForeignObject` makes no database constraint.
- Measured on 2026-10-26 with Django 6.1 and PostgreSQL 18.6, on
  throwaway tables that were rolled back, a constraint class of our own
  (`SameWorkshop`, built on Django's `BaseConstraint`):
  - made a two-column foreign key together with the table;
  - was removed and added again by migration steps;
  - made PostgreSQL refuse a job card linked to another workshop's car;
  - made `full_clean()` refuse it before the database;
  - could be written down by migrations.

## Decision

- **The workshop is passed by hand.** One middleware sets
  `request.workshop` from the signed-in person's membership (built with
  the memberships). Every selector and service takes the workshop as its
  first argument. Queries start with `Model.objects.for_workshop(workshop)`,
  which refuses anything but a `Workshop`. No thread-locals, and no
  manager that filters by itself.
- **Every business model builds on `WorkshopModel`**
  (`apps/workshops/models.py`): `core`'s base model, a required workshop
  link, and a unique (workshop, id) pair. A test checks every model in our
  apps. The models left out are listed in that test, each with its reason:
  the user (one person can belong to several workshops) and the workshop
  itself.
- **A link stays inside its workshop.** A link to another workshop record
  carries a `SameWorkshop` constraint: a two-column foreign key from
  (workshop, link) to the target's (workshop, id). PostgreSQL checks it at
  the end of the transaction, like Django's own foreign keys; forms check
  it first. It is built with the first such link: the job card, in
  Slice 1.
- **Leak tests.** One test covers every workshop model by itself: it makes
  a record in each of two workshops and checks that `for_workshop()`
  returns only the right one. Every workshop model needs a factory for it.
  Page leak tests come with the permission matrix, from the first page: a
  member of one workshop gets "not found" for another workshop's record.
- **Whether a workshop may work now is decided in one place:** `may_work()`
  in `apps/workshops/selectors.py`. The middleware asks it on every
  request. A suspended workshop is blocked, except for signing out (later,
  also its payment page). A subscription rule plugs in there.
- Which branches a member may see is decided with the memberships.
- **The Django admin is not scoped.** It is for emergencies only
  (ADR-0007), and it is locked down before go-live.
- **Row-level security comes later**, as a second guard, before a second
  workshop's data shares a database.

## Consequences

- The workshop is an argument of every selector and service: more to type,
  but anyone can follow where it comes from.
- Until row-level security is added, a forgotten `for_workshop()` is caught
  by the page leak tests, not by the database. Adding it stays small:
  every table already has the workshop column, and one middleware already
  knows the workshop.
- The (workshop, id) index also serves every "this workshop's records"
  query, so the workshop link needs no index of its own. Each index entry
  is one key bigger than a plain workshop index.
- A model that adds its own constraints must keep `WorkshopModel`'s. The
  test fails if it does not.
- `SameWorkshop` is our own code to keep right, and it is checked at the
  end of the transaction, so a wrong link fails at the save of the whole
  change, not at the line that made it. Forms catch it earlier.

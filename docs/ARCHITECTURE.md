# Architecture

> **Status: Accepted** (ADR-0005, 2026-10-26). Binding: change it only
> through a new ADR.

How the code is organised. What is planned: `docs/PLAN.md`. Why: `docs/adr/`.

---

## What we optimise for

- **Correct money.** Every rupee traceable to the record that moved it.
- **Easy to change.** Every rule has one home, so anyone can say which file to
  change when a rule changes.
- **Safe for many workshops.** No data can cross from one workshop to another.
- **Simple to run.** One application and one database per deployment.

## Deployment model

```
one repository -> CI -> staging -> production servers
                                     ├── dedicated: one workshop, the client's own hosting
                                     └── shared:    many workshops (later)
```

- Same code and same version on every server.
- What differs between servers is configuration (environment variables) or
  per-workshop settings, never code.

---

## Project layout

```
workshopos/
├── apps/              all Django apps (below)
├── config/            settings (base, local, test, production), urls, wsgi, health check
├── templates/         base layout and shared components
├── static/            design system CSS (ADR-0017), icons (ADR-0018), shared JS modules, vendor/htmx (ADR-0016)
├── locale/            translations (Malayalam later, ADR-0015)
├── tests/             project-wide tests (settings, safe defaults, layers, keys, tenancy); js/ JavaScript unit tests (ADR-0020); e2e/ browser tests (Playwright)
├── design/lab/        UI lab prototypes, never imported by the app
├── docs/
├── .github/workflows/ CI
├── pyproject.toml     dependencies, ruff, import-linter and pytest settings
├── uv.lock            exact versions of every dependency
└── manage.py, README.md, CLAUDE.md, CONTRIBUTING.md, LICENSE, .env.example,
    .pre-commit-config.yaml
```

## Apps: small, each answering one question

| App | Holds |
|---|---|
| `core` | shared tools: the base model that gives every model its UUID7 key (ADR-0022), money, dates, template helpers. No business rules. (Shared UI components live in `templates/components/` and `static/`.) |
| `workshops` | the tenant: the workshop, its branches, the base of every business model (ADR-0023), profile, status, the module list and switches (ADR-0011) |
| `accounts` | users, memberships, roles, platform staff, login security |
| `audit` | change history: deleted, edited, back-dated |
| `notifications` | the bell, push alerts, email |
| `photos` | photos of cars and parts: a real link to the job card or the part, and a database check that exactly one is set (v1's shape) |
| `inventory` | products, categories, stock, costing, opening stock |
| `vehicles` | customers, vehicles, brands and models, vehicle profile |
| `staff` | staff roster, salary, advances |
| `suppliers` | spare shops, Supplies Shops, purchases, payments, discounts, opening balances |
| `jobs` | job cards, concerns, work done, parts used, warranty, estimates |
| `billing` | invoices, settling, GST, fleet accounts, old bills, printed documents |
| `finance` | cashbook, rent, owner withdrawals |
| `reports` | profit, cash tracking, deep analysis, dashboard; read-only |
| `assistant` | the AI assistant: tools over read-only selectors (ADR-0008); read-only |
| `onboarding` | go-live import tools; the whole app can be removed once go-live import is done (but see open decision 9) |

An app is created with its first real code: a model, a page or a shared
tool (ADR-0021). No empty apps.

## Layers: who may import whom

```
Top        reports, onboarding, assistant    <- nothing imports these
Business   billing, finance, photos
           jobs
           suppliers
           inventory, vehicles, staff
Services   audit, notifications             <- any business app may call these
Base       accounts
           workshops
           core
```

- An app may import only from apps in **lower rows**, never the same row,
  never above.
- **Model links follow the same rule.** A model links only to its own app's
  models or to lower rows. A link written as text
  (`ForeignKey("billing.FleetAccount")`) needs no import, so import-linter
  cannot see it.
- A lower app never reads an upper one. When it needs data that an upper app
  creates, the upper app's service passes it down.
- CI checks both, so the rule cannot quietly break (ADR-0021):
  `import-linter` reads the imports, and a test walks every model link and
  fails on one that points up, or on a generic link. Both run in
  `tests/test_layers.py`. The row order lives in the `import-linter`
  settings in `pyproject.toml`, so it has one home; a new app is placed
  there in the same commit.

## Inside every app: the same files every time

```
jobs/
├── models.py      the data
├── services.py    rules that CHANGE data (create, settle, cancel)
├── selectors.py   rules that READ data (lists, totals)
├── forms.py       checks what was typed
├── views.py       thin: request -> form -> service -> response
├── urls.py
├── admin.py
├── templates/jobs/
├── static/jobs/
└── tests/
```

| You are writing | It goes in |
|---|---|
| a database table | `models.py` |
| anything that creates, changes or deletes data | `services.py` |
| a query for a list, a total or a report | `selectors.py` |
| a check on what a person typed | `forms.py` |
| the handling of a page request | `views.py`, kept thin |
| a page address | `urls.py` |
| HTML | `templates/<app>/` |
| page-specific CSS or JS | `static/<app>/` |
| a component used by several pages | `templates/components/` and `static/` |
| a rule used by many apps (money, dates) | `core` |
| a test | `<app>/tests/` |

- **No business logic in signals.** Every change happens through an explicit
  service call.
- **No CSS or JS inside templates.** It lives in static files, which allows a
  strict Content-Security-Policy.

---

## Tenancy

How each workshop's data stays its own: ADR-0023.

- `Workshop` and `Branch` live in `workshops`. A workshop is the business; a
  branch is one of its locations (ADR-0006).
- Every business model builds on `WorkshopModel` (`apps/workshops/models.py`):
  a required workshop link, and a unique (workshop, id) pair. Operational
  records (job cards, invoices, stock, cash) also link to a branch.
- Customers and vehicles belong to the workshop, so all its branches share them.
- Unique rules include the workshop (e.g. a bill number is unique per branch
  of a workshop).
- **The workshop is passed by hand.** One middleware
  (`apps/accounts/middleware.py`) finds the signed-in account's membership
  once per request and sets `request.membership` and `request.workshop`.
  Every selector and service takes the workshop as its first argument, and
  its queries start with `Model.objects.for_workshop(workshop)`. No hidden
  current workshop.
- **Every page needs a workshop that may work now**, unless it is public, in
  the Django admin, or marked `@workshop_not_required` (like signing out).
  Otherwise the answer is "not allowed" (403).
- **A link stays inside its workshop.** A link to another workshop record
  carries a `SameWorkshop` constraint, so PostgreSQL refuses a link to a
  record of another workshop.
- **Whether a workshop may work now** has one home: `may_work()` in
  `apps/workshops/selectors.py`, asked by the middleware.
- **A membership** (`apps/accounts/models.py`) is an account's place in a
  workshop, with its role (ADR-0007). For now an account belongs to one
  workshop, a database rule. A shared login, like one Floor login on the
  workshop tablet, is one account.
- Staff and superusers run the system: they are never members and never get
  a workshop (ADR-0007). The Django admin is not scoped: it is for
  emergencies only.
- **Leak tests:** `tests/test_tenancy.py` checks that every business model
  builds on `WorkshopModel`, and that each one shows a workshop only its own
  records. The permission matrix checks every page: a record of another
  workshop is never found.
- PostgreSQL's row-level security is added as a second guard before a second
  workshop's data shares a database.

## Shared rules

- **Money** (`core`): `Decimal` only, bounds read from the column, a zero or
  negative amount refused by the parser itself.
- **Dates** (`core`): India time, `timezone.localdate()`, never `date.today()`.
- **Audit:** services call `audit` whenever money is changed, deleted or
  back-dated.
- **Notifications:** services call `notifications`; views never do.
- **History:** record when things happen. Status changes that matter store
  their time (part ordered and received, work started and fixed, car in,
  ready and delivered), and kilometres are a number at every visit.
  Estimates, reports and the AI assistant are built on this history, which
  cannot be filled in later.
- **Module switches:** each workshop has its modules on or off (ADR-0011).
  Menus, pages and the assistant's tools check this in one place. Off hides
  a module; it never deletes data. Every page and menu item names its
  module from the first page; the switch itself is built when a workshop
  first needs a module off.
- **Per-workshop settings** (ADR-0024): each lives beside the rule that
  uses it, in its app's settings model, one row per workshop. No saved row
  means the default in the code. A setting acts at the moment of an
  action, never on saved records.

---

## Where each v1 area goes

| v1 area | New app |
|---|---|
| Job cards, concerns, job lines, parts on cards, warranty, estimates | `jobs` |
| Invoice, settle, printed documents, fleet accounts, old bills | `billing` |
| Spare shops, unassigned spares, Supplies Shops, payments, shop discounts, opening balances | `suppliers` |
| Inventory items, categories, stock, costing replay, opening stock, stock history | `inventory` |
| Cashbook, rent, owner withdrawals | `finance` |
| Staff roster, salary and advances | `staff` |
| Car profiles, brands and models, chassis code and VIN, known plate | `vehicles` |
| Spare-part and concern master lists | `jobs` |
| Profit, cash tracking, deep analysis, dashboard, live report | `reports` |
| Deletion, edit and back-dated history | `audit` |
| Notifications, web push, email | `notifications` |
| Photos | `photos` |
| Legacy Data screens, PDF reader, go-live lock | `onboarding` |
| Login, roles, sessions, lockout, password reset, Control Hub | `accounts` |
| Business constants (discount threshold, edit window, back-date limit, markup) | the app of the rule that uses each (ADR-0024) |
| Bill and job card number series | `billing`, `jobs` |
| `money.py`, `money_dates.py`, base templates, design system | `core`, `templates/`, `static/` |
| About page and system map | feature audit: keep or drop |

---

## Open decisions: each becomes an ADR

1. **Shop parts and the supplier ledger.** Proposal: `suppliers` owns a
   purchase record; a job's shop-part line points to it (`jobs` imports
   `suppliers`). An unassigned spare is then simply a purchase no job uses yet.
2. Background and scheduled jobs: backups, clean-ups, push.
3. Tenancy enforcement: decided in ADR-0023 (the workshop passed by hand;
   row-level security later).
4. Per-workshop settings: decided in ADR-0024 (each beside the rule that
   uses it).
5. Photo storage: one bucket with a prefix per workshop, or a bucket per
   deployment.
6. AI provider and model for the assistant (ADR-0008).
7. **Fleet accounts and the job card.** In v1 the job card points to its
   fleet account, but `billing` sits above `jobs`, so that link would point
   up. Move fleet accounts down beside customers in `vehicles`, or put the
   link on the bill? Decided in the billing loop.
8. **Stock costing and purchases.** v1 works out the average cost by
   replaying the restock bill rows, but purchases live in `suppliers`, above
   `inventory`. Proposal: the `suppliers` service tells `inventory` how much
   came in at what cost, and costing replays only `inventory`'s own rows.
   Decided in the stock section.
9. **Old data from other workshops.** Each workshop's old system has its
   own format. Proposal: one standard import format, with a small reader per
   source (Excel, Tally, another system, the first workshop's PDF bills);
   every import checked, shown as a preview, and saved as one batch that
   can be undone; each row keeps its source reference, so a second run adds
   nothing twice. `onboarding` then stays after go-live, because each new
   workshop imports. Decided with the go-live tools (Phase 6) and the SaaS
   data import.

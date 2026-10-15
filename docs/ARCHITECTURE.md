# Architecture

> **Status: Proposed.** It becomes binding when ADR-0005 is accepted in
> Phase 1. After that, change it only through a new ADR.

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
├── config/            settings (base, local, test, production), urls, wsgi
├── templates/         base layout and shared components
├── static/            design system CSS and shared JS
├── tests/e2e/         browser tests (Playwright)
├── design/lab/        UI lab prototypes, never imported by the app
├── docs/
├── .github/workflows/ CI
├── pyproject.toml     dependencies, ruff and pytest settings
├── docker-compose.yml local PostgreSQL
└── manage.py, README.md, CLAUDE.md, CONTRIBUTING.md, LICENSE, .env.example
```

## Apps: small, each answering one question

| App | Holds |
|---|---|
| `core` | shared tools: money, dates, template helpers. No business rules. (Shared UI components live in `templates/components/` and `static/`.) |
| `workshops` | the tenant: the workshop, its branches, profile, status, settings, bill-number series |
| `accounts` | users, memberships, roles, platform staff, login security |
| `audit` | change history: deleted, edited, back-dated |
| `notifications` | the bell, push alerts, email |
| `photos` | photos of cars and parts, linked generically to their subject |
| `inventory` | products, categories, stock, costing, opening stock |
| `vehicles` | customers, vehicles, brands and models, vehicle profile |
| `staff` | staff roster, salary, advances |
| `suppliers` | spare shops, Supplies Shops, purchases, payments, discounts, opening balances |
| `jobs` | job cards, concerns, work done, parts used, warranty, estimates |
| `billing` | invoices, settling, GST, fleet accounts, old bills, printed documents |
| `finance` | cashbook, rent, owner withdrawals |
| `reports` | profit, cash tracking, deep analysis, dashboard; read-only |
| `onboarding` | go-live import tools; the whole app can be removed once go-live import is done |

## Layers: who may import whom

```
Top        reports, onboarding               <- nothing imports these
Business   billing, finance
           jobs
           suppliers
           inventory, vehicles, staff
Services   audit, notifications, photos     <- any business app may call these
Base       accounts
           workshops
           core
```

- An app may import only from apps in **lower rows**, never the same row,
  never above.
- CI checks this with `import-linter`, so the rule cannot quietly break.

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

- `Workshop` and `Branch` live in `workshops`. A workshop is the business; a
  branch is one of its locations (ADR-0006).
- Every business model inherits an abstract base from `workshops`, which adds a
  required, indexed `workshop` link. Operational records (job cards, invoices,
  stock, cash) also link to a branch.
- Customers and vehicles belong to the workshop, so all its branches share them.
- Unique rules include the workshop (e.g. a bill number is unique per branch
  of a workshop).
- Queries go through workshop-scoped managers. The current workshop comes from
  the signed-in user's membership.
- Workshop members and platform staff are separate kinds of account
  (ADR-0007).
- Every app has a **leak test**: data from workshop A is never visible to
  workshop B.

## Shared rules

- **Money** (`core`): `Decimal` only, bounds read from the column, a zero or
  negative amount refused by the parser itself.
- **Dates** (`core`): India time, `timezone.localdate()`, never `date.today()`.
- **Audit:** services call `audit` whenever money is changed, deleted or
  back-dated.
- **Notifications:** services call `notifications`; views never do.

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
| Business constants (discount threshold, edit window, back-date limit, markup), number series | `workshops` |
| `money.py`, `money_dates.py`, base templates, design system | `core`, `templates/`, `static/` |
| About page and system map | feature audit: keep or drop |

---

## Open decisions: each becomes an ADR

1. Django version: 5.2 LTS or 6.x.
2. Package manager: `uv` or `pip`.
3. Interactivity: `htmx`, or plain JS modules.
4. **Shop parts and the supplier ledger.** Proposal: `suppliers` owns a
   purchase record; a job's shop-part line points to it (`jobs` imports
   `suppliers`). An unassigned spare is then simply a purchase no job uses yet.
5. Background and scheduled jobs: backups, clean-ups, push.
6. Tenancy enforcement: scoped managers now; PostgreSQL row-level security as
   a second guard later?
7. Per-workshop settings: one settings model, or settings per app.
8. Photo storage: one bucket with a prefix per workshop, or a bucket per
   deployment.

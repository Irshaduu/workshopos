# Plan

What we build, in what order, and where we are.
How we work: `CONTRIBUTING.md` · Structure: `docs/ARCHITECTURE.md` · Why: `docs/adr/`

**Now:** Phase 0 — the developer meets the client for the agreement. In this
repo: the first commit and push.
**Next:** Phase 1 — foundation.
**No code until the agreement is signed** ("agreement before code", below),
unless the developer decides otherwise. Discussion and docs are fine.

Marks: `[x]` done · `[~]` in progress · `[ ]` to do

---

## Goal

- Rebuild the workshop management system — previous version **v1**, once
  called "WorkshopOS Titan" — as **v2**: a clean, tested, tenant-ready product.
- The first client runs it on its own dedicated server.
- The same code can later serve other workshops on a shared server.
- Built in small, reviewed, documented steps.

## Decided

- **One codebase, tenant-ready from the first commit.** → ADR-0003
- **Fresh repository. v1 frozen at tag `titan-final`**, used as the
  specification, not as a code template. → ADR-0002
- **SaaS business features wait for a second workshop.** → ADR-0004
- **No data migration from v1** — it never went live. The client enters only
  its go-live position: old bills, opening stock, opening balances.
- **"Complete for daily work", not "perfect".** Polish after go-live.
- **No delivery date until Phase 5 has been measured.**

## Lessons from v1

| What happened | Rule now |
|---|---|
| Work began before a written agreement | Agreement before code |
| Changes merged with no review step | Every change reviewed and explained before merge |
| Tests run by hand, sometimes only part of them | CI runs every check on every pull request |
| No JavaScript ever ran under test | Browser tests for the key flows |
| One rule copied into many screens | One implementation per rule |
| CSS and JS written inside templates | Static files, a design system, a strict CSP |
| UI decided screen by screen, often reversed | Prototype in the UI lab first, then build |
| Code assumed a single workshop | Tenant-ready from the first commit |
| One huge instruction file; hand-written counts went stale | Short docs, ADRs, no hand-written counts |
| Work left unmerged; dev database behind migrations | Branch → pull request → merge → migrate |
| Client names and a phone number inside the repo | No real people or data in the repo |
| Deploy settings lived only in the hosting dashboard | Everything about deploying lives in the repo |
| Stock moved through signals — an invisible flow | Explicit service calls; no business logic in signals |

---

## Phases

| # | Phase | Status |
|---|---|---|
| 0 | Agreement and v1 freeze | `[~]` |
| 1 | Foundation | `[ ]` |
| 2 | Understand v1 | `[ ]` |
| 3 | Design system (UI lab) | `[ ]` |
| 4 | Core architecture | `[ ]` |
| 5 | Slice 1, timed | `[ ]` |
| 6 | All other sections | `[ ]` |
| 7 | GST and WhatsApp (earlier if GST is legally due first) | `[ ]` |
| 8 | Staging trial → go-live → close watch | `[ ]` |
| 9 | Running it | `[ ]` |
| Later | SaaS business features | `[ ]` |

### Phase 0 — Agreement and v1 freeze

- [ ] Client agreement signed (the checklist is kept privately, outside this repo)
- [ ] From the client: the GST deadline; which sections must be ready before
      go-live; keep / simplify / drop for each v1 section
- [x] v1 tagged `titan-final` and pushed
- [x] v1 moved to `../v1/` (recreate its virtualenv before running it)
- [x] Workspace and this repository created; plan documents written
- [x] Private GitHub repository created: `Irshaduu/workshopos`
- [ ] First commit; `origin` added; `main` pushed
- [x] v1's GitHub repository renamed to `workshopos-v1`

### Phase 1 — Foundation

**Decide — one ADR each**
- [ ] Final product name (the repository can be renamed to match)
- [ ] Django version: 5.2 LTS or 6.x (check current releases first —
      6.x has built-in CSP, template partials and a background-tasks framework)
- [ ] Python version; package manager: `uv` or `pip`
- [ ] Test runner: `pytest-django`
- [ ] Interactivity: `htmx`, or plain JS modules
- [ ] CSS base (decided in the UI lab)
- [ ] Local services: Docker Compose for PostgreSQL
- [ ] Translatable text from day one (Malayalam later)

**Repository**
- [ ] `main` protected; changes only through pull requests
- [ ] Pull request template and issue templates
- [ ] Project board, one milestone per phase
- [ ] `CHANGELOG.md`; tagged releases

**Quality**
- [ ] `ruff` (lint and format); `pre-commit`
- [ ] Import rules between apps, checked in CI (`import-linter`)
- [ ] Dependencies pinned; every new library has an ADR

**Tests**
- [ ] `pytest-django`, factories, coverage report
- [ ] Playwright browser tests
- [ ] JavaScript unit tests with Node's built-in runner

**CI/CD**
- [ ] CI on every pull request: lint, tests, missing-migration check,
      dependency audit, secret scan
- [ ] `main` → staging automatically; release tag → production, every server
- [ ] Deploy configuration in the repo; migrations run before traffic moves

**Environments and settings**
- [ ] Local, CI, staging (fake data), production
- [ ] Settings only from environment variables; `.env.example`
- [ ] Health-check endpoint

**Running live**
- [ ] Error tracking (Sentry) and an uptime monitor
- [ ] Logs never contain customer data
- [ ] Automatic backups, an off-site copy, a monthly test restore

**Docs added when first needed**
- [ ] `docs/rules/` (rule catalogue), `docs/design/`, `RUNBOOK.md`

### Phase 2 — Understand v1

- [ ] The map: every Django layer, and how one request flows through v1
- [ ] How it runs on a server: request → host → gunicorn → Django → PostgreSQL
- [ ] Feature audit with the client: keep / simplify / drop
- [ ] Leave behind: dormant columns, dead templates, unused models
      (e.g. `JobCardLabourItem.amount`, `JobCard.is_deleted`,
      `ConsumptionRecord`, the unrendered bulk-payment templates)
- [ ] Fix, don't port:
  - `parse_money` refuses zero itself — callers must not need their own check
  - Floor's hidden price inputs → a separate form per role
  - seven copied list searches → one component
  - inline JS → static modules (allows a strict CSP)
  - date, back-date and edit-window rules repeated across nine money tables
    → one shared core
  - `is_superuser` meaning "owner" → a membership per workshop
  - bill-number floor in an env var, a single lock row → per-workshop settings
- Rules are catalogued **section by section, as each is built** (the loop,
  step 1) — not all up front.

### Phase 3 — Design system (UI lab)

- [ ] Tokens: colour, type, spacing, radius, shadow
- [ ] About ten components. v1's approved patterns are the first candidates:
      the payment row (`.rpay-*`), the confirmation card (`.wcf-*`), the back
      control (`.pg-back`), chips, status badges
- [ ] Checked at phone, tablet and laptop widths
- [ ] Tried on the real devices by the real users: floor tablet, owners'
      phones, office laptop
- [ ] Accessibility: contrast, 44px touch targets, labels

### Phase 4 — Core architecture

- [ ] Apps and layers as in `docs/ARCHITECTURE.md`; ADR-0005 accepted
- [ ] Tenancy: `Workshop`, a workshop link on every business record,
      workshop-scoped queries
- [ ] Leak test: one workshop can never read another's data
- [ ] Accounts: users; membership = user + workshop + role (Owner / Office / Floor)
- [ ] Permission matrix test: every page × every role
- [ ] Per-workshop number series (JB / WR) and settings (discount threshold,
      edit window, back-date limit, markup)
- [ ] Shared cores: money, dates, audit log, notifications
- [ ] Decide: Customer and Vehicle as real records (v1 keeps them as text
      typed on each card)
- [ ] Decide: how background and scheduled jobs run (backups, clean-ups, push)
- [ ] Safe-migration rules written down

### Phase 5 — Slice 1, timed

- [ ] Login → vehicle → job card → invoice → settle, end to end, with tests
- [ ] Time recorded → a realistic delivery date for the client

### Phase 6 — All other sections

Each section follows the loop in `CONTRIBUTING.md`. Suggested order — the
final order is agreed with the client:

- [ ] Spare shops and their payments
- [ ] Inventory, Supplies Shops and stock costing
- [ ] Cashbook
- [ ] Fleet accounts
- [ ] Estimates
- [ ] Vehicle profile, service history, all invoices for a vehicle
- [ ] Salary and advances
- [ ] Rent and owner withdrawals
- [ ] Profit and deep analysis
- [ ] Change history, notifications, push
- [ ] Warranty
- [ ] Photos
- [ ] Go-live data: old bills, opening stock, opening balances
- [ ] Each section marked: needed before go-live, or after

### Phase 7 — GST and WhatsApp

- [ ] GST details from the client and their accountant: GSTIN, HSN/SAC codes,
      rates, tax-invoice format, CGST + SGST or IGST, rounding, credit notes
- [ ] WhatsApp: a click-to-chat link, or the official API (per-message cost,
      approved templates, which number sends)

### Phase 8 — Go-live

- [ ] Trial on staging with the client
- [ ] Short training for each role
- [ ] Go-live checklist; a written rollback plan, practised on staging
- [ ] Daily error review in the first weeks

### Phase 9 — Running it

- [ ] Releases: staging first, production outside working hours
- [ ] Release notes in plain words
- [ ] Incident plan: what to do when it is down, and who to tell
- [ ] Monthly: test restore, dependency updates, cost check
- [ ] Client feedback becomes issues

### Later — SaaS business features (ADR-0004)

- [ ] Self sign-up, subscription billing, platform admin console,
      feature switches per workshop
- [ ] Own hosting account and domain; terms of service; privacy policy
      (India's DPDP Act)
- [ ] Pilot workshops before any marketing
- [ ] A "Dedicated" plan for workshops that want their own server

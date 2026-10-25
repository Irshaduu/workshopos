# Plan

What we build, in what order, and where we are.
How we work: `CONTRIBUTING.md`. Structure: `docs/ARCHITECTURE.md`.
Modules: `docs/MODULES.md`. Design: `docs/DESIGN.md`. Why: `docs/adr/`.

**Now:** Phase 3, design system (UI lab).
**Alongside:** the client agreement, needed before go-live, not before code.

Marks: `[x]` done, `[~]` in progress, `[ ]` to do

---

## Goal

- Rebuild the workshop management system (the previous version, **v1**, once
  called "WorkshopOS Titan") as **v2**: a clean, tested, SaaS-ready product.
- The first client goes live on it first.
- Other workshops can join the same system later.
- Built in small, reviewed, documented steps.

## Decided

- **One codebase, tenant-ready from the first commit.** (ADR-0003)
- **Fresh repository. v1 frozen at tag `titan-final`**, used as the
  specification, not as a code template. (ADR-0002)
- **Branches inside a workshop; customers and vehicles shared by its
  branches.** (ADR-0006)
- **Two kinds of account: workshop members and platform staff.** (ADR-0007)
- **Modules can be switched on or off per workshop.** Off hides, never
  deletes. (ADR-0011)
- **SaaS business features are planned now and built when a second workshop
  wants the system.** The list is in `docs/MODULES.md`. (ADR-0004)
- **v2 is its own product.** Code does not wait for the client's signature;
  the agreement is needed before go-live.
- **Go live with the daily-work modules** (marked Go-live in
  `docs/MODULES.md`). Everything else follows after go-live.
- **"Complete for daily work", not "perfect".** Polish after go-live.
- **No delivery date until Slice 1 (Phase 5) has been timed.**
- **GST is printed only for a workshop with a valid GSTIN.** All tax rules
  live in one place.
- **No data migration from v1.** It never went live. The client enters only
  its go-live position: old bills, opening stock, opening balances.

## Lessons from v1

| What happened | Rule now |
|---|---|
| Building began with no plan, module list or UI design | Plan, module list and UI lab before code |
| Every module was built before anything went live | Go live with the daily-work modules first |
| Work began before a written agreement | Agreement before go-live |
| Changes merged with no review step | Every change reviewed and explained before merge |
| Tests run by hand, sometimes only part of them | CI runs every check on every pull request |
| The full test suite took about 50 minutes on the laptop | Fast tests by design; the suite timed, with a limit |
| No JavaScript ever ran under test | Browser tests for the key flows |
| One rule copied into many screens | One implementation per rule |
| CSS and JS written inside templates | Static files, a design system, a strict CSP |
| UI decided screen by screen, often reversed | Prototype in the UI lab first, then build |
| Code assumed a single workshop | Tenant-ready from the first commit |
| One huge instruction file; hand-written counts went stale | Short docs, ADRs, no hand-written counts |
| Work left unmerged; dev database behind migrations | Branch, then pull request, merge, migrate |
| Client names and a phone number inside the repo | No real people or data in the repo |
| Deploy settings lived only in the hosting dashboard | Everything about deploying lives in the repo |
| Stock moved through signals, an invisible flow | Explicit service calls; no business logic in signals |
| A service worker re-sent form POSTs, which some browsers dropped | A service worker never re-sends a POST |
| One thing had two names: a fleet account was `BulkPayer` in the code | One name per thing, from `docs/GLOSSARY.md` |

---

## Phases

| # | Phase | Status |
|---|---|---|
| 0 | Plan and v1 freeze | `[x]` |
| 1 | Foundation | `[x]` |
| 2 | Understand v1 | `[x]` |
| 3 | Design system (UI lab) | `[~]` |
| 4 | Core architecture | `[ ]` |
| 5 | Slice 1, timed | `[ ]` |
| 6 | Go-live modules | `[ ]` |
| 7 | Ready to run live | `[ ]` |
| 8 | Staging trial, go-live, close watch | `[ ]` |
| 9 | After go-live: remaining modules, GST, WhatsApp | `[ ]` |
| 10 | Running it | `[ ]` |
| Later | SaaS business features | `[ ]` |

### Alongside: the client

- [ ] Agreement signed, before go-live (the checklist is kept privately,
      outside this repo)
- [ ] Go-live marks in `docs/MODULES.md` confirmed
- [ ] Keep / simplify / drop for each v1 section
- [ ] GST: a valid registration and the accountant's details (moves GST
      before go-live if it is legally due first)

### Phase 0: Plan and v1 freeze

- [x] v1 tagged `titan-final` and pushed
- [x] v1 moved to `../v1/` (recreate its virtualenv before running it)
- [x] Workspace and this repository created; plan documents written
- [x] Private GitHub repository created: `Irshaduu/workshopos`
- [x] First commit; `origin` added; `main` pushed
- [x] v1's GitHub repository renamed to `workshopos-v1`
- [x] Module list (`docs/MODULES.md`); ADR-0006 and ADR-0007; this plan revised

### Phase 1: Foundation

**Decide (one ADR each)**
- [x] Django 6.1 now, then 6.2 LTS (ADR-0009)
- [x] Python 3.14, managed with uv (ADR-0010)
- [x] Code checks and tests: ruff, pre-commit, pytest-django (ADR-0013)
- [x] CI: GitHub Actions, uv audit, gitleaks; the health check (ADR-0014)
- [x] Interactivity: htmx 4 for server calls, small JS modules for the
      rest (ADR-0016)
- [x] Local database: PostgreSQL 18 on the machine, no Docker (ADR-0019)
- [x] Translatable text from day one; Malayalam later (ADR-0015)

**Repository**
- [x] `main` protected; changes only through pull requests, merged with
      "Rebase and merge" once CI is green
- [x] GitHub push protection on, so a secret is stopped before the push
      (ADR-0014)
- [x] Pull request template carrying the definition of done

**Quality**
- [x] `ruff` (lint and format); `pre-commit`
- [x] A `pre-commit` check for the writing rule: no em dashes, arrows or
      decorative symbols in docs
- [x] Dependencies pinned (`uv.lock`); every new library has an ADR

**Tests**
- [x] `pytest-django` and a coverage report

**CI**
- [x] On every push to `main` and every pull request: lint, tests,
      missing-migration check, dependency audit, secret scan (ADR-0014)

**Settings**
- [x] Local environment
- [x] CI environment
- [x] Settings only from environment variables; `.env.example`
- [x] Health-check endpoint

### Phase 2: Understand v1

- [x] The map: every Django layer, and how one request flows through v1
- [x] How it runs on a server: from the request, through the host, gunicorn and Django, to PostgreSQL
- [x] Leave behind (each checked in v1's code; more may show up in each
      section's loop):
  - dormant columns: `JobCard.is_deleted`, `JobCardLabourItem.amount`,
    `CarBrand.logo_image`
  - unused model: `ConsumptionRecord`
  - dead templates: the old fleet payment pages (`bulk_payments.html` and
    its partial), `workshop/home.html`, `inventory/home.html`
  - dead code: the soft-delete signals in `inventory/signals.py`
- [x] Fix, don't port: each item checked in v1's code; each fix is now a
      task in the phase that makes it
- Rules are catalogued **section by section, as each is built** (the loop,
  step 1), not all up front.

### Phase 3: Design system (UI lab)

- [x] CSS base: plain CSS with our own tokens (ADR-0017)
- [x] Tokens: colour, type, spacing, radius, shadow (`docs/design/`)
- [x] About ten components. v1's approved patterns are the first candidates:
      the payment row (`.rpay-*`), the confirmation card (`.wcf-*`), the back
      control (`.pg-back`), chips, status badges; one list search for every
      list page
- [x] Icon set: Lucide, only the icons we use, kept in the repo (ADR-0018)
- [x] Screen states, each designed once (`docs/DESIGN.md`)
- [x] Three signature screens in the lab: live board, job card, owner
      dashboard
- [ ] Each signature screen's size and speed measured on the floor tablet;
      a limit set from it
- [x] JavaScript unit tests, set up with the first JS module
- [x] Checked at phone, tablet and laptop widths
- [ ] Tried on the real devices by the real users (`docs/DESIGN.md`)
- [x] Accessibility: WCAG 2.2 AA (`docs/DESIGN.md`)

### Phase 4: Core architecture

- [ ] Apps and layers as in `docs/ARCHITECTURE.md`; ADR-0005 accepted
- [ ] Import rules between apps checked in CI (`import-linter`, with its
      ADR), from the first app
- [ ] Safe defaults from the first app: every page needs sign-in unless
      marked public; a strict CSP (Django's own); ruff's security rules
- [ ] Translation set up with the first app: `LANGUAGES`, `LOCALE_PATHS`
      (ADR-0015)
- [ ] Factories for test data (factory-boy, ADR-0013), with the first model
- [ ] Tenancy: `Workshop` and `Branch` (ADR-0006); a workshop link on every
      business record, a branch link on operational ones; scoped queries
- [ ] Leak test: one workshop can never read another's data
- [ ] Workshop status: active or suspended
- [ ] One service creates a workshop with its first branch and owner
- [ ] Workshop profile: logo, name, address, GSTIN, UPI QR, used by every
      printed document
- [ ] Accounts (ADR-0007): users; membership = user + workshop + role
      (+ branches); platform staff kept apart; superuser for emergencies only
- [ ] Custom user model in `accounts`, made before any other app's first
      migration (the local database is reset once at that point)
- [ ] Permission matrix test: every page for every role
- [ ] Query-count tests for list pages, so a longer list never means more
      queries
- [ ] Per-workshop settings (discount threshold, edit window, back-date
      limit, markup); bill-number series per branch
- [ ] Customers and vehicles as real records (ADR-0006); decide what
      happens to a car's history when it is sold to a new owner
- [ ] History from day one: kilometres as a number at every visit; times of
      status changes (part ordered and received, work started and fixed,
      car in, ready, delivered)
- [ ] Module switches (ADR-0011): a registry of modules and what each needs;
      one check for menus, pages and assistant tools; off never deletes
- [ ] Shared cores: money (the parser is the only amount check), dates
      (Indian date and number formats; one period filter for every page),
      audit log, notifications
- [ ] A double tap or a slow network never saves a record twice
- [ ] Decide: how background and scheduled jobs run (backups, clean-ups, push)
- [ ] Safe-migration rules written down

### Phase 5: Slice 1, timed

- [ ] Login, vehicle, job card, invoice and settle, end to end, with tests.
      Billing rules for it:
  - the bill is a preview until it is settled
  - the bargaining discount (a bill of 47,500 settled at 45,500, for
    example) is recorded at settle, before tax
  - the final bill number is given at settle
- [ ] The job card has a separate form for each role; no hidden inputs
- [ ] Browser tests (Playwright) for this flow, in both Chrome's and
      Safari's engines
- [ ] The full test suite timed, and a time limit set from it; checked
      again at the end of each phase
- [ ] Time recorded; every Go-live module sized small / medium / large
- [ ] From that, a realistic delivery date for the client

### Phase 6: Go-live modules

Every module marked Go-live in `docs/MODULES.md`, each through the loop in
`CONTRIBUTING.md`. Suggested order (the final order is agreed with the client):

- [ ] The rest of the job card and the floor: live board, live report,
      completed list
- [ ] The rest of billing: printed bill, pending and paid bills, discount audit
  - internal jobs (own car, demo car, free redo) take no customer payment;
    any money from a customer is a sale and gets a proper bill
  - one sales register: every settled sale is in the reports and in the
    accountant's export
- [ ] Spare shops, unassigned spares and payments
- [ ] Supplies shops, inventory and stock costing
- [ ] Cashbook
- [ ] Fleet accounts
- [ ] Change history, alerts, push
- [ ] Go-live tools: old bills, opening stock, opening balances

### Phase 7: Ready to run live

- [ ] Decide hosting for the client: its own account, or the shared server
- [ ] Decide (ADR): the final product name and its domain; the repository
      can be renamed to match
- [ ] Staging (fake data) and production
- [ ] Load test on staging with fake workshops; the worker count and the
      server size come from it
- [ ] `config/settings/production.py`: hosts and security settings from the
      environment (`wsgi.py` and `asgi.py` already point to it)
- [ ] Deploy configuration in the repo; migrations run before traffic moves
- [ ] Decide (ADR): one Dockerfile as the deploy recipe, built in CI and used
      by the host; no Docker needed on the laptop (ADR-0019)
- [ ] `main` goes to staging automatically; a release tag goes to production, on every server
- [ ] Error tracking (Sentry) and an uptime monitor
- [ ] Logs never contain customer data
- [ ] Security pass before go-live: `manage.py check --deploy` clean in CI,
      the dependency audit also weekly, the admin locked down, a review
      against the OWASP Top 10
- [ ] Automatic backups, an off-site copy, a test restore
- [ ] `RUNBOOK.md`

### Phase 8: Staging trial, go-live, close watch

- [ ] Agreement signed
- [ ] Trial on staging with the client
- [ ] Short training for each role
- [ ] Go-live checklist; a written rollback plan, practised on staging
- [ ] `CHANGELOG.md`; first release tag
- [ ] Daily error review in the first weeks

### Phase 9: After go-live

- [ ] Every module marked After in `docs/MODULES.md`, through the loop, in
      the order the client needs
- [ ] GST details from the client and their accountant: GSTIN, HSN/SAC codes,
      rates, tax-invoice format, CGST + SGST or IGST, rounding, credit notes
  - the workshop's GST type, with its start date, sets the final document:
    none gives a plain bill, regular a tax invoice, composition a bill of
    supply (the accountant confirms). Never a choice per customer; old
    bills never change when the type changes.
  - input tax credit tracked from purchase bills
- [ ] WhatsApp: a click-to-chat link, or the official API (per-message cost,
      approved templates, which number sends)
- [ ] Malayalam, when the client wants it: translations, a language choice
      per person, a font check on screens and printed documents (ADR-0015)
- [ ] AI assistant (ADR-0008): first version on fake data, an eval set in CI,
      cost per question measured

### Phase 10: Running it

- [ ] Releases: staging first, production outside working hours
- [ ] Release notes in plain words
- [ ] Incident plan: what to do when it is down, and who to tell
- [ ] Monthly: test restore, dependency updates, cost check
- [ ] Client feedback becomes issues

### Later: SaaS business features (ADR-0004)

- [ ] The SaaS modules in `docs/MODULES.md`
- [ ] Own hosting account and domain
- [ ] Pilot workshops before any marketing
- [ ] A "Dedicated" plan for workshops that want their own server

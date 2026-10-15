# Plan

What we build, in what order, and where we are.
How we work: `CONTRIBUTING.md`. Structure: `docs/ARCHITECTURE.md`.
Modules: `docs/MODULES.md`. Why: `docs/adr/`.

**Now:** Phase 1, foundation. Phase 2 can run alongside it.
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

---

## Phases

| # | Phase | Status |
|---|---|---|
| 0 | Plan and v1 freeze | `[x]` |
| 1 | Foundation | `[ ]` |
| 2 | Understand v1 (alongside Phase 1) | `[ ]` |
| 3 | Design system (UI lab) | `[ ]` |
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
- [ ] Final product name (the repository can be renamed to match)
- [ ] Django version: 5.2 LTS or 6.x (check current releases first:
      6.x has built-in CSP, template partials and a background-tasks framework)
- [ ] Python version; package manager: `uv` or `pip`
- [ ] Test runner: `pytest-django`
- [ ] Interactivity: `htmx`, or plain JS modules
- [ ] Local services: Docker Compose for PostgreSQL
- [ ] Translatable text from day one (Malayalam later)

**Repository**
- [ ] `main` protected; changes only through pull requests
- [ ] Pull request template carrying the definition of done

**Quality**
- [ ] `ruff` (lint and format); `pre-commit`
- [ ] A `pre-commit` check for the writing rule: no em dashes, arrows or
      decorative symbols in docs
- [ ] Import rules between apps, checked in CI (`import-linter`)
- [ ] Dependencies pinned; every new library has an ADR

**Tests**
- [ ] `pytest-django`, factories, coverage report

**CI**
- [ ] On every pull request: lint, tests, missing-migration check,
      dependency audit, secret scan

**Settings**
- [ ] Local and CI environments
- [ ] Settings only from environment variables; `.env.example`
- [ ] Health-check endpoint

**Moved out of Phase 1**
- Browser tests: Phase 5, with the first real flow
- JavaScript unit tests: with the first JS module
- Staging, deploys, error tracking, backups: Phase 7
- `CHANGELOG.md` and release tags: Phase 8
- Project board, milestones, issue templates: dropped; this plan is the board

### Phase 2: Understand v1

Can run alongside Phase 1.

- [ ] The map: every Django layer, and how one request flows through v1
- [ ] How it runs on a server: from the request, through the host, gunicorn and Django, to PostgreSQL
- [ ] Leave behind: dormant columns, dead templates, unused models
      (e.g. `JobCardLabourItem.amount`, `JobCard.is_deleted`,
      `ConsumptionRecord`, the unrendered bulk-payment templates)
- [ ] Fix, don't port:
  - `parse_money` refuses zero itself, so callers need no check of their own
  - Floor's hidden price inputs: replace with a separate form per role
  - seven copied list searches: replace with one component
  - inline JS: move to static modules (allows a strict CSP)
  - date, back-date and edit-window rules repeated across nine money tables:
    move to one shared core
  - `is_superuser` meaning "owner": replace with a membership per workshop (ADR-0007)
  - bill-number floor in an env var and a single lock row: replace with a series per branch
- Rules are catalogued **section by section, as each is built** (the loop,
  step 1), not all up front.

### Phase 3: Design system (UI lab)

- [ ] CSS base decided (ADR)
- [ ] Tokens: colour, type, spacing, radius, shadow
- [ ] About ten components. v1's approved patterns are the first candidates:
      the payment row (`.rpay-*`), the confirmation card (`.wcf-*`), the back
      control (`.pg-back`), chips, status badges
- [ ] Checked at phone, tablet and laptop widths
- [ ] Tried on the real devices by the real users: floor tablet, owners'
      phones, office laptop
- [ ] Accessibility: contrast, 44px touch targets, labels

### Phase 4: Core architecture

- [ ] Apps and layers as in `docs/ARCHITECTURE.md`; ADR-0005 accepted
- [ ] Tenancy: `Workshop` and `Branch` (ADR-0006); a workshop link on every
      business record, a branch link on operational ones; scoped queries
- [ ] Leak test: one workshop can never read another's data
- [ ] Workshop status: active or suspended
- [ ] One service creates a workshop with its first branch and owner
- [ ] Workshop profile: logo, name, address, GSTIN, UPI QR, used by every
      printed document
- [ ] Accounts (ADR-0007): users; membership = user + workshop + role
      (+ branches); platform staff kept apart; superuser for emergencies only
- [ ] Permission matrix test: every page for every role
- [ ] Per-workshop settings (discount threshold, edit window, back-date
      limit, markup); bill-number series per branch
- [ ] Customers and vehicles as real records (ADR-0006)
- [ ] Shared cores: money, dates, audit log, notifications
- [ ] Decide: how background and scheduled jobs run (backups, clean-ups, push)
- [ ] Safe-migration rules written down

### Phase 5: Slice 1, timed

- [ ] Login, vehicle, job card, invoice and settle, end to end, with tests
- [ ] Browser tests (Playwright) for this flow
- [ ] Time recorded; every Go-live module sized small / medium / large
- [ ] From that, a realistic delivery date for the client

### Phase 6: Go-live modules

Every module marked Go-live in `docs/MODULES.md`, each through the loop in
`CONTRIBUTING.md`. Suggested order (the final order is agreed with the client):

- [ ] The rest of the job card and the floor: live board, live report,
      completed list
- [ ] The rest of billing: printed bill, pending and paid bills, discount audit
- [ ] Spare shops, unassigned spares and payments
- [ ] Supplies shops, inventory and stock costing
- [ ] Cashbook
- [ ] Fleet accounts
- [ ] Change history, alerts, push
- [ ] Go-live tools: old bills, opening stock, opening balances

### Phase 7: Ready to run live

- [ ] Decide hosting for the client: its own account, or the shared server
- [ ] Staging (fake data) and production
- [ ] Deploy configuration in the repo; migrations run before traffic moves
- [ ] `main` goes to staging automatically; a release tag goes to production, on every server
- [ ] Error tracking (Sentry) and an uptime monitor
- [ ] Logs never contain customer data
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
- [ ] WhatsApp: a click-to-chat link, or the official API (per-message cost,
      approved templates, which number sends)

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

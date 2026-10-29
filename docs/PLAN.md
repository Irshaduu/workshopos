# Plan

What we build, in what order, and where we are.
How we work: `CONTRIBUTING.md`. Structure: `docs/ARCHITECTURE.md`.
Modules: `docs/MODULES.md`. Design: `docs/DESIGN.md`. Why: `docs/adr/`.

**Now:** Phase 5, Slice 1, is in progress: Sign-in is built; Roles is
next.
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
- **Go live complete for daily work.** Extra features and polish wait
  until after go-live; correctness, edge cases and tests never wait.
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
| Back, after signing out on a shared laptop, showed a customer's bill again | A signed-in page is never kept by the browser |

---

## Phases

| # | Phase | Status |
|---|---|---|
| 0 | Plan and v1 freeze | `[x]` |
| 1 | Foundation | `[x]` |
| 2 | Understand v1 | `[x]` |
| 3 | Design system (UI lab) | `[x]` |
| 4 | Core architecture | `[x]` |
| 5 | Slice 1, timed | `[~]` |
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
- [x] JavaScript unit tests, set up with the first JS module
- [x] Checked at phone, tablet and laptop widths
- [x] Accessibility: WCAG 2.2 AA (`docs/DESIGN.md`)

### Phase 4: Core architecture

Phase 4 builds only what every later app stands on. A task that needs a
page, a form or a business record is built with the first one, mostly in
Slice 1.

**1. First app, safe base**
- [x] Apps and layers as in `docs/ARCHITECTURE.md`; ADR-0005 accepted
- [x] Decide (ADR): primary keys, UUID7 or numbers, before the first model
      (ADR-0022)
- [x] Import rules and model links between apps checked in CI
      (`import-linter`, with its ADR, and a test), from the first app
      (ADR-0021)
- [x] Custom user model in `accounts`, made before any other app's first
      migration (the local database is reset once at that point)
- [x] Safe defaults from the first app: every page needs sign-in unless
      marked public; a signed-in page is never kept by the browser; a
      strict CSP (Django's own); ruff's security rules
- [x] Translation set up with the first app: `LANGUAGES`, `LOCALE_PATHS`
      (ADR-0015)
- [x] Factories for test data (factory-boy, ADR-0013), with the first model

**2. Tenancy**
- [x] Tenancy, decided in an ADR first (ADR-0023): `Workshop` and `Branch`
      (ADR-0006); a workshop link on every business record; scoped queries
- [x] Leak test: one workshop can never read another's data; it covers
      every workshop model by itself
- [x] Workshop status: active or suspended, and one place that says whether
      a workshop may work now

**3. Members**
- [x] Accounts (ADR-0007): membership = account + workshop + role, one
      workshop per account for now; staff and superusers are never members;
      each request gets its workshop from the membership and asks
      `may_work()` (ADR-0023)
- [x] One service in `accounts` creates a workshop with its first branch
      and owner

**4. Per-workshop choices**
- [x] Per-workshop settings: where they live, decided in an ADR
      (ADR-0024); each setting is built with the feature that uses it
- [x] Module switches (ADR-0011): checked again; built in two steps, from
      the first page (Slice 1) and when a workshop first needs a module off

**5. Shared cores**
- [x] Shared cores (money, dates, audit log, notifications): checked
      again; each is built with its first user, in Slice 1 and Phase 6

### Phase 5: Slice 1, timed

Build order. Each step goes through the loop in `CONTRIBUTING.md`; base
work gets its own pull request, just before the page that first uses it.

1. Sign-in, with its ADR
2. Roles, with its ADR: the page mark, the module list, the permission
   matrix, and the app's tab bar and menu (v1's, through the lab), which
   takes over Sign out from the plain home page
3. Base for the first pages: Indian formats, the `for_workshop()` check,
   the double-tap guard, the query-count test
4. Staff list: the first list page and form
5. Money base, just before the first money column
6. Job card: customers and cars, the number, the links, history, a form
   per role
7. Known plate: old plates, the chassis number, moving an open job card
8. Settle bill: payments, the discount, the frozen copy, the first
   settings, the audit log
9. Browser tests and limits, with the Playwright ADR
10. Close: the hours sorted, the other modules sized, the delivery date

- [ ] One car, from sign-in to a settled bill, end to end, with tests. It
      builds these Go-live modules whole (`docs/MODULES.md`), each through
      the loop in `CONTRIBUTING.md`: Sign-in, Roles, Staff list, Job
      card, Known plate, Settle bill. The rest waits for
      Phase 6, like parts on the job card, fleet accounts and the printed
      bill. Billing rules for it:
  - the bill is a preview until it is settled
  - settle is one step: Office or an owner types what the customer paid,
    by method (cash, UPI, card or bank transfer; one bill can use two),
    and the rest of the bill is the discount, shown before saving; each
    payment is its own row; an amount above the bill is refused
  - the bargaining discount (a bill of 43,000 settled at 40,000, for
    example) is saved as its own amount, before tax, and the bill shows
    it with its label; the total is called Net, never Paid
  - one number per visit, as in v1 (JB-26-027): given when the job card
    is made, it is the job card's number and its bill's number; a job
    card that ends with no bill is cancelled with a reason, never
    deleted, and keeps its number
  - the settled bill keeps a frozen copy of the customer and the car as
    printed, so fixing a name later, or a customer's request to delete
    their data, never changes an old bill
- [ ] Customers and vehicles as real records (ADR-0006), built with the
      job card. In a workshop, a car keeps one record and its whole
      history; each job card keeps the customer and the plate of that
      visit; a sale changes only the owner, and a new plate (a car from
      another state registered here, a temporary plate made permanent)
      only the plate, from that day on; Floor never sees customers (v1). A
      job card finds its car by the plate, an old plate or the chassis
      number (VIN), as v1's Known plate did; old bills join that search
      with the old bills tool (Phase 6). The chassis number stays optional,
      with v1's checks. A plate or a chassis number belongs to one car in a
      workshop; when two cars claim one, the car in front of you, checked
      against its RC, keeps it, and the other car's is asked again at its
      next visit. A chassis number never decides alone: a match asks "same
      car with a new number?", only when the make matches. Office can move
      an open job card to the right car; a settled one never moves. The
      car's page (Car profiles, After) gets the same changes; no merge tool
      unless the staging trial shows a need
- [ ] A branch link on operational records, and every link kept inside its
      workshop by PostgreSQL (`SameWorkshop`, ADR-0023), from the job card;
      a factory gives its linked records the same workshop
- [ ] A pre-commit check that every query in `apps/` starts with
      `for_workshop()`, unless the line says why not, from the first
      selector (ADR-0023); it also flags Django's shortcuts that query by
      themselves (`get_object_or_404(Model, ...)`, a class-based view's
      `model =`, `_default_manager`)
- [ ] History from day one, with the job card: kilometres as a whole
      number at every visit, or blank when the odometer does not work,
      never miles (settle warns when it is blank, as v1 does); the time of
      every step the workflow has (car in, each concern started and fixed,
      on hold and back, ready), kept as rows, one per change, because ready
      can be undone; part ordered and received come with parts (Phase 6); a
      delivered step only if the client asks (v1 had none)
- [ ] The first per-workshop settings (ADR-0024), with settle: how far
      back Office may date money (v1: 3 days), and how long Office may
      change a settled bill before only owners can (v1: 24 hours); the
      big-discount alert limit comes with the bell (Phase 6)
- [ ] The number series per branch: a counter locked when a job card is
      made, never a PostgreSQL sequence (it skips a number when a save
      fails); the letters (JB) and the yearly restart are the branch's,
      like v1's JB-26-097, or each financial year if the accountant asks
      (GST: unique in a financial year, at most 16 characters); it starts
      after the last Excel bill number, and a number is used once, old
      bills included
- [ ] Money, with the first money column: one size for every money
      column, v1's numeric(12, 2); typed amounts through Django's decimal
      form field, no parser of our own; a zero or negative amount refused
      by the model and by PostgreSQL; the money date rules (no future date,
      how far back Office may go) with the first money page
- [ ] Indian dates and numbers on screen, with the first page: one formats
      file, read by Django's own filters (26 Oct 2026; 1,50,000, 1,50,000.50
      or 1,50,000.00 through `floatformat`), so v1's own rupee filters are
      not rebuilt; only the short figure for a big number on a phone
      (45.2L) is our own code, in `core`; which style each screen uses, with
      v1's reasons, written in `docs/DESIGN.md`
- [ ] The audit log, in the same pull request as the first service that
      changes, deletes or back-dates money: a frozen copy of what changed,
      with who, when and why (v1's shape, in one table), saved in the same
      transaction; every service that changes money is told who acts. Its
      first entries: a change to a settled bill (amount, discount, payment,
      date); a first settle is not a change (v1)
- [ ] Every page and menu item names its module, from the first page: a
      list of modules in the code, where each app adds its own, and a test
      that fails for a page with no module or an unknown one (ADR-0011). A
      page's one mark names its module and what it needs from the roles
      list, and one check reads both (decided with the roles ADR); this
      test and the permission matrix go through the same list of pages
- [x] Sign-in, as ADR-0025 decides, with every rule in
      `docs/rules/sign-in.md` built and tested; SIGN-39 comes with the first
      htmx call, and the rules marked Phase 6 with the Staff logins page and
      the bell
- [ ] Roles checked in one place, decided in an ADR with the first page: a
      list of what each role may do (each app adds its own, like the module
      list), and no page checks a role by name, so a new role is added
      without changing pages; Django's own permission check (`has_perm`,
      `perms` in templates) tried first. The ADR replaces ADR-0007's Floor
      line: Floor sees the whole floor (one shared login), never prices or
      customer details
- [ ] Permission matrix test, from the first page: it finds every page by
      itself, so a page with no row fails; the expected answers are typed
      in the test, never read from the roles list; for each page, a visitor
      who is signed out is sent to sign in, each role gets in or is
      refused, and a record of another workshop is never found
- [ ] Query-count tests for every page that shows rows (a list page, a job
      card's lines), from the first one: the page opened with a few rows
      and with many makes the same number of queries, so a longer list
      never means more queries
- [ ] A double tap or a slow network never saves a record twice, from the
      first form. The server is the guard; the button only shows it is
      busy. A new record's key comes in the form's address (UUID7 keys exist
      before saving, ADR-0022), so PostgreSQL refuses a second copy and the
      page shows the saved one; a change runs in one locked transaction
      that refuses a repeat (a settled bill is never settled twice)
- [ ] A separate form for each role, on every form, not only the job card:
      a field a role may not change is left out of its form, never hidden
      (v1: a Floor post changed a price it could not see); the rule goes
      into `CONTRIBUTING.md` with the first role form
- [ ] Browser tests (Playwright, with its ADR first) for the key flows
      only: sign in, open a job card, settle a bill; in both Chrome's and
      Safari's engines (`docs/DESIGN.md`), in their own CI job, which
      `main` also requires; the real iPhones are checked in the staging
      trial (Phase 8)
- [ ] The full test suite timed, and a time limit set from it in CI (the
      test job's `timeout-minutes`), so a slow suite fails loudly; checked
      again at the end of each phase
- [ ] A stand-in speed limit, measured with Playwright in Chrome set to act
      like a slow phone (`docs/DESIGN.md`): CI fails when the job card
      page's size (bytes downloaded, number of files) passes the limit;
      its time on a slow phone is written down at the end of each phase,
      and the floor tablet confirms it in the staging trial
- [ ] Time recorded per pull request, each sorted as one module's work or
      one-time setup (base work gets its own pull request, before the page
      that first uses it); then every other Go-live module and every Phase 7
      task sized small, medium or large against them
- [ ] From that, a delivery date for the client, as a range: the rest of
      Phases 6 to 8, from the measured sizes and hours per week, saying the
      hours per week it assumes; checked again at the end of each phase

### Phase 6: Go-live modules

Every module marked Go-live in `docs/MODULES.md`, each through the loop in
`CONTRIBUTING.md`. Suggested order (the final order is agreed with the client):

- [ ] The rest of the job card and the floor: live board, live report,
      completed list
- [ ] The rest of billing: printed bill, pending and paid bills, discount audit
  - the workshop profile on the printed bill: its name and logo, the
    branch's address and phone, the UPI QR, with the file storage decision
    (`docs/ARCHITECTURE.md`, open decision 5); an old bill keeps the
    details it was printed with
  - one period filter for every page that filters by date, from the first
    one
  - internal jobs (own car, demo car, free redo) take no customer payment;
    any money from a customer is a sale and gets a proper bill
  - one sales register: every settled sale is in the reports and in the
    accountant's export
- [ ] Spare shops, unassigned spares and payments
- [ ] Supplies shops, inventory and stock costing
- [ ] Cashbook
- [ ] Fleet accounts
- [ ] The change history screen, alerts and push: the bell comes with
      the first alert, v1's big-discount alert at settle
- [ ] Decide (ADR): how background and scheduled jobs run (backups,
      clean-ups, push), with push, the first one
- [ ] Go-live tools: old bills, opening stock, opening balances
- [ ] Module switches, if the client does not use a go-live module: the
      on/off choice per workshop, one check for menus, pages and
      assistant tools, the modules each one needs, and "module off" in
      the permission tests (ADR-0011)

### Phase 7: Ready to run live

- [ ] Decide hosting for the client: its own account, or the shared server
- [ ] Decide (ADR): the final product name and its domain; the repository
      can be renamed to match
- [ ] Staging (fake data) and production
- [ ] Load test on staging with fake workshops; the worker count and the
      server size come from it
- [ ] `config/settings/production.py`: hosts and security settings from the
      environment (`wsgi.py` and `asgi.py` already point to it); errors
      written to the console, database connections kept open, and a
      "noindex" header on every answer, as v1's settings do
- [ ] The host's health check gets its answer: its host name allowed
      (Railway calls `/health/` as `healthcheck.railway.app`), and no
      redirect to HTTPS first
- [ ] Decide (ADR): static files with hashed names and compressed pages,
      and how both are served (v1: WhiteNoise and GZipMiddleware, because
      Railway's proxy did not compress); JS imports rewritten too
      (`support_js_module_import_aggregation`)
- [ ] The production mailer: a web service, not SMTP (v1: Railway blocks
      SMTP below its Pro plan, so v1 used Resend); the shared settings have
      none. Owners sign in with an emailed code (ADR-0025), so the sending
      domain gets its SPF, DKIM and DMARC records, and a code is tried in
      each owner's own mailbox
- [ ] Deploy configuration in the repo; migrations run before traffic moves
- [ ] Safe-migration rules written down, before the first real data
- [ ] Decide (ADR): one Dockerfile as the deploy recipe, built in CI and used
      by the host; no Docker needed on the laptop (ADR-0019)
- [ ] `main` goes to staging automatically; a release tag goes to production, on every server
- [ ] Error tracking (Sentry) and an uptime monitor
- [ ] Logs never contain customer data
- [ ] Security pass before go-live: `manage.py check --deploy` clean in CI,
      the dependency audit also weekly, the admin locked down, the
      superuser's two-factor sign-in (ADR-0007), a review against the
      OWASP Top 10
- [ ] Decide a sign-in limit per internet address, once the host's proxy
      is measured; needed before a second workshop shares a server
      (ADR-0025)
- [ ] Automatic backups, an off-site copy, a test restore
- [ ] `RUNBOOK.md`

### Phase 8: Staging trial, go-live, close watch

- [ ] Agreement signed
- [ ] Trial on staging with the client
- [ ] In the trial, the real users try every go-live screen on their own
      devices (`docs/DESIGN.md`)
- [ ] In the trial, each go-live screen's size and speed measured on the
      floor tablet; the Slice 1 limit confirmed or changed
- [ ] Short training for each role
- [ ] Go-live checklist; a written rollback plan, practised on staging
- [ ] `CHANGELOG.md`; first release tag
- [ ] Daily error review in the first weeks

### Phase 9: After go-live

- [ ] Every module marked After in `docs/MODULES.md`, through the loop, in
      the order the client needs
- [ ] GST details from the client and their accountant: GSTIN (one per
      state, so a branch in another state has its own), HSN/SAC codes,
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
- [ ] PostgreSQL row-level security as a second guard, before a second
      workshop's data shares a database (ADR-0023)
- [ ] Pilot workshops before any marketing
- [ ] A "Dedicated" plan for workshops that want their own server

# Contributing

How work is done here.
What is planned: `docs/PLAN.md`. Structure: `docs/ARCHITECTURE.md`. Why: `docs/adr/`.

`ruff`, `pre-commit` and `pytest` are set up (ADR-0013), and CI runs every
check on GitHub (ADR-0014). **`main` is protected:** every change reaches it
through a pull request, and only when CI is green.

---

## The flow

1. A **branch**: `feat/<short-name>`, `fix/...`, `docs/...`, `refactor/...`, `chore/...`.
2. **Small commits**, each with its tests.
3. A **pull request** into `main`. Its template says why and what changed,
   and carries the definition of done. CI must pass.
4. **Rebase and merge**: each commit lands on `main` with its own checked
   message, in a straight line, and the branch is deleted. Staging deploys.
   A **release tag** deploys to production, on every server.
5. On the laptop: `git switch main`, then `git pull`.

An **issue** is only for work that has to wait: a bug found, or a client
request for later. The pull request that does it says `Fixes #N`, which
closes the issue.

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/):
`type(scope): summary`, for example `feat(jobs): settle a bill`

- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`
- Summary: present tense, 72 characters or fewer
- Body: **why**, not what. The diff already shows what.

---

## Building a section: the loop

1. **Rules:** list the section's rules from v1 into `docs/rules/<section>.md`,
   each with an ID, and its words into `docs/GLOSSARY.md`.
2. **UI lab:** prototype the designs below; compare them on phone, tablet
   and laptop; choose.
3. **Plan:** a short written plan: models, screens, tests. Approved before code.
4. **Build:** small commits on a branch, tests in the same commit.
5. **Explain:** every commit is explained and understood before merge.
6. **Check:** CI green; clicked through in a browser; behaviour matches v1.
7. **Sign-off:** the client checks it on staging.
8. **Merge:** rule catalogue updated; an ADR if a decision was made.

## UI lab

- Lives in `design/lab/<section>/`. **Never imported by the app.**
- Uses the real design tokens and the same fake data, and follows
  `docs/DESIGN.md`.
- The design system is the first prototype, before any section.
- **A big choice** (the overall look, a main screen) starts from v1: v1's
  screen rebuilt in the lab with the same contents, layout and colours,
  fixed only where it breaks a rule. The fixes stay small; the structure
  and the look stay v1's. Why: v1's screens were settled with the owners,
  the staff already know them, and v1 was chosen every time it was
  compared.
- **A second design**, v1 refined (v1 made better in our own way, for the
  same job), is made only when the developer asks for one, or when a rule
  fix would change the layout. Then one is chosen, or parts of both are
  combined.
- Screenshots of v1 with fake data are the reference for the rebuild and
  stay out of git. A screen v1 never had gets one proposed design, with the
  reason it is recommended.
- **A small choice** (one colour, one space) gets one version, changed if
  needed.
- After each decision the other designs are **deleted**. The chosen one stays
  in the lab as the reference until its screen is built, then it is deleted
  too. One screenshot and one line of reasoning stay in `docs/design/`.
- One page stays: `design/lab/system/`, every token and component in every
  state, the reference to check before writing a screen (ADR-0017).

---

## Code rules

- **One implementation per rule.** Search before writing anything new.
- **One name per thing** (`docs/GLOSSARY.md`). The word on screen is the
  name in models, functions, files, URLs and docs. A new word goes in the
  glossary first.
- **Extract on the second use**, never before. No abstraction for one caller.
- **Code goes where `docs/ARCHITECTURE.md` says.** Views thin; rules in
  `services.py` (changes) and `selectors.py` (reads).
- **Every business model builds on `WorkshopModel`**
  (`apps/workshops/models.py`), so each record belongs to one workshop
  (ADR-0023). A model left out is listed, with why, in
  `tests/test_tenancy.py`.
- **No query without its workshop.** A selector or service takes the
  workshop as its first argument, and its queries start with
  `Model.objects.for_workshop(workshop)`. Never a hidden current workshop.
- **An app imports, and links its models, only to lower layers**
  (ADR-0005). A new app is placed on its floor in `pyproject.toml` in the
  same commit. No generic links (`GenericForeignKey`): PostgreSQL cannot
  guard them. Tests check all three (ADR-0021).
- **Every model builds on `core`'s base model** (`apps/core/models.py`), so
  its key is a UUID7 that exists before saving (ADR-0022). To know if a
  record is saved, ask Django's `_state.adding`, never "is the key empty?".
  A test checks every model.
- **Every page needs sign-in.** A public page is marked
  `@login_not_required`, with a comment saying why.
- **Every page needs a workshop that may work now**, read from
  `request.workshop` (ADR-0023). A page that works without one, like
  signing out, is marked `@workshop_not_required`
  (`apps/accounts/decorators.py`), with a comment saying why.
- **Money is `Decimal`, never `float`.** Dates use `timezone.localdate()`.
- **Every text a person sees is marked for translation** (ADR-0015):
  `{% translate %}` in templates, `gettext_lazy` in Python.
- **No business logic in signals.**
- **Let PostgreSQL 18 guard the data** (ADR-0019). Before writing a model or
  a query, check what PostgreSQL 18 and Django can do in the database:
  constraints (unique, check, exclusion), generated fields, database
  defaults, `UUID7`. Use one when it makes the data safer or the code
  simpler, not because it is new. Write it through Django in `models.py`,
  never as a trigger or a stored procedure, so the flow stays visible.
- **No CSS or JS inside templates**: no `style` attribute, inline `<script>`
  or `onclick` in any HTML; scripts come from static files. pre-commit
  checks it.
- **A colour is written only in `static/css/tokens.css`.** Every other file
  uses its token (ADR-0017). pre-commit checks it.
- **A size in px or rem is written only in `static/css/tokens.css`**
  (ADR-0017), except 1px and 2px lines and media query widths. Lab pages
  stay as chosen; when a screen is built, each size takes the nearest
  token, or a new token when the difference shows. pre-commit checks it
  outside `design/lab/`.
- **The server decides; JavaScript only shows** (ADR-0016). htmx 4 for
  server calls: mark inherited attributes with `:inherited`, use the htmx 4
  event names, and no `hx-on`, `js:` values or trigger filters. JS modules
  hold no business rules and work out no money.
- **Delete code; never comment it out.** Git remembers.
- **No dead files, no experiments on `main`.**
- **Every new dependency needs an ADR.**

## Tests

- **Every rule has a test**, named after the rule it protects, and linked to
  its rule ID.
- **Test the invariant, not the implementation.** For example, two screens agree, or a
  total adds up from its own rows.
- **Factories, not hand-made fixtures.**
- **The leak test covers every workshop model by itself**
  (`tests/test_tenancy.py`). Each one needs a factory: `<Model>Factory` in
  its app's `tests/factories.py`.
- **A permission matrix**: every page for every role, and a record of
  another workshop is never found.
- **Browser tests** for the key flows.
- **A JavaScript module's plain functions are tested with Node's own test
  runner**, in `tests/js/` (ADR-0020). No npm and no test library.
- **A failing test means the code regressed.** Fix the code, not the test.

## Docs

- **One fact, one home.** Link; never repeat.
- **A plan task is one line, in the phase that does it.** Its detail lives
  in its home doc.
- **No hand-written counts.** Generate them or leave them out.
- **Docs say what is true now.** History lives in git and in ADRs.
- **An ADR for every decision that is hard to undo.** The format is in
  `docs/adr/README.md`.
- **Re-check a plan when its building starts.** An ADR, plan task or
  design written earlier is checked again against what changed since and
  against the whole system: is there now a simpler, safer or more stable
  way? The check fits the item: one line for a small task, full pros and
  cons for an ADR, a design or a rule. It ends in a decision: keep,
  change or drop. A Proposed ADR is edited; an Accepted one is replaced by
  a new ADR. The aim is the best fit for the whole system now. Scope can
  wait; quality never does: whatever is built gets every rule, edge case
  and test (`docs/PLAN.md`).
- **Plain, natural English** in docs, screens and commit messages. Short
  sentences, everyday words, no em dashes, arrows or decorative symbols.
- **Written so another developer could take over.**
- **No client names, customer data or personal details anywhere in the repo.**

---

## Definition of done

The checklist lives in the pull request template
(`.github/pull_request_template.md`), so every pull request carries it.

## Never commit

- `.env` or any secret
- Real customer data, database dumps, backups
- Logs, build output, caches

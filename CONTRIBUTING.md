# Contributing

How work is done here.
What is planned: `docs/PLAN.md`. Structure: `docs/ARCHITECTURE.md`. Why: `docs/adr/`.

`ruff`, `pre-commit` and `pytest` are set up (ADR-0013), and CI runs every
check on GitHub (ADR-0014). Branch protection comes next in Phase 1. **Until
it exists, commits go straight to `main`.** Branches and pull requests start
then.

---

## The flow

1. An **issue** describes the change.
2. A **branch**: `feat/<short-name>`, `fix/...`, `docs/...`, `refactor/...`, `chore/...`.
3. **Small commits**, each with its tests.
4. A **pull request** into `main`. CI must pass.
5. **Merge**, and staging deploys. A **release tag** deploys to production, on every server.

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/):
`type(scope): summary`, for example `feat(jobs): settle a bill`

- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`
- Summary: present tense, 72 characters or fewer
- Body: **why**, not what. The diff already shows what.

---

## Building a section: the loop

1. **Rules:** list the section's rules from v1 into `docs/rules/<section>.md`,
   each with an ID.
2. **UI lab:** prototype a fresh design; compare with v1 on phone, tablet
   and laptop; choose.
3. **Plan:** a short written plan: models, screens, tests. Approved before code.
4. **Build:** small commits on a branch, tests in the same commit.
5. **Explain:** every commit is explained and understood before merge.
6. **Check:** CI green; clicked through in a browser; behaviour matches v1.
7. **Sign-off:** the client checks it on staging.
8. **Merge:** rule catalogue updated; an ADR if a decision was made.

## UI lab

- Lives in `design/lab/<section>/`. **Never imported by the app.**
- Uses the real design tokens and the same fake data.
- The design system is the first prototype, before any section.
- After each decision the prototype is **deleted**. One screenshot and one line
  of reasoning stay in `docs/design/`.

---

## Code rules

- **One implementation per rule.** Search before writing anything new.
- **Extract on the second use**, never before. No abstraction for one caller.
- **Code goes where `docs/ARCHITECTURE.md` says.** Views thin; rules in
  `services.py` (changes) and `selectors.py` (reads).
- **Every business record belongs to a workshop.** No query without it.
- **An app imports only from lower layers.**
- **Money is `Decimal`, never `float`.** Dates use `timezone.localdate()`.
- **No business logic in signals.**
- **No CSS or JS inside templates.**
- **Delete code; never comment it out.** Git remembers.
- **No dead files, no experiments on `main`.**
- **Every new dependency needs an ADR.**

## Tests

- **Every rule has a test**, named after the rule it protects, and linked to
  its rule ID.
- **Test the invariant, not the implementation.** For example, two screens agree, or a
  total adds up from its own rows.
- **Factories, not hand-made fixtures.**
- **A leak test per app** and a **permission matrix** (every page for every role).
- **Browser tests** for the key flows.
- **A failing test means the code regressed.** Fix the code, not the test.

## Docs

- **One fact, one home.** Link; never repeat.
- **No hand-written counts.** Generate them or leave them out.
- **Docs say what is true now.** History lives in git and in ADRs.
- **An ADR for every decision that is hard to undo.** The format is in
  `docs/adr/README.md`.
- **Plain, natural English** in docs and commit messages. Short sentences,
  everyday words, no em dashes, arrows or decorative symbols.
- **Written so another developer could take over.**
- **No client names, customer data or personal details anywhere in the repo.**

---

## Definition of done

- [ ] Rules listed with IDs; each rule has a test
- [ ] CI green: lint, tests, migrations, import rules, audit, secret scan
- [ ] Checked by hand in a browser at phone, tablet and laptop widths
- [ ] Behaviour matches v1, or the difference is decided and recorded
- [ ] Docs updated in the same pull request
- [ ] No dead code, no stray files

## Never commit

- `.env` or any secret
- Real customer data, database dumps, backups
- Logs, build output, caches

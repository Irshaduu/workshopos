# 0021: Layer checks: import-linter for imports, our own test for model links

**Status:** Accepted (2026-10-26)

## Context

- ADR-0005 puts every app on a floor: an app imports, and links its models,
  only to the floors below its own. Unless a machine checks it, the rule
  quietly breaks: v1's two big apps imported each other.
- import-linter reads `import` lines. A Django link written as text, like
  `ForeignKey("billing.FleetAccount")`, needs no import, so it cannot see
  one.
- Compared on 2026-10-26:
  - import-linter 2.15: stable, BSD licence, supports Python 3.14, also
    checks indirect chains, clear messages.
  - Tach 0.35: fast, but still below version 1.
  - Our own import reader: no new package, but its edge cases (relative
    imports and others) would be ours to keep right.
  - ruff's banned imports: one setting per app, and no idea of floors.
- ADR-0005 said an app is created with its first model or page. `core`
  holds shared tools, which are neither.

## Decision

- **import-linter checks the imports.** One `layers` contract in
  `pyproject.toml` holds the floors of `docs/ARCHITECTURE.md`:
  - every app is listed; apps on one row are written with `|`, so they
    never use each other;
  - an app not built yet is in brackets, which come off when it is built;
  - `exhaustive` is on, so a new app folder that is not placed on a floor
    fails.
- **Our own test checks the model links** (foreign keys, one-to-one and
  many-to-many): each points to its own app or a lower floor. It reads the
  floors from the same contract, so the order has one home. Links to
  Django's own apps are allowed: they sit below everything.
- **The same test fails on a generic link** (`GenericForeignKey`,
  `GenericRelation`): PostgreSQL cannot guard one (ADR-0019).
- **Both run in the tests** (`tests/test_layers.py`), so CI's Tests job
  stops a pull request that breaks them. `uv run lint-imports` runs the
  import check by hand.
- No exception (`ignore_imports`) without a line saying why, reviewed in
  its pull request.
- Versions: import-linter 2.15 with grimp 3.17. grimp 3.18 came out the day
  this was written.
- **An app is created with its first real code: a model, a page or a
  shared tool.** No empty apps.

## Consequences

- A wrong import or link fails the tests, naming the apps and the field.
  Each check was shown to catch a planted mistake: an import up a floor,
  an import inside one row, a bracketed app that exists, an app folder not
  placed, and a generic link.
- A new app is placed on its floor in `pyproject.toml` in the same commit.
- pre-commit does not run import-linter. A hook would call `uv`, which is
  not on the laptop's PATH, or keep a second copy of the versions in
  `.pre-commit-config.yaml`, which would drift. A broken floor is caught by
  the tests, on the laptop and in CI, instead of at the commit.
- New development-only packages: import-linter, grimp, click, rich,
  markdown-it-py, mdurl and typing-extensions. None run on the server.
  More packages can bring more audit notices.

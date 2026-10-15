# 0013: Code checks and tests: ruff, pre-commit, pytest-django

**Status:** Accepted (2026-10-15)

## Context

- v1 ran its tests by hand, sometimes only part of them, and had no
  automatic style or lint check.
- The plan asks for one formatter and linter, checks before every commit,
  and `pytest-django`.
- The writing rule (`CONTRIBUTING.md`, Docs) is easy to forget, so a check
  should enforce it.

## Decision

- **ruff** checks and formats all Python. Rules: E, W, F, I, UP, B and DJ;
  lines up to 100 characters. Its settings live in `pyproject.toml`.
- **pre-commit** runs before every commit: ruff check (with safe fixes),
  ruff format, and the plain-writing check on docs, code and the commit
  message. Its ruff version is kept the same as the one in `uv.lock`.
- **pytest** with **pytest-django** runs the tests on a real PostgreSQL test
  database, never SQLite. **pytest-cov** measures coverage. Test settings live
  in `config/settings/test.py`.
- **factory-boy** makes test data, added with the first model.
- All of these are development-only dependencies (the uv `dev` group).

## Consequences

- The same checks run on every machine; CI runs the same commands.
- A commit can be stopped by a check: fix it and commit again. A person can
  skip the hooks on purpose (`--no-verify`), so CI is the final guard.
- The ruff version is named in two places (`uv.lock` and
  `.pre-commit-config.yaml`); they are updated together.

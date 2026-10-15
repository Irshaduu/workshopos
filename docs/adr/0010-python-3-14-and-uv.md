# 0010: Python 3.14, managed with uv

**Status:** Accepted (2026-10-15)

## Context

- Django 6.1 supports Python 3.12, 3.13 and 3.14.
- Python 3.15.0 was released on 2026-10-09; Django does not support it yet.
  Python 3.14 has had a year of fixes.
- The laptop, CI and every server must run exactly the same versions of
  Python and of every library.
- On the development laptop (Windows), `python` opens the Microsoft Store.

## Decision

- Python 3.14, pinned in `.python-version` and in `requires-python`.
- `uv` manages Python itself, the virtual environment, the dependencies and
  the lock file. `uv.lock` is committed.
- Commands run through `uv run` (for example `uv run python manage.py check`).
  `pip` is not used directly in the project.

## Consequences

- One tool instead of several; installs are fast and repeatable.
- The lock file gives the same versions on every machine.
- Moving to Python 3.15 is its own small step, once Django supports it.
- uv is a new tool for the team to learn.

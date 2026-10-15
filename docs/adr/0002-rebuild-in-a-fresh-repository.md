# 0002: Rebuild in a fresh repository; v1 frozen as the specification

**Status:** Accepted (2026-10-08)

## Context

- v1 (Django 5.2, PostgreSQL) grew feature by feature from January to
  October 2026.
- It is well tested and rich in business rules and edge cases.
- Structurally it assumes a single workshop, repeats some rules across
  screens, writes CSS and JS inside templates, and keeps its documentation in
  one very large file.
- It never went live, so there is no production data to migrate.

## Decision

- Build the new system in a new repository.
- Freeze v1 at git tag `titan-final`. Use its rules, tests and docs as the
  specification for business behaviour and edge cases.
- Re-implement the rules; do not copy its code or structure.
- Keep v1 deployable as a fallback until the new system is live.

## Consequences

- Edge cases could be lost in the rebuild. Each section's rules are therefore
  catalogued from v1 before it is built, and every rule gets a test.
- Some work may be done twice, for example GST, if it is needed before the
  new system is ready.
- The first months bring the client no new features.

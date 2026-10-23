# 0019: PostgreSQL 18 on every machine; no Docker on the laptop

**Status:** Accepted (2026-10-23)

It replaces ADR-0012, and the PostgreSQL version that ADR-0014 names for CI.

## Context

- ADR-0012 chose PostgreSQL 17 because it was already on the laptop. It
  said production uses the host's PostgreSQL, "version 17 or the closest
  available", and that every machine runs the same version.
- Facts read from postgresql.org and the Django docs on 2026-10-23:
  - PostgreSQL 18 came out on 25 September 2025. Its latest release is
    18.6 (13 August 2026). Its support ends on 14 November 2030; support
    for 17 ends on 8 November 2029.
  - PostgreSQL 19 is still a release candidate (RC 1, 15 October 2026).
  - Django 6.1 supports PostgreSQL 15 and newer.
- Both hosting options for go-live can run 18 (the choice is made in
  Phase 7). Railway gives new databases 18, as other projects reported in
  October 2026; Railway's own docs do not name a version. On a VPS we
  install the version we choose.
- There is no real data yet. The laptop and CI hold only test data, so
  changing the version now moves nothing. Changing it later on the live
  server, with real bills on it, needs a planned upgrade.

## Decision

- **PostgreSQL 18 on every machine:** the laptop, CI and production.
- The laptop runs PostgreSQL 18 as a Windows service, with its own database
  and user for this project (`workshopos`). The user may create databases,
  so the test runner can create its test database.
- No Docker on the laptop, for the memory reason in ADR-0012.
- Connection settings come from environment variables, read from a local
  `.env` file that is never committed. `.env.example` lists every variable.
- CI uses a `postgres:18` service container.
- The database driver stays psycopg 3 (`psycopg[binary]`).
- The backup and restore tools (`pg_dump`, `pg_restore`) have the same
  major version as the server. An older `pg_dump` refuses a newer server.
- A test checks that the database is 18 or newer (`tests/test_settings.py`).

## Consequences

- The tests run on the version the client will run.
- No major upgrade is needed before 2030. The next one (19 or later) waits
  until that version has had its first bug-fix releases, and is tried on
  staging first.
- Django 6.1 can use two features that need 18: the `UUID7` database
  function, and virtual `GeneratedField` columns (`db_persist=False`).
  Whether we use them is decided in Phase 4. Other gains need no code:
  better use of indexes with several columns, faster reads from disk, and
  data checksums on by default when a new database server is set up.
- Another developer installs PostgreSQL 18 their own way (or runs it in
  Docker); the settings only read environment variables.
- The PostgreSQL version must be kept the same on every machine and checked
  at each major upgrade.

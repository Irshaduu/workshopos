# 0012: Local PostgreSQL 17, without Docker

**Status:** Superseded by 0019 (2026-10-23)

## Context

- The plan suggested Docker Compose for the local database.
- The development laptop has 7.7 GB of memory. Docker Desktop on Windows runs
  a separate Linux virtual machine, which uses a large part of that.
- PostgreSQL 17 is already installed on the laptop and runs as a Windows
  service.

## Decision

- Local development uses the installed PostgreSQL 17, with its own database
  and user for this project (`workshopos`). The user may create databases,
  so the test runner can create its test database.
- Connection settings come from environment variables, read from a local
  `.env` file that is never committed. `.env.example` lists every variable.
- CI uses a PostgreSQL 17 service container. Production uses the hosting's
  PostgreSQL, version 17 or the closest available.
- The database driver is psycopg 3 (`psycopg[binary]`).

## Consequences

- No Docker to install or run on the laptop; more memory left for tests.
- Another developer installs PostgreSQL 17 their own way (or runs it in
  Docker); the settings only read environment variables.
- The PostgreSQL version must be kept the same on every machine and checked
  at each major upgrade.

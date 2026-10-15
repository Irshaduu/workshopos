# 0003: One codebase, tenant-ready; dedicated or shared deployments

**Status:** Accepted (2026-10-08)

## Context

- The first client wants an isolated system on its own hosting.
- Other workshops may use the system later.
- Two codebases would mean every feature and every fix built twice.

## Decision

- **One codebase.** Every business record belongs to a `Workshop`.
- The same code runs as a **dedicated** deployment (one workshop, on the
  client's own hosting) or a **shared** one (many workshops).
- **No forks, and no "dedicated mode" branches in the code.** A dedicated
  deployment is simply one with a single workshop.
- What differs between deployments is configuration (environment variables) or
  per-workshop settings, never code.
- **One version everywhere.** Every release goes to staging, then to every
  production server.

## Consequences

- Every query must be scoped to a workshop; leak tests prove it.
- The deploy pipeline must reach every server.
- A dedicated server becomes a product option for other workshops.

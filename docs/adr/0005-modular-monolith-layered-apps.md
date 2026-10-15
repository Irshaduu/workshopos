# 0005 — Modular monolith: layered apps, services and selectors

**Status:** Proposed · **Date:** 2026-10-08

## Context

v1 was two large apps that imported each other. Business rules lived in
views, models, signals and template scripts, so the answer to "where does this
rule live?" was often "in several places".

## Decision (proposed)

- One deployable Django project, split into small apps, each with one job.
- Apps are layered. An app imports only from apps in lower layers; CI checks
  this.
- Inside an app: `services.py` changes data, `selectors.py` reads it, views
  stay thin, and signals carry no business logic.
- Details: `docs/ARCHITECTURE.md`.

## Consequences

- "Where does this rule live?" has one answer.
- More files than v1, and some links between apps need care — see the open
  decisions in `docs/ARCHITECTURE.md`.
- No microservices: at this size they would add deployment and network cost
  with no benefit.

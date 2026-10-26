# 0005: Modular monolith: layered apps, services and selectors

**Status:** Accepted (2026-10-26)

Proposed on 2026-10-08 and checked again before the first app, against
v1's code and the decisions made since.

## Context

v1 was two large apps that imported each other. Business rules lived in
views, models, signals and template scripts, so the answer to "where does this
rule live?" was often "in several places".

## Decision

- One deployable Django project, split into small apps, each with one job.
- An app is created when its first model or page is built. No empty apps.
- Apps are layered. An app imports only from apps in lower layers, and its
  models link only to its own models or to lower layers.
- CI checks both. import-linter reads the imports. A test walks every model
  link, because a link written as text (`"billing.FleetAccount"`) needs no
  import and would slip past import-linter.
- Inside an app: `services.py` changes data, `selectors.py` reads it, views
  stay thin, and signals carry no business logic.
- Details: `docs/ARCHITECTURE.md`.

## Consequences

- "Where does this rule live?" has one answer.
- A lower app never reads an upper one. When it needs data that an upper app
  creates, the upper app's service passes it down.
- More files than v1, and some links between apps need care. The check
  before acceptance found three planned links that pointed up a layer:
  photos to their subjects (fixed: `photos` moved above `jobs`), and the job
  card to its fleet account and stock costing to purchases (open decisions
  in `docs/ARCHITECTURE.md`, decided when their sections are built).
- No microservices: at this size they would add deployment and network cost
  with no benefit.

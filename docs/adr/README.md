# Architecture Decision Records

One short file per significant decision: what was decided, why, and what it
costs.

| # | Decision | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-rebuild-in-a-fresh-repository.md) | Rebuild in a fresh repository; v1 frozen as the specification | Accepted |
| [0003](0003-one-codebase-tenant-ready.md) | One codebase, tenant-ready; dedicated or shared deployments | Accepted |
| [0004](0004-saas-features-wait-for-a-second-workshop.md) | SaaS business features wait for a second workshop | Accepted |
| [0005](0005-modular-monolith-layered-apps.md) | Modular monolith: layered apps, services and selectors | Proposed |
| [0006](0006-branches-and-shared-vehicles.md) | Branches inside a workshop; customers and vehicles shared by its branches | Accepted |
| [0007](0007-workshop-members-and-platform-staff.md) | Two kinds of account: workshop members and platform staff | Accepted |

## Rules

- Write one when a choice is hard to undo, or someone would ask "why?".
- Numbered in order, never reused. File name: `NNNN-short-title.md`.
- Status: `Proposed` → `Accepted`. Later: `Superseded by NNNN`.
- An accepted ADR is never rewritten. Only its status line changes; a new ADR
  carries the new decision.
- Add every new ADR to the table above.

## Template

```markdown
# NNNN — Title

**Status:** Proposed · **Date:** YYYY-MM-DD

## Context
What forces the decision. Facts, not opinions.

## Decision
What we will do. Short and concrete.

## Consequences
What gets easier, what gets harder, what it costs.
```

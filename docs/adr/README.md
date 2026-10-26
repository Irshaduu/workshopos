# Architecture Decision Records

One short file per significant decision: what was decided, why, and what it
costs.

| # | Decision | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-rebuild-in-a-fresh-repository.md) | Rebuild in a fresh repository; v1 frozen as the specification | Accepted |
| [0003](0003-one-codebase-tenant-ready.md) | One codebase, tenant-ready; dedicated or shared deployments | Accepted |
| [0004](0004-saas-features-wait-for-a-second-workshop.md) | SaaS business features wait for a second workshop | Accepted |
| [0005](0005-modular-monolith-layered-apps.md) | Modular monolith: layered apps, services and selectors | Accepted |
| [0006](0006-branches-and-shared-vehicles.md) | Branches inside a workshop; customers and vehicles shared by its branches | Accepted |
| [0007](0007-workshop-members-and-platform-staff.md) | Two kinds of account: workshop members and platform staff | Accepted |
| [0008](0008-ai-assistant-tools-over-tested-functions.md) | AI assistant: tools over tested read-only functions | Proposed |
| [0009](0009-django-6-1-then-6-2-lts.md) | Django 6.1 now, then 6.2 LTS | Accepted |
| [0010](0010-python-3-14-and-uv.md) | Python 3.14, managed with uv | Accepted |
| [0011](0011-module-switches-per-workshop.md) | Module switches per workshop | Accepted |
| [0012](0012-local-postgresql-without-docker.md) | Local PostgreSQL 17, without Docker | Superseded by 0019 |
| [0013](0013-code-checks-and-tests.md) | Code checks and tests: ruff, pre-commit, pytest-django | Accepted |
| [0014](0014-ci-on-github-actions.md) | CI on GitHub Actions | Accepted |
| [0015](0015-translatable-text-from-day-one.md) | Translatable text from day one; Malayalam later | Accepted |
| [0016](0016-htmx-for-server-calls.md) | htmx 4 for server calls; small JavaScript modules for the rest | Accepted |
| [0017](0017-plain-css-with-our-own-tokens.md) | Plain CSS with our own tokens; no CSS framework, no build step | Accepted |
| [0018](0018-lucide-icons-kept-in-the-repo.md) | Icons: Lucide, only the icons we use, kept in the repo | Accepted |
| [0019](0019-postgresql-18-on-every-machine.md) | PostgreSQL 18 on every machine; no Docker on the laptop | Accepted |
| [0020](0020-javascript-unit-tests-with-node.md) | JavaScript unit tests with Node's own test runner | Accepted |

## Rules

- Write one when a choice is hard to undo, or someone would ask "why?".
- Numbered in order, never reused. File name: `NNNN-short-title.md`.
- Status: `Proposed`, then `Accepted`. Later: `Superseded by NNNN`.
- An accepted ADR is never rewritten. Only its status line changes; a new ADR
  carries the new decision.
- Add every new ADR to the table above.

## Template

```markdown
# NNNN: Title

**Status:** Proposed (YYYY-MM-DD)

## Context
What forces the decision. Facts, not opinions.

## Decision
What we will do. Short and concrete.

## Consequences
What gets easier, what gets harder, what it costs.
```

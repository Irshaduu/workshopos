# 0007 — Two kinds of account: workshop members and platform staff

**Status:** Accepted · **Date:** 2026-10-15

## Context

- In v1, `is_superuser` meant "owner". The company running the system and the
  workshop using it were the same thing.
- A system serving many workshops has two groups of people: the company that
  runs it, and the people of each workshop. Mixed together, a support person
  could read a workshop's customers, or a workshop user could reach the
  platform.
- Customers' names and phone numbers are personal data under India's DPDP Act.

## Decision

- **Workshop members.** A person joins a workshop through a **membership**:
  user + workshop + role, optionally limited to some branches (ADR-0006). One
  user may hold memberships in more than one workshop.
- **Workshop roles:**
  - **Owner** — everything in the workshop, all branches, all money.
  - **Office** — daily work and money for its branches.
  - **Floor** — its own jobs; never prices or customer details.
  - A read-only **Accountant** role may be added later.
- **Platform staff** — people of the company that runs the system — are kept
  apart from memberships. Their roles (office, support, sales) are built with
  the SaaS features (ADR-0004).
- **The Django superuser is for emergencies only:** two-factor sign-in, never
  used for daily work, never a workshop owner.
- **Platform staff see no workshop's business data by default.** Support
  access, when built, is logged and time-limited.
- **Permissions are checked in one place.** A test covers every page × every
  role.

## Consequences

- "Who can do this?" has one answer, in one place.
- The permission test grows with every page.
- Only the separation is built now; platform roles cost nothing until the
  SaaS features arrive.

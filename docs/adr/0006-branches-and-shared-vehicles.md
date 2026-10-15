# 0006: Branches inside a workshop; customers and vehicles shared by its branches

**Status:** Accepted (2026-10-15)

## Context

- Some workshops run two or three branches, and one car can visit more than
  one of them.
- v1 assumed one workshop in one place, and kept the customer and the car as
  text typed on each job card. A car's history was a search, not a record.
- Adding a branch link, or real customer and vehicle records, after go-live
  would mean changing every table and the data already in it.

## Decision

- **`Workshop` is the business:** one owner group, one subscription, one set
  of customers and vehicles. It stays the tenant (ADR-0003).
- **`Branch` is a location inside a workshop.** Every workshop has at least one.
- **Customers and vehicles are real records that belong to the workshop.**
  Every branch sees the same vehicle profile and the full service history;
  each job shows which branch did it.
- **Operational records belong to a branch:** job cards, invoices, stock,
  cash and staff.
- **Bill numbers run per branch,** with a branch prefix. The format is
  confirmed with the workshop's accountant before GST invoicing.
- **Two different workshops never share data**, not even a car's history.
- A workshop with one branch never sees branch screens. Branch screens
  (switching, stock transfers, combined reports) are built when a workshop
  with more than one branch joins.

## Consequences

- Operational records carry two links: workshop and branch. Queries are scoped
  by both; leak tests cover both.
- Vehicle profiles and service history work across branches without copying.
- A car sold to a new owner, or taken to another workshop, starts a separate
  record there. Each workshop keeps its own history.

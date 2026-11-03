# 0028: Several places: one workshop by default

**Status:** Accepted (2026-11-04)

## Context

- ADR-0006: a workshop is one owner group with one set of customers and
  vehicles; a branch is a place inside it; two workshops never share data;
  every branch sees the full service history.
- A workshop may open another place. Who owns it is known only on the day:
  the same owners, a partner or a funder for that place, or a different
  firm.
- Our expectation, not measured: most workshops with several places have
  the same owners, and a place with its own partners is rare.
- A car's history across places is a large part of the system's value. v1's
  service history sheet follows a part across visits, with the distance it
  lasted, so a history with visits missing can mislead.
- Whether a firm's customers and money must be kept apart is a question for
  the accountant, not for the code.
- The test for each idea: would adding it later change real records? Only
  the branch link fails that test, so only that is needed now.

## Decision

**One workshop by default.** The first question on the day: who owns the
new place, and must its customers and money be walled off, by law or by
choice? The accountant confirms the law.

| If they say | We do | Built |
|---|---|---|
| The same owners, another place (common) | One workshop, one more branch, and the history switch | With Branch screens, when the second place is real |
| A partner or a funder for one place (rare) | The same workshop, and a Branch Owner login limited to that branch, read-only for a funder. A new firm there needs its legal name and GSTIN on the branch | When a workshop asks |
| The partners leave, or a branch becomes its own firm | A one-time copy of its records out | When it happens |
| A wall is truly needed (very rare) | A second workshop, with no shared history. The founders get one login, with a switch that never changes the address | With Several workshops per account |
| Share history between two workshops | Not now, only if the market asks | |

**The history switch:** one per branch, "Share this branch's history with
other branches".

- It is off until an owner presses on, and only owners see it. A Branch
  Owner does not.
- It only filters what screens show, so it never changes a record.
- Shared visits show the work only, never the money.
- The screen and the sheet say when visits are hidden. Owners see every
  visit, and kilometre checks use every visit.
- One switch per branch, not per pair of branches: five branches would need
  twenty.
- Each change goes in the change history.
- It is a setting with one row per branch, a case ADR-0024's one row per
  workshop does not cover. Everything else in ADR-0024 applies.

**It hides history, not customers.** A full plate still finds any car of
the workshop, with its make and its owner's name and phone. Lists show only
your own branch's cars, except for owners.

**Smaller rules, for the build:**

- The Customer history page shows a car's owner every visit.
- A warranty claim stays with the branch that fitted the part.
- One open job card per plate stays workshop-wide.
- A Branch Owner's alerts cover only that branch.
- The switch, settings, master lists and the workshop profile stay with
  owners.

**Now:** pages are branch-ready from the base for the first pages (step 3
of the build order). A query on a record with a branch asks for the branch
too (`for_branch()`; ADR-0006 already says queries are scoped by both). A
rule in `CONTRIBUTING.md` and a test: every new model has a branch link, or
sits on a short workshop-wide list with the reason. Nothing else is built.

## Consequences

- A second place needs no change to real records, because each record
  already knows its branch.
- Every query on a branch record takes a branch, and the leak tests cover
  it.
- A history with visits missing can mislead, so the label on the screen and
  the sheet is part of the switch.
- The one hard path: a branch that becomes its own firm needs a one-time
  copy out. So the question comes first.
- Branch screens move from SaaS to After (`docs/MODULES.md`).
- ADR-0006's full service history line is replaced by the switch. Its
  status line says so.

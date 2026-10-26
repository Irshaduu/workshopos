# 0024: Per-workshop settings: each beside the rule that uses it

**Status:** Accepted (2026-10-26)

## Context

- A workshop changes a few business values: the discount that alerts the
  owners, the suggested markup on a part, how long Office may change a
  money entry, and how far back Office may date money.
- v1 keeps each one as a constant in its code, and its owners chose no
  settings screen:
  - `JobCard.HIGH_DISCOUNT_AMOUNT`: ₹3,500 (30% until the owner changed it);
  - `pricing.py`: a 40% markup, and a warning below 20%;
  - `delete_window.py`: Office may change money for 24 hours;
  - `money_dates.py`: Office may date money 3 days back.
- v2 runs the same code on every server (ADR-0003). On a shared server two
  workshops need two values, so a value in the code cannot be one
  workshop's own.
- Four ways were compared:
  - **one settings table in `workshops`:** everything in one place, but
    `workshops` sits low and would have to know every upper app's words
    (discount, markup), and every new feature would change it;
  - **each app keeps its own:** the setting sits beside its rule, but there
    are several small tables;
  - **one list of names and values:** a new setting needs no migration, but
    PostgreSQL cannot check a value's type or range (ADR-0019), and every
    value has to be read and converted;
  - **values in the code, as in v1:** the simplest, but one value for every
    workshop on a server.

## Decision

- **A setting lives beside the rule that uses it**, in that app's settings
  model: one row per workshop (it builds on `WorkshopModel`), a typed
  column for each setting, and PostgreSQL checks on its values. A rule used
  by several apps has one home (`CONTRIBUTING.md`), and its setting lives
  there too.
- **Built with the feature that uses it.** No settings model exists before
  its first setting.
- **A workshop with no saved row uses the defaults written in the code**,
  starting from v1's values. Reading a setting never writes.
- **A setting acts at the moment of an action, never on saved records.** A
  new discount limit changes the next alerts, not old bills.
- A value that old records must keep is stored with its start date, in its
  own feature: for example the GST type (Phase 9).
- **The bill-number series is not a setting.** It is a counter for each
  branch, in `billing`, built with the first bill.
- Only the Owner changes a setting, and each change goes into the audit
  log. A settings screen is built only when the owners want one; until
  then the developer changes a value for them.
- What differs between servers stays in environment variables. What
  differs between workshops on one server is a setting.

## Consequences

- A setting is found in the `models.py` of the app whose rule uses it.
- A settings menu, when one is built, links to each app's own page.
- A settings model builds on `WorkshopModel`, so it needs a factory and the
  leak test covers it.
- A changed default reaches every workshop that never chose its own value.
  So a default changes only on purpose, and its pull request says so.

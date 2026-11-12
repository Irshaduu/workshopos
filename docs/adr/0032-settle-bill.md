# 0032: Settle bill: the bill's shape, and who may date or change money

**Status:** Proposed (2026-11-10)

## Context

- `docs/PLAN.md` (Phase 5): settling is one step. Office or an owner types what the customer
  paid, by method, and the rest of the bill is the discount, shown before saving. The
  discount is its own amount, before tax, and the bill shows it, with Net, never Paid. The
  bill gets its number when it is final (ADR-0030), and keeps a frozen copy of the customer
  and the car as printed.
- v1 kept the money on the job card: one received amount, one method, a discount, and a
  stored total kept equal to its rows by hand. It printed Paid with the amount received, and
  hid the discount. Its settle took the moment of the tap as the payment's day.
- v1's owners decided on 2026-09-22 that Office may date money at most 3 days back, and may
  change money for 24 hours after it was recorded; after that only an owner may, and never
  silently. v1 read back-dated money from each record's own two dates, and kept every change
  with what it was, in a table with no link to the record.
- A script works out no money (`CONTRIBUTING.md`, ADR-0016).
- `jobs` sits below `billing` (ADR-0005), so a job card can never read its bill.
- The client values its own bill design: it was made from their Excel bill, and it won them in
  the v1 demo. Other workshops will join later (ADR-0004).

## Decision

- **A bill is a record of its own, made when the job card is settled.** A job card that is
  still open has a preview, worked out from its rows, and no record. One bill for each card
  for now; Cancel bill (Phase 6) will let a card be billed again under a new number.
- **The total is never stored.** It is worked out from the card's rows each time it is read.
  What settling decided is stored, because nothing may change it by itself: the number, the
  date, the discount, and the frozen copy of the customer's name, the brand and the model.
- **Each method typed is its own payment row**, above zero, one per method. A walk-in's
  payments share the bill's date, which is the date paid; fleet payments (Phase 6) will have
  their own.
- **The server shows the discount before saving.** A settle with a discount answers with a
  check: the total, each payment, the discount and the net. Its Settle bill button carries the
  total it showed, and a total that moved since then is refused.
- **Settling ends the job card:** it becomes Settled, with a step, and its car is free at once.
- **Numbers come from a counter row per branch and financial year,** locked after the card's
  own lock, in the same transaction. A number is unique in the workshop, so a second place
  needs letters of its own before it bills.
- **A bill's branch is its card's, by PostgreSQL** (`SameBranch`, built like `SameWorkshop`).
- **The back-date limit and the edit window live in `audit`,** each workshop's own setting
  (ADR-0024), because every money record will use them, not only bills. Back-dated money is
  read from its record's two dates, as in v1, so nothing extra is stored for it: a bill keeps
  its date, and the moment it was settled with who settled it.
- **The change history is one table, built with the first service that changes money** (Change
  payments): each change keeps what it was and what it became, who, when and why, with no link
  to the record. A first settle is not a change.
- **One bill design for now: the client's, used only for the client.** One function builds a
  bill's figures, and a design only shows them, so a second design is a second template, not
  a second copy of the rules. A workshop's look comes from its profile (Phase 6). When a
  second workshop pays, it gets a standard design with its own logo, details and colour; a
  few ready designs follow only if workshops ask; never a one-off design for one workshop.

## Consequences

- A bill's figures always agree with its job card: there is no stored total to drift.
- Every change to a settled bill must recompute its discount and keep a Change. Change job
  card, v1's Unlock, comes with Parts on the job card (Phase 6), because it must then also
  move stock and shop money.
- A settle with a discount takes one more tap than v1, and the dialogs need the page's script,
  like the cancel card.
- A workshop with a second place cannot settle there until Branch screens give it letters.
- The client's design sits in a public repository, like all code. What is promised is use,
  not secrecy: no other workshop's bills use it.

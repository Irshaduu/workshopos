# Rules: settle bill

The rules of the Settle bill module (`docs/MODULES.md`), taken from v1 and checked in v1's
code (`invoice_view` and `update_bill_status` in `workshop/views/billing.py`,
`workshop/settlement.py`, `settlement()` and `build_invoice()` in `workshop/invoice.py`, the
Financial Lock and `_reconcile_settled_bill` in `workshop/views/jobcard.py`,
`invoice_template.html` and `_invoice_sheet.html`, and their tests in
`test_settlement_preflight.py`, `test_money_change_rules.py`, `test_edit_history.py` and
`test_money_guards.py`). It builds the job card's Settled state (JOB-3), its frozen copy
(JOB-12), the warning for an empty mileage (JOB-22), and the rules that a settled card is
never cancelled (JOB-52) and never moves (KNOWN-17). Who may change money and when, and
what a change keeps: `docs/rules/change-history.md`. Why a bill has its own number:
ADR-0030. Money: ADR-0029. Words: `docs/GLOSSARY.md`. The code: `apps/billing/`, with the
Settled state in `apps/jobs/`.

- Each rule has an ID. A test names the ID of the rule it protects.
- An ID never changes. A new rule takes the next free number.
- Each rule says where it comes from: **v1** (kept as it was), **v1, changed** (and what
  changed), or **new** (v2 only).
- Every rule is built with this module, unless it says when.

A customer pays the whole agreed amount at once and takes the car, and most cars get a
discount: the bill says 43,000, the customer asks what to pay, and the workshop names
40,000. Settling records that in one step: what was paid, and how. The rest of the bill is
the discount, and the bill is final.

## The bill

- **SETTLE-1** A bill is what a customer pays for one job card: the jobs done, with the one
  labour charge (JOB-31), and the total. Once settled, it also has its number, its date,
  the discount, the net and the payments. Parts join it with Parts on the job card
  (Phase 6). *v1: `build_invoice`.*
- **SETTLE-2** While the job card is open, its bill is a preview: it says Preview, it has
  no number, and it changes with the card. It becomes final when it is settled. *New
  (ADR-0030).*
- **SETTLE-3** The total is worked out from the bill's rows each time it is read: the
  labour charge today, and the parts later. It is never typed, and never stored beside the
  rows. *v1, changed: v1 stored the total beside its rows and kept the two equal by hand.*
- **SETTLE-4** A cancelled job card has no bill, so its page has no Bill button. *New
  (JOB-49).*

## The bill page

- **SETTLE-5** A job card's page has a Bill button for the roles that see bills
  (SETTLE-47). It opens the bill page. *v1: the Invoice button.*
- **SETTLE-6** The bill page is v1's: a bar with the back control, the bill's state
  (Preview or Settled), a link to the job card and Settle bill; under it, the bill as it
  prints: its title, date and number; the customer's name; the car's brand, model and
  plate, and the mileage; Job Performed with the labour charge as its one subtotal; and the
  total. *v1: `invoice_template.html`, through the lab.* The letterhead, Print, the file's
  name and WhatsApp come with Printed bill (Phase 6).
- **SETTLE-7** A settled bill also shows the discount, labelled Discount, and the net,
  labelled Net. Its amount is never labelled Paid. A bill settled with no discount shows
  no discount line. Under them, the bill shows how it was paid, method by method. *v1,
  changed (`docs/PLAN.md`): v1 hid the discount and printed Paid with the amount received,
  so the bill would not invite more bargaining. The client wants every discount shown,
  with its label.*
- **SETTLE-8** Every amount on the bill shows its paise, like 17,800.00, because a
  customer adds up the column by eye (`docs/DESIGN.md`). *v1: `inr_exact`.*
- **SETTLE-9** The bill is titled Bill. Tax invoice is the title only for a workshop with
  a valid GSTIN (Phase 9). *v1, changed: v1's bill said Invoice.*

## Before you settle

- **SETTLE-10** Settle bill first lists what is still not filled on the job card, because
  settling locks it (SETTLE-36): an empty mileage (JOB-22), no lead mechanic, jobs listed
  with a labour charge of 0, and each concern not marked Fixed. A card with nothing to
  list goes straight to the settle box. *v1: `settlement.py`. What parts leave not filled
  comes with parts (Phase 6).*
- **SETTLE-11** Each thing not filled is one short phrase, like "no mileage", and a concern
  is named by its own words, like "AC not cooling: not fixed". The head says how many things
  are not filled. *v1: `MISSING`, `NOT_FIXED`, `count`.*
- **SETTLE-12** The list never stops a settle. It has two ways on: Open job card, to fill
  them in, and Continue. *v1: "Nothing here blocks", because a customer at the counter
  does not wait for a mechanic to tick a box.*
- **SETTLE-13** The list comes from one function, which the live report's Unfilled bills
  reads too (Phase 6), so the two never disagree. *v1: "one module, two readers".*

## Settling

- **SETTLE-14** Office or an owner settles a bill in one step: they type what the customer
  paid, by method, and the rest of the bill is the discount. *v1: `update_bill_status`.*
- **SETTLE-15** The settle box has one money box for each payment method: Cash, UPI, Card
  and Bank transfer, each named in words, all empty at first. A bill can be paid two ways,
  or more. Each method with an amount is saved as its own payment. *v1, changed: v1 kept
  one amount and one method for each bill, so part cash and part UPI was saved as one
  method.*
- **SETTLE-16** A payment is above zero, because it is money that moved (ADR-0029). An
  empty box is no payment, and a bill needs at least one. A job card that ends with no
  money is cancelled with its reason (JOB-49). *v1, changed: v1 read a 0 as "not paid" and
  put the card back to unpaid.*
- **SETTLE-17** The payments together are never more than the total. More is refused,
  naming the total. *v1, changed (`docs/PLAN.md`): v1 kept it and called it an
  overpayment.*
- **SETTLE-18** A bill whose total is 0 is never settled. The page says so: add the labour
  charge, or cancel the job card with its reason. *New.*
- **SETTLE-19** The discount is the total less the payments. It is saved on the bill as
  its own amount, before tax, and it may be 0. *v1: `discount_amount`.*
- **SETTLE-20** The discount is shown before it is saved. A settle with a discount answers
  first with a check: the total, each payment, the discount and the net, with two buttons,
  Go back and Settle bill. A settle with no discount saves at once. The server works this
  out, never a script. *v1, changed: v1's script worked out the discount while the amount
  was typed, and asked again only for a discount above 3,500. Here a script never works out
  money (`CONTRIBUTING.md`).*
- **SETTLE-21** The settle box has the date paid, starting at today, India time. The money
  date rules hold (CHANGE-13 to CHANGE-16): never in the future, and Office no further back
  than the back-date limit. It is also never before the job card's admitted date. *v1,
  changed: v1 took the moment of the tap, so a payment from Saturday typed on Monday was
  filed under Monday.*
- **SETTLE-22** The bill is dated the date paid. It also keeps the moment it was settled,
  and who settled it, so a back-dated bill keeps both its days and the edit window counts
  from the bill itself (CHANGE-10, CHANGE-17). *v1, changed: v1's bill printed the day the
  car came in.*
- **SETTLE-23** Settling ends the job card: it becomes Settled, it leaves the live board,
  and its car is free at once for a new job card (JOB-4). A Settled step is kept, with its
  time, who settled it and the lead mechanic at that moment (JOB-39, JOB-40). *v1,
  changed: v1 kept "paid" apart from "completed", and offered Complete and settle when they
  disagreed.*
- **SETTLE-24** After settling, the bill page shows the settled bill, with a notice and
  its sound. *v1: "Billing updated".*

## Saving once

- **SETTLE-25** A double tap or a slow network never settles a bill twice. The settle
  form's address holds the new bill's key, so a repeat shows the bill settled the first
  time, with the same notice. A settle sent from another page after the bill was settled
  is refused, saying who settled it and when. *New (`docs/PLAN.md`).*
- **SETTLE-26** The settle box sends the total it showed, and so does the check. If the job
  card changed the total since then, the settle is refused and the box shows the new total,
  so a discount is never worked out on a total nobody saw. A send that says no total is
  refused the same way. *New.*
- **SETTLE-27** A job card's save sent after the card was settled, like from a tablet left
  open, is refused, and nothing is saved. *New, like JOB-51.*

## The number

- **SETTLE-28** A bill gets its number when it is settled, never before: the letters INV,
  its financial year, and a count of at least four digits, like INV-26-27-0045. A financial
  year runs from 1 April to 31 March. *New (ADR-0030).*
- **SETTLE-29** The count runs per branch and starts again at 0001 each financial year,
  from a counter row locked in the same transaction as the settle. Two bills settled at
  one moment never take one number, and a settle that fails uses no number. It is never a
  PostgreSQL sequence, which skips a number when a save fails. *New (ADR-0030), like
  JOB-6.*
- **SETTLE-30** The financial year is the one the bill's date falls in, so a bill dated 31
  March and typed on 1 April takes the next number of the year that ended. *New.*
- **SETTLE-31** A number is unique in its workshop, by PostgreSQL, at most 16 characters,
  as GST allows, and it never changes. *New (ADR-0030).*
- **SETTLE-32** A branch's own letters come with Branch screens, before a second place
  settles its first bill. Until then a number that repeats another bill's number in the
  workshop is refused. That alone is not enough: a second place that settled first in a
  new year would take that year's first number, and the first place's next bill would then
  be refused. So no second place settles before it has its own letters. *New, like JOB-9.*
- **SETTLE-33** The accountant confirms the letters and the format before GST starts. The
  accountant also says whether a back-dated bill may keep the next number: numbers follow
  the order bills are settled, so a bill dated Saturday and settled on Monday comes after
  Monday's earlier bills, and an owner's bill dated in a year that ended takes that year's
  next number. *New (ADR-0030).*

## The frozen copy

- **SETTLE-34** A settled bill keeps its own copy of what it prints about the customer and
  the car: the customer's name, and the car's brand and model. A later change to those
  records, like a name fixed on another card, the car's next visit, a renamed brand
  (Master lists, Phase 6) or a customer's request to delete their data, never changes a
  settled bill. The plate and the mileage are already the visit's own (JOB-13, JOB-22).
  *New (`docs/PLAN.md`).*
- **SETTLE-35** A preview reads the records as they are now. A settled bill reads only its
  copy. *New.*

## The settled job card

- **SETTLE-36** A settled job card is locked: every box is locked and looks it, and a send
  is refused (SETTLE-27). Its page says Settled, with who settled it and when, and its Bill
  button. The bill's number and date are on the bill page, because a job card never reads
  its bill (`docs/ARCHITECTURE.md`, layers). *v1: the Financial Lock.*
- **SETTLE-37** A settled job card is never cancelled (JOB-52) and never moves to another
  car (KNOWN-17). *v1.*

## Changing a settled bill

- **SETTLE-38** A settled bill can be changed in two ways, both from its bill page: its
  payments, with Change payments, or its job card, with Change job card. Office may do it
  within the edit window, which starts when the bill was settled; after that only an owner
  may (CHANGE-9). *v1: settling a paid bill again, the Financial Lock, and `delete_window`.
  Change job card is built with Parts on the job card (Phase 6), because a change to a
  settled card must then also move stock and shop money.*
- **SETTLE-39** Change payments opens the settle box with the payments and the date paid
  as saved, and the same rules hold (SETTLE-15 to SETTLE-21). The discount becomes the
  total less the new payments. *v1: settling a paid bill again.*
- **SETTLE-40** Change job card on a settled card opens its boxes for one save, except the
  plate, because a settled card never moves (KNOWN-17). The payments stay, and the discount
  becomes the new total less the payments. A new total below the payments is refused, so
  the payments are changed first. *v1, changed: v1 kept a bill that fell below what was
  paid, and called the rest an overpayment. Built with Parts on the job card (Phase 6).*
- **SETTLE-41** Every change to a settled bill asks why (CHANGE-5), and is kept in the
  change history with what it was and what it became: the total, the discount, each
  payment, the date paid, and the frozen copy's name, brand and model. A save that moves
  none of these keeps nothing. *v1, changed: v1 kept the money that moved, with no reason.
  The total and the copy move only with Change job card (Phase 6).*
- **SETTLE-42** A change keeps the moment the bill was settled, so the edit window never
  starts again. *v1: `test_a_re_settle_keeps_the_day_the_bill_was_settled`.*
- **SETTLE-43** A change of the job card makes the bill's copy again (SETTLE-34), because
  it fixes this bill. *New. Built with Change job card (Phase 6).*
- **SETTLE-44** A change never moves a bill into another financial year, because its
  number belongs to its year. *New.*
- **SETTLE-45** A change runs in one locked transaction, so two changes at one moment
  never undo each other, and a repeat changes nothing twice. *New (`docs/PLAN.md`).*
- **SETTLE-46** Office past the edit window sees why, in place of the buttons that change
  the bill (ROLE-12, CHANGE-12). *v1: `settle_past_window`, `unlock_past_window`.*

## Who may do what

- **SETTLE-47** Office and owners see bills and settle them (ROLE-19). Floor never sees a
  bill, its Bill button or any money on a settled card (ROLE-16). *v1: `office_required`.*
- **SETTLE-48** Changing a settled bill after the edit window needs an owner's permission.
  No page asks for a role by its name (ROLE-7). *v1: `is_owner` in `delete_window`.*
- **SETTLE-49** The bill page only shows: it answers a GET (ROLE-5). Settling and each
  change are pages of their own that save. *New.*
- **SETTLE-50** A bill of another workshop or another branch is never found (ROLE-10).
  *New (ADR-0023, ADR-0028).*
- **SETTLE-51** A longer bill never means more queries (`tests/test_query_counts.py`).
  *New.*

## Left out for now

- Change job card, v1's Unlock (SETTLE-38, 40, 41 and 43): with Parts on the job card
  (Phase 6).
- Cancelling a bill settled by mistake: it keeps its number, as GST asks, and the job card
  is billed again with a new one. With Pending and paid bills (Phase 6). Until then, an
  owner changes its payments. v1 put such a card back to unpaid with a payment of 0.
- Ready, v1's Completed, and the question when a card is settled before it is Ready: with
  the live board and the Completed list (Phase 6). Until then, settling ends an open card.
- The letterhead, Print, the file's name, the UPI QR and WhatsApp: Printed bill (Phase 6),
  with the workshop's details kept as printed.
- Parts on the bill, and what they leave not filled before settling: Parts on the job card
  (Phase 6).
- The alerts for a large discount, a changed bill and a back-dated payment: with the bell
  (Phase 6), and the discount limit with them.
- Fleet accounts, whose bills are final before they are paid: Phase 6.
- Pending bills, paid bills and the discount audit: Phase 6. Until then, a settled bill is
  reached from its job card, and a settled job card is on no list: the way in comes with
  Change payments, which needs it.
- Other bill designs: a standard design for every new workshop, with its own logo, details
  and colour, and a few ready designs if workshops ask (SaaS, `docs/MODULES.md`). The
  client's design is used only for the client (ADR-0032).
- Warranty cards, which are never settled: After.
- Tax on the bill: GST (Phase 9).

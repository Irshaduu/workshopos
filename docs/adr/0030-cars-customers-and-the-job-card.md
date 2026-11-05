# 0030: Cars and customers as records, and a job card that keeps its visit

**Status:** Accepted (2026-11-05)

## Context

- ADR-0006: customers and cars are real records of the workshop, shared by its
  branches. It does not say what makes one customer one customer, or what lives on the
  car and what lives on the job card.
- v1 kept all of it as text typed on each job card, and fixed the spelling on each save.
  Read in its code: a brand not yet on its list lost its capitals, so BYD became Byd; KL 10
  AA 1000 and KL10AA1000 were two cars; and a car's history was a search.
- `docs/PLAN.md`: a car keeps one record and its whole history; a job card keeps the
  customer and the plate of that visit; a sale changes only the owner.
- Many cards carry no customer at all. One phone can serve a family or a company.
- A Floor tablet can stay open on one card all morning. v1 saved every box on the page,
  so a late save put back whatever the page opened with.
- Measured on Django 6.1 and Python 3.14: a field with `show_hidden_initial` carries the
  value the page opened with, `changed_data` compares what was sent with that value and
  not with the record, and a refused form keeps it. 200,000 `uuid.uuid7()` keys made in a
  row stayed in order.
- GST's Rule 46 asks a tax invoice for a consecutive serial number, at most 16 characters,
  in one or more series, unique for a financial year. A cancelled invoice number stays in
  the series and is reported as cancelled in GSTR-1. We found no such rule for a job card.
  The accountant confirms the details before GST starts.
- v1 gave one number when the job card was made, and that was also the bill's. So a car
  waiting for parts got a lower number than a bill dated before it; a cancelled card left a
  hole in the bills; and a car in on 28 December and billed on 2 January had last year in its
  number.
- Old Excel bills are numbered JB-YY-NNN. In v1 the system shared those numbers, so it needed
  a go-live setting for the last Excel bill, and a rule to skip numbers old bills hold.

## Decision

- **The car holds what is true of the car:** its plate today, its model, chassis code,
  VIN and colour. **The job card holds what is true of the visit:** the plate it came
  with, the mileage, the customer, the note, the labour charge.
- **Brands and models are lists, and a car links to its model.** A typed word finds its
  entry, whatever the capitals, and a new word joins the list by itself. So typing stays
  as fast as v1's, the list decides the spelling, and a rename or a merge (Master lists,
  Phase 6) changes rows of the list, with no job card to rewrite.
- **A customer is a name and a number together.** The same two boxes find the same record.
  Another name with the same number is another record, so one person's visit never
  changes the name on another person's open card. A name-only or number-only customer is
  fine. Nothing merges by itself.
- **The car has no owner column.** A car's customer today is the customer on its newest job
  card that has one, so a sale is only the next card. It can be added later with no change
  to any record, if a page ever needs it stored.
- **A row of a job card has no branch link of its own:** a concern, a job line and a step
  reach their branch through their card. They build on `WorkshopModel` and sit on the short
  list in `tests/test_tenancy.py`. A second branch link would be one fact with two homes.
- **A save changes only what this person changed.** Each box carries the value the page
  opened with, and the service applies only the boxes that differ from it, in one locked
  transaction. So nobody can undo another person's save by accident. When two people change
  one box, the later save wins.
- **A saved row keeps its key in its box's name, and new rows come as a plain list.** So a
  row someone else removed is simply not there to save, and a new row needs no key of its
  own: the same words twice on one card are one row, by PostgreSQL, so a slow network can
  never add lines twice.
- **A job card and its bill have two numbers, and each code means one thing for good** (his
  choice, 2026-11-05, replacing one number per visit):
  - JC, the job card: JC-0027, given when the card is made. It never restarts, and no tax rule
    touches it.
  - INV, the bill: INV-26-27-0045, given when the bill is final, restarting each financial
    year, so it should not need changing when GST comes. Built with Settle bill.
  - JB, old Excel bills only, typed in as printed. A new series never clashes with them, so
    no go-live setting and no skip rule are needed.
- **The job card number comes from a locked counter row per branch,** in the same transaction
  as the card, and never from a PostgreSQL sequence, which skips a number when a save fails.
  The service takes the lock first and asks whether the key is saved after it, so a double tap
  uses no number.

## Consequences

- One car has one record, so a change of plate or owner never splits its history.
- A wrong spelling of a customer's name makes a second record. It is harmless, shows nowhere
  today, and a merge tool can come if a page ever needs one.
- A wrong new word on the brand list stays until Master lists can rename or merge it
  (Phase 6). Nothing is live before then.
- Every box on a job card's page sends a second, hidden value, so the page is a little
  larger. The stand-in speed limit (`docs/PLAN.md`) measures it.
- A card's boxes change the car's record, so a card opened on the wrong car could change the
  wrong record. Known plate (step 7) fills the boxes first and asks before another brand
  replaces the saved one.
- Saving a new card takes one lock per branch, so two saves wait for each other for a moment.
  A workshop's saves are far apart, and the wait is measured by the load test (Phase 7).
- Staff and customers meet two numbers, and a printed bill shows both. On the floor this costs
  little, because staff mostly talk by plate.
- A bill preview has no number until the bill is final.
- The client's bills change from JB to INV at go-live, and the accountant sees one series end
  and another begin, which the rule allows. If the owners insist on JB for bills, the letters
  can change before go-live, and the Excel rules come back.

# 0031: Known plate: which car a plate names, and a save that asks first

**Status:** Accepted (2026-11-08)

## Context

- ADR-0030: a car is one record with its whole history, and a card's boxes change the car's
  record. So a card on the wrong car could change the wrong record, and that ADR left the rest
  to Known plate.
- v1 knew a car only by its plate: its job cards held the car as text, so the plate was the
  car. Read in its code: it never had to decide on a plate that changed, a VIN on two cars, or
  a card on the wrong car.
- A plate can change, like a car from another state registered here, or a temporary plate made
  permanent. A plate can also pass to another car. A VIN is typed by hand, so it can be wrong.
- `docs/MODULES.md` and `docs/ARCHITECTURE.md` placed Known plate in `vehicles`. But it has to
  read job cards, for old plates and the last customer, and `vehicles` sits below `jobs`
  (ADR-0005).
- htmx's morph swap keeps the focused box's own value (its docs). After the plate, the person
  is already in the brand box, so a swap from the server would leave that box empty, and a
  plain swap would replace the box under their finger.
- A browser's Enter presses a form's first submit button. Measured in the browser, on a page
  whose first button was an answer: Enter said "Yes, same car", and a Volvo became a Tata
  Safari.

## Decision

- **Known plate lives in `jobs`.** `vehicles` reads no job card: a car nothing holds is found
  by Django's PROTECT, which refuses to remove a car a job card points to.
- **Old plates come from the job cards themselves,** because each card keeps the plate it came
  with (JOB-13). There is no second list of plates, so the fact has one home.
- **An old plate always asks,** even with the same brand, because it may have passed to another
  car. A plate a car has today asks only when the brand differs.
- **A car can be left with no plate.** When the car in front of you takes a plate, the other
  car keeps its visits, and its VIN finds it again. PostgreSQL still allows one plate per
  workshop, when there is one.
- **A save asks, with a card at the top of the form,** not a card over the page. It works with
  no script, and what was typed stays in view below it. A question is raised inside the card's
  one transaction, which undoes everything, so it uses no number. An answer names the car it is
  about, so if the records changed in between, the save asks again. A refused save forgets the
  answers, so a person is never stuck with one. The form's first submit button is a plain save,
  so Enter never answers.
- **"Same car?" comes only for a car with no record of its own yet,** of the same brand. So two
  cars that both have visits are never joined. There is no merge tool.
- **Nothing is taken from a car with an open job card.** Then both cars are in the workshop, and
  one card is wrong, so that card is fixed first.
- **The server answers what it knows, and a small script writes it only into boxes nobody typed
  in.** Which car, what it holds and who sees the customer stay on the server, and a page with
  no script saves the same card.
- **Every role that changes job cards may move one.** The plan said Office. Floor makes most
  cards and most typing slips, and it already answers the same questions when it makes a card.
- **A move takes nothing from boxes that showed another car.** A new car takes only what was
  typed. A car a move leaves with no other visit gives what it holds to the other car's empty
  boxes, never over what it holds. A car a move leaves with no job card is removed, because it
  was made by mistake and would fill a new card wrongly later.
- **An error answer stays out of a page by one setting in the base page,** htmx's `noSwap`, so
  no call has to remember it. A refused form's answer is still swapped.

## Consequences

- A car with no plate and no VIN is found by nobody. Its history stays, and its next visit
  starts a new car.
- Two records of one car stay two when both have visits, until a merge tool shows it is needed
  in the staging trial.
- A move leaves no step on the card, so on the shared tablet nobody can tell later who moved
  it. It can be added later as one more kind of step.
- More script on the page. Its plain functions are tested with Node. The rest is clicked through
  by hand until the browser tests (step 10 of Slice 1).
- A question costs a person a second tap, each time the records disagree. The staging trial
  shows whether the words are clear enough on the floor.
- htmx comes to the new job card page, and it is what the stand-in speed limit (`docs/PLAN.md`)
  has to measure there.

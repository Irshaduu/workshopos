# Rules: known plate

The rules of the Known plate module (`docs/MODULES.md`), taken from v1 and checked in
v1's code (`workshop/known_car.py`, `known_car_lookup` in `workshop/views/autocomplete.py`,
the lookup script at the foot of `jobcard_form.html`, `workshop/vehicle_ids.py`, and their
tests in `test_known_car.py` and `test_vehicle_ids.py`). It changes these job card rules:
JOB-14, JOB-15, JOB-16, JOB-20 and JOB-59 (`docs/rules/job-card.md`). Why a car is one
record: ADR-0030. Why these rules: ADR-0031. Words: `docs/GLOSSARY.md`. The code:
`apps/jobs/` and `apps/vehicles/`.

- Each rule has an ID. A test names the ID of the rule it protects.
- An ID never changes. A new rule takes the next free number.
- Each rule says where it comes from: **v1** (kept as it was), **v1, changed**
  (and what changed), or **new** (v2 only).
- Every rule is built with this module, unless it says when.

v1 knew a car only by its plate: its job cards held the car as text, so the plate was the
car. Now a car is one record with its whole history (JOB-11). Its plate can change, and two
records can disagree. These rules find the car, fill the card from it, and ask before one
car's record is used for another.

## Finding the car

- **KNOWN-1** A plate names the car that has it today. A plate that no car has today, but
  that a job card came with, is an old plate: it names the car of the newest such card,
  because a car keeps its history when its plate changes, like a car from another state
  registered here, or a temporary plate made permanent. A plate can also pass to another
  car, so a save never takes an old plate on trust: it always asks (KNOWN-10). A plate no job
  card has come with names no car. *v1, changed: v1 knew a plate only as the plate itself.*
- **KNOWN-2** The server finds the car the same way when it fills the boxes and when it
  saves the card, so a page with no script saves the same card. *New.*
- **KNOWN-3** A car can be left with no plate for a while, when the car in front of you
  takes its plate (KNOWN-10). Its job cards keep the plates they came with, and it is found
  again by its VIN (KNOWN-11). A car with neither a plate nor a VIN stays, with its history,
  and its next visit starts a new car. *New.*

## Filling a new job card

- **KNOWN-4** On a new job card, leaving the plate box asks the server what the workshop
  knows about that plate. The car's brand with its model, its colour with Other's own
  colour, its chassis code and its VIN fill their boxes, each group whole or not at all, so
  a card never shows one car's brand beside another car's model. The mileage, the lead
  mechanic, the date and the note belong to this visit, so they are never filled. *v1:
  `known_car.py`, "each is answered whole".*
- **KNOWN-5** A box a person typed into, or emptied, is never touched. A box the fill wrote
  is written again when the plate changes, so a plate typed wrong and then corrected swaps
  the first car's details for the second car's, or takes them off. An answer that comes
  after the plate changed again is dropped. A page that comes back after a refused save or
  a question has the plate's answer with it: a box that still holds what the car holds counts
  as the fill's, and a box holding anything else counts as typed. That page cannot know a box
  was emptied before, so an empty box is filled. If the server cannot be reached, nothing
  happens, and typing still works. *v1: the lookup script.*
- **KNOWN-6** A fill marks the card unsaved, as typing does (JOB-47), and the VIN's meter
  and the colour's swatch, rail and dot show what it wrote. *v1: `jcFormTouched()`.*
- **KNOWN-7** The last customer (JOB-29) is offered, never filled. Their name and number
  show greyed and in italics inside the two customer boxes, with one Use last visit button
  beside the name's label, which copies both. The offer shows only while both boxes are
  empty, and it stays on a page that comes back. The customer section opens to show it, but
  never again after someone closed it. *v1: "the customer is offered, never filled", because
  cars change hands, and that number is the one the bill's WhatsApp button opens.*
- **KNOWN-8** Floor's answer has nothing about the customer: no name, no number and no
  button, anywhere in what is sent (ROLE-17). The same permission that picks Floor's form
  decides it. *v1: `include_customer`.*
- **KNOWN-9** A line under the plate box says what the plate found, only when it matters:
  an old plate, with the car's plate today; and a car with an open job card, with its
  number, and a link when it is in this branch (JOB-4). For any other known car, the filled
  boxes say it. A page that comes back keeps the line, and when the save refused the plate
  for its open card, only the refusal says so. *New.*

## The save asks first

- **KNOWN-10** A known plate typed with another brand is never saved over that car, and an
  old plate always asks, even with the same brand. The save asks whether the car in front of
  you is that car, naming it, like "KL10AA1000 is the plate of Toyota Innova. Last in on 3 Mar
  2026." Same car: the brand and the model typed replace the saved ones (JOB-14). Another
  car: the car in front of you, checked against its RC, takes the plate as a new car, and the
  Toyota keeps its visits. The new car takes nothing the Toyota holds: a chassis code, a VIN
  or a colour the same as the Toyota's was written by the fill, so it is dropped, and what was
  typed stays. If the plate was the Toyota's plate today, it has none until it is found again
  (KNOWN-3). A car with that plate today and an open job card is refused before any of this
  (JOB-4). The same question comes when the brand changes on a saved card whose car has
  another visit. *New (`docs/PLAN.md`, ADR-0030).*
- **KNOWN-11** A VIN saved on another car is never moved quietly: the save asks. When the
  other car has the same brand, and the car in front of you has no record of its own yet (a
  plate the workshop has never seen, a card's car with no other visit, or after the person
  said the car a plate found is another car), it asks "Is it the same car, now with
  KL10AA1000?". Same car: the card is that car's, and the plate typed
  is its plate from today, while its earlier cards keep theirs. Otherwise it asks to check
  the VIN on this car's RC. When this car keeps the VIN, the other car's VIN is emptied, and
  its empty box asks for it at its next visit (JOB-48). Two cars that both have visits are
  never joined: there is no merge tool. *New (`docs/PLAN.md`: a VIN never decides alone, and
  "same car?" comes only when the brand matches). It replaces JOB-20's refusal.*
- **KNOWN-12** A plate or a VIN is never taken from a car with an open job card, because
  then both cars are in the workshop and one card is wrong. The save is refused next to the
  box, naming that card, with a link when it is in this branch, so that card is fixed
  first. An old plate takes nothing from its car, so it asks first: another car is free, and
  same car is refused (JOB-4). *New.*
- **KNOWN-13** A question is a card at the top of the form, with everything typed kept
  below it. Its answers are buttons that send the form again, and fixing a box and saving
  again is always a way out, so Enter in a box saves again and never answers. An answer
  names the car it is about, so if the records changed in between, the save asks again. One
  question at a time; an answer already given stays for the next one, and a refused save
  forgets them all, so each can be given again, differently. It works with no script, and it
  uses no job card number (JOB-6). *New: v1 never asked.*

## Moving a job card

- **KNOWN-14** On an open job card, a plate that names another car (KNOWN-1) asks "Move
  this job card?", naming it. Move: the card is that car's now, with its number and
  everything on it, and the plate typed is that car's plate from today. Nothing else from the
  form goes on that car, except as KNOWN-16 says, and its boxes then show its own. An old
  plate has one more answer: it is another car, so this card's car takes the plate, and
  nothing changes on the other car. A plate another car has today has no such answer, because
  a plate is on one car: fix the box instead. *New (`docs/PLAN.md`). It replaces JOB-15's
  refusal.*
- **KNOWN-15** On an open job card, a plate that names no other car becomes its car's plate
  with no question when the car has no other visit: a typing slip fixed. When it has, the save
  asks whether the car got a new plate. A new plate: the car's plate changes from today, and
  its earlier cards keep theirs. Another car: the card moves to a new car with this plate,
  and the first car keeps its plate and its visits. *v1, changed (JOB-15): v1's card held
  the plate as text.*
- **KNOWN-16** A new car made by a move takes the brand and the model the page shows, and of
  its other boxes only what was typed, because the rest describes the car it leaves. A car a
  move leaves with no other visit was typed for the car in front of you, so what it holds goes
  into the boxes empty on the car the card moves onto, never over what that car holds. A car
  with other visits gives nothing. A car that a move leaves with no job card is removed: it
  was made by mistake, and nothing else knows it. A car with any job card is never removed.
  *New.*
- **KNOWN-17** Every role that changes job cards may move one (JOB-53), because Floor
  already answers the same questions when it makes a card, and every question names the
  cars first. A cancelled card never moves (JOB-51), and a settled one never will (Settle
  bill). *New.*

## Who may do what

- **KNOWN-18** Every role looks up a known plate (ROLE-15). The lookup only shows: it
  answers a GET, and refuses a POST (ROLE-5). *v1: `staff_required`.*

## The answer

- **KNOWN-19** The answer is a small part of the job card's page, made by the server
  (ADR-0016). A lookup whose session has ended sends the whole page to sign in (SIGN-39).
  Any other refusal or error leaves the page as it was, by the base page's htmx setting. *New.*

## Left out for now

- Old bills answer too, for what their paper carries (the brand, the model and the
  customer's name): with the old bills tool (Phase 6). *v1.*
- The car's page, with its plates, its visits and its VIN: Car profiles (After), with these
  same rules.
- Joining two cars that both have visits: only if the staging trial shows a need
  (`docs/PLAN.md`).
- Suggestions while typing a brand or a model: Phase 6.
- The History switch (ADR-0028) may hide another branch's visits from the line under the
  plate box and from the questions: with Branch screens.

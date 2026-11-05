# Rules: job card

The rules of the Job card module (`docs/MODULES.md`), taken from v1 and checked in
v1's code (`JobCard`, `JobCardConcern` and `JobCardLabourItem` in
`workshop/models.py`, `JobCardForm` in `workshop/forms.py`,
`workshop/views/jobcard.py`, `workshop/vehicle_ids.py`, `workshop/mileage.py`,
`jobcard_form.html`, and their tests). Why the records have this shape: ADR-0030.
Words: `docs/GLOSSARY.md`. The code: `apps/jobs/` and `apps/vehicles/`.

- Each rule has an ID. A test names the ID of the rule it protects.
- An ID never changes. A new rule takes the next free number.
- Each rule says where it comes from: **v1** (kept as it was), **v1, changed**
  (and what changed), or **new** (v2 only).
- Every rule is built with this module, unless it says when.

## What a job card is

- **JOB-1** A job card is one visit of one car. It holds the car, the customer if
  there is one, the concerns, the jobs done and one labour charge. *v1. Parts come
  with Parts on the job card (Phase 6).*
- **JOB-2** A job card belongs to one branch. A card of another workshop or another
  branch is never found: its pages answer "Not found" (ROLE-10). *New (ADR-0028).*
- **JOB-3** A job card is Open or Cancelled. Later steps add its other states: Ready
  with the live board (Phase 6), and Settled with Settle bill. *New: v1 kept these as
  separate flags.*
- **JOB-4** A car has one open job card at a time, across all the branches of its
  workshop, and PostgreSQL holds this. A second is refused, with no way around it.
  The refusal names the open card's number, with a link to it when it is in this
  branch. A cancelled card does not count. *v1: `get_active_conflict`, "hard block,
  no bypass"; ADR-0028.*

## The number

- **JOB-5** A job card gets its own number when it is first saved. It looks like
  JC-0027: the letters JC, and a count of at least four digits, which grows past 9999 to
  JC-10000. A bill has its own number, like INV-26-27-0045, given when the bill is final
  (Settle bill). *v1, changed (ADR-0030): v1 gave one number, JB-26-027, to the job card
  and its bill.*
- **JOB-6** The count runs per branch and never restarts, from a counter row locked in the
  same transaction as the job card. Two cards saved at one moment never take one number,
  and a save that fails uses no number. It is never a PostgreSQL sequence, which skips a
  number when a save fails. *New (`docs/PLAN.md`): v1 read every number of the year under
  a lock, and once sorted them as text, so 999 came after 1000.*
- **JOB-7** A number is unique in its branch, by PostgreSQL, and it never changes. A
  cancelled card keeps its number, and that number is never given again. *v1.*
- **JOB-8** A job card's number is not a tax number. GST's rule for a consecutive serial
  number is about the bill, so a cancelled card or a free job leaves no hole in the bills,
  and no bill is dated before a lower number because a car waited for parts. *New
  (ADR-0030).*
- **JOB-9** A branch's own letters come when a workshop's second place is real, and no
  saved number changes then. Until then, each branch counts from JC-0001. *New. Built with
  Branch screens.*
- **JOB-10** The printed bill shows both numbers, and a list's search finds a card by
  either. *New. Built with Printed bill and the lists (Phase 6).*

## The car

- **JOB-11** A car is one record in a workshop, shared by its branches, with its whole
  history. The same car in another workshop is another record there. *New (ADR-0006):
  v1 kept the car as text on each job card, so a car's history was a search.*
- **JOB-12** The brand and model, chassis code, VIN and colour belong to the car. A
  change on a job card changes the car, so it is right on the next visit. *New. A
  settled bill keeps its own frozen copy (Settle bill).*
- **JOB-13** A job card keeps the plate of that visit. A new plate changes the car from
  that day on, and an old card still shows the plate it came with. *New
  (`docs/PLAN.md`).*
- **JOB-14** A plate typed on a new job card finds its car, and a plate the workshop
  has never seen makes a new car. What was typed is the car in front of you, so it
  replaces what the record says, and a box left empty changes nothing. *New. Known
  plate fills the boxes first, and asks before another brand replaces the saved one
  (step 7).*
- **JOB-15** Changing the plate on an open job card: a free plate becomes the car's
  plate, and a plate on another car is refused next to the box, naming that car. *v1,
  changed: v1's card held only text, and it refused only a plate with another open
  card. Moving a card to the right car comes with Known plate (step 7).*
- **JOB-16** A plate is required, and it is saved in one spelling: capitals, with
  spaces, dashes, dots and slashes gone, so "kl-10 aa 1000" is KL10AA1000. What is left
  must be letters and digits, up to 20, and PostgreSQL holds that. Its shape is never
  judged further, because temporary, new and other countries' plates are real. A car with
  no plate yet takes its temporary number or its VIN here. A plate belongs to one car in a
  workshop, by PostgreSQL. *v1, changed: v1 only trimmed it and raised its capitals, so
  KL 10 AA 1000 and KL10AA1000 were two cars.*
- **JOB-17** The brand and the model are required. Each workshop has one list of
  brands, and one list of models for each brand. A typed word finds its entry whatever
  the capitals, and the list's spelling wins, so "bmw" shows BMW. A new word joins the
  list by itself. A new brand is tidied like a staff name (STAFF-6), and a new model
  only loses extra spaces, so i20 and CR-V stay. *v1, changed: v1 kept both as text on
  each card and fixed the spelling on each save, and a brand not yet on its list lost its
  capitals, so BYD became Byd. Renaming and merging come with Master lists (Phase 6).*
- **JOB-18** The chassis code is optional, up to 20 characters: capitals, with spaces
  gone. It is never refused for its shape, because real codes carry dots, like 991.2.
  Floor may record it. *v1: `normalise_chassis_code`.*
- **JOB-19** The VIN is optional. It may be typed in groups, and it is saved in
  capitals with spaces and dashes gone. It must then be exactly 17 letters and digits,
  with no I, O or Q, and each slip is refused with its rule, never corrected. There is
  no check-digit test, because European makers fill that place freely. A small meter
  above the box counts to 17: it turns green at 17 and red past it. The browser is
  never told to cut the box off. Floor may record it. *v1: `vin_problem`,
  `_prepare_vehicle_ids`.*
- **JOB-20** A VIN belongs to one car in a workshop, by PostgreSQL. A VIN saved on
  another car is refused next to the box, naming that car. *New (`docs/PLAN.md`).
  Known plate replaces this refusal with its question (step 7).*
- **JOB-21** The colour is optional: v1's 14 colours, or Other, where the browser's own
  colour box picks any colour, or Not set. Other left at the box's starting grey is
  refused, because nobody chose it. A swatch opens the choices, each with its name
  in words, because a tablet has no tooltip. The head's rail and dot show the colour. A white car's rail has an
  edge. A car with no colour has a hatched rail, because plain grey would say the car
  is grey. *v1: `CAR_COLOR_CHOICES`, `_car_color_picker.html`.*

## This visit

- **JOB-22** Mileage is kept on the job card, one reading for each visit: a whole number
  of kilometres, from 1 to 20,00,000. Commas are fine only where they truly group a
  number, like 50,000 or 1,02,340, and km may follow. Anything else is refused in plain
  words, never guessed: miles, a decimal, 50k, or 0. Empty means the odometer does not
  work or was not read, and settling warns about that (step 8). *v1, changed: v1 read
  the same shapes, but it also took 50k, rounded a decimal, and saved as text whatever
  it could not read.*
- **JOB-23** The lead mechanic is optional, picked from this branch's Mechanics, then
  its Assistant Mechanics, each by name (STAFF-15). Only people turned on are offered. A
  card keeps the person it has, shown with "not current" when they have been turned
  off or their designation has changed, so opening an old card never clears them. *v1:
  `MechanicChoiceField`, and its tests.*
- **JOB-24** The admitted date is required and starts at today, in India time. A date
  in the future is refused, never moved to today. An earlier date is fine. The picker
  stops at today, but only the server decides. *v1: `clean_admitted_date`.*
- **JOB-25** The internal note is optional, up to 255 characters, about this visit.
  Every role may write it. It is never printed on a bill. Its box starts one row tall
  and grows with its words. *v1: `JobCard.notes`.*

## The customer

- **JOB-26** A customer is optional, because many cards carry none. Their section
  stays folded while it has nothing to show, and it opens by itself for a name, a
  number, a note, or an error inside it. A closed section still saves what is in it.
  *v1: "folded away, because this workshop rarely fills it".*
- **JOB-27** A customer is one record in a workshop, shared by its branches. It is
  found by the name and the number together, whatever the capitals, so typing the same
  two boxes again finds the same record. Another name with the same number is another
  record: one phone can serve a family or a company, and a card's name never changes
  because of another person's visit. PostgreSQL holds this. A customer needs a name or
  a number, or both. *New (ADR-0006, ADR-0030): v1 kept both as text on each card.*
- **JOB-28** Changing the two boxes points the card to the record they name, and no
  other card changes. Emptying both takes the customer off the card. Changing only a
  name's capitals corrects the record. A record left with no card stays, and shows
  nowhere. *New.*
- **JOB-29** A car's customer today is the customer on its newest job card that has
  one. It is not saved on the car, so a sale changes nothing but the next card. *v1:
  `known_car.py`, "from the newest visit that recorded either".*
- **JOB-30** A name is tidied like a staff name (STAFF-6), up to 150 characters. A
  contact number loses its spaces, dashes, dots and brackets, and a leading + stays.
  +91 or 91 before a 10-digit mobile goes, so all three are one number. A leading 0
  stays: 080 40000001 is a landline, and it cannot be told from a mobile written with
  a 0. Anything else must be 7 to 15 digits, so a landline and a Gulf number are fine.
  Letters are refused. *v1, changed: v1 saved whatever was typed, and its WhatsApp
  button read the number later.*

## The labour charge

- **JOB-31** A job card has one labour charge for all its work, typed once, under the
  jobs. No job line has a price. *v1: `labour_amount`, "quoted as a whole".*
- **JOB-32** The labour charge is a money column that may be zero, and its box follows
  ADR-0029: an empty box means 0, a negative amount or a comma is refused in plain
  words, and a saved amount shows ready to type over. *v1, changed: ADR-0029.*

## Concerns and jobs

- **JOB-33** Concerns are what the customer reported. Each has a status: Pending,
  Working or Fixed, each with its word and its colour. A new one is Pending. A status
  box takes its colour as soon as it changes, before saving. *v1: `JobCardConcern`.*
- **JOB-34** Job Performed lists what was done, in words, up to 150 characters each. A
  concern holds up to 255. Spaces at the ends and double spaces go. *v1, changed: a
  concern had no limit.*
- **JOB-35** Each list keeps one open, empty row at its end, and typing into it opens
  the next, so there are no Add buttons. An untouched open row is never saved. A status
  alone is not typing, and an open row's status stays grey. With no script, one open
  row comes back after each save. *v1's Old Bills, chosen in the lab.*
- **JOB-36** Emptying a saved row's words and saving removes that row. *v1: its blank
  rows, worked out again on every submit. Now the server decides.*
- **JOB-37** The same words twice on one card, whatever the capitals, are one row, and
  PostgreSQL holds this. A new row that repeats one is left out with no error, so a
  slow network can never add lines twice. A saved row changed to repeat another is
  refused next to it. *New.*
- **JOB-38** Rows stay in the order they were added. *v1.*

## History

- **JOB-39** Every step of a card is a row with its time, one per change, saved in the
  same transaction as the change: Car in when the card is made, and each change of a
  concern's status. It cannot be filled in later. *New (`docs/PLAN.md`). On hold, back,
  Ready and its undo come with their buttons (live board, Phase 6), part ordered and
  received with parts (Phase 6).*
- **JOB-40** A step also keeps who acted, by login, and the lead mechanic at that
  moment, because a shared Floor login says only Floor (ROLE-3). *New.*
- **JOB-41** A concern's status and its newest step always agree, and a test checks it.
  A save that changes no status adds no step. Removing a concern removes its steps. A
  new concern already Working or Fixed gets its step when it is saved. *New.*

## Saving

- **JOB-42** A double tap or a slow network never makes a card twice. The form's address
  holds the new record's key, and a repeat opens the card saved the first time, with
  the same notice. Another plate sent with a key already used, like from a page brought
  back by Back, is not saved, and the notice says so. The key used by another workshop
  or branch answers "Not found". *New (`docs/PLAN.md`).*
- **JOB-43** A save changes only what this person changed since opening the page, in
  one locked transaction. So a tablet left open all morning can never put back Office's
  fix or a concern's old status. When two people change one box, the later save wins. A
  row someone else removed stays removed. *New: v1 saved every box on the page.*
- **JOB-44** A refused save says so in a notice with its sound, says how many things to
  fix, and lists each one by what it holds, like "Concern, AC not cooling". Each error
  also sits next to its box, and everything typed stays. *v1: `_collect_problems`.*
- **JOB-45** After a save the card stays open, with a notice and its sound. *v1.*
- **JOB-46** The button says Save Job Card on a new card, in blue, and Update Job Card
  on a saved one, in amber with dark words. It shows it is busy after one tap. *v1,
  changed: v1's new-card button was green, and in v2 green means done or paid.*
- **JOB-47** Once anything is typed and not saved, the pinned head turns amber and, from
  576 pixels wide, says Unsaved. The changed box gets an amber edge, painted inside it
  so nothing moves. Leaving the page asks first. A submit that really leaves clears it.
  *v1: `jc-dirty`.*
- **JOB-48** An empty box has a red hairline until it is filled, in colour only, so
  nothing moves, and it never blocks a save. The customer's name and number and the note
  have none, because they are empty on most cards. The chassis code and the VIN have one,
  on the owners' word. *v1: `jc-optional`. It is not the error state.*

## Cancelling

- **JOB-49** A job card is never deleted. A card that ends with no bill is cancelled,
  and it keeps its number and everything on it. *v1, changed (`docs/PLAN.md`): v1 deleted
  a card with no parts, no labour and no payment, and kept a copy in its Deletion
  History.*
- **JOB-50** Only Office and owners cancel. The button asks first, on a card over the
  page, with a reason that must be typed, up to 255 characters. Its two buttons say Keep
  job card and Cancel job card. *v1: `jobcard_delete`, `office_required`. v1's reason was
  optional; here it tells the owners why a car ended with no money.*
- **JOB-51** A cancelled card frees its car at once for a new card. Its page says
  Cancelled, with the reason, who and when. Every box is locked and looks it, and a send
  is refused. It cannot be brought back: if a card was cancelled by mistake, a new card
  takes a new number. *New.*
- **JOB-52** A card with parts cannot be cancelled until they are moved, and a settled
  card can never be. *v1: its delete guard. Built with parts (Phase 6) and Settle bill.*
- **JOB-64** When a card is cancelled, the owners get an alert. *v1: `RECORD_DELETED`.
  Built with the bell (Phase 6).*

## Who may do what

- **JOB-53** Every role makes and changes job cards (ROLE-15, ROLE-19). *v1:
  `staff_required`.*
- **JOB-54** Floor's form has no customer boxes and no labour box. They are left out,
  never hidden, so they are nowhere in Floor's page, and a send that names them changes
  nothing (ROLE-13, ROLE-16, ROLE-17). A new card from Floor has no customer and a
  labour charge of 0, and Office prices it after. *v1, changed: v1 sent the boxes hidden
  and put the saved values back on the server, after a Floor login turned a 5,000 rupee
  bill into 1 rupee.*
- **JOB-55** Floor's section is called Workshop Note, with the note alone. For Office and
  owners it is called Customer & Notes. *v1, ROLE-17.*
- **JOB-56** A role that may not save, like a read-only one added later, does not open
  this page or see its New button (ROLE-5). It reads a card on Job card view (Phase 6).
  *New.*

## The screen

- **JOB-57** The page is v1's job card, in its order: Car Details, the customer section,
  Customer Concerns, Job Performed with the labour charge, then the button. Parts come
  in their place in Phase 6. *v1, chosen in the lab (`docs/design/`).*
- **JOB-58** The head stays pinned while the page scrolls. It says New Job Card, or
  Editing with the colour dot, the car, the plate and the number. A long car name is cut
  short, and the plate and the number never are. *v1, changed: v1's head did not show the
  number.*
- **JOB-59** The plate comes first, before the brand and the model, as on v1's Old Bills,
  so a known car can fill them (step 7). *v1, chosen in the lab.*
- **JOB-60** A longer list never means more queries (`tests/test_query_counts.py`).
  *New (`docs/PLAN.md`).*

## The first live board

- **JOB-61** The home page is the first, plain live board, so a card can be found: every
  open job card of this branch, newest first, with its number, car, plate, lead mechanic
  and admitted date. A tap opens the card. An empty board says so, with the next step.
  *New, for now. Its cards, chips, drawers and filters are built in Phase 6, from
  `design/lab/live-board/`.*
- **JOB-62** Owners and Office start a card from the New button on this page, and Floor
  from New on its tab bar (ROLE-26). *v1.*
- **JOB-63** A job card's page lights the home tab, and Floor's new card lights its New
  tab (ROLE-28). *New: v1 lit no tab there.*

## Left out for now

- Parts, and the job lines suggested from them: Parts on the job card (Phase 6).
- On hold, Ready, and Ready's undo: the live board and the Completed list (Phase 6).
- Finding a car by an old plate or a VIN, filling the boxes from a known plate, offering
  the last customer, and moving a card to another car: Known plate (step 7).
- Locking a settled card, and the Invoice button: Settle bill (step 8). The Profile button:
  Car profiles (After). A button comes with its page (ROLE-32).
- Suggestions as you type, and the concerns list: Phase 6. Photos: After. Warranty cards,
  v1's second kind of card: After. A fleet account on the card: Phase 6.
- Job card view, the read-only page: Phase 6.
- v1's Job Cards list page, a search of every card: checked with the Completed list and the
  bill lists (Phase 6). It is in no module today.
- The pinned round Save button: with parts (Phase 6), when the form is long enough to need
  it.
- The light that runs around the button, the squash on a tap, and the flash on a new row:
  polish, for after go-live if the owners miss them. v1 flashed a row because its Add button
  was far from the new row, and there is no Add button now.
- v1's warning about clearing a part's name: with parts (Phase 6).

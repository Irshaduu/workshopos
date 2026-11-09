# Glossary

One name for each thing. The word a person reads on screen is the word in
the code (models, functions, files, URLs) and in the docs.

- A new word goes here before it is used anywhere. Each section adds its
  words in step 1 of the loop (`CONTRIBUTING.md`).
- "Never say" holds v1's old names. Use them only to point to a v1 file.

| Say | In code | Never say | Means |
|---|---|---|---|
| Workshop | `Workshop` | | The business that uses the system, with all its branches |
| Branch | `Branch` | | One place where a workshop works. A workshop has one or more |
| Workshop-wide | `WORKSHOP_WIDE_MODELS` | | A record that belongs to the whole workshop, not to one branch, like a customer or a car |
| Membership | `Membership` | | An account's place in a workshop, with its role |
| Role | `Role` | group; Admin, for an owner | A member's part in the workshop: Owner, Office or Floor. What each role may do is its permissions |
| Permission | `has_perm()`, `perms`, `permissions.py` | ability, right | One thing a role may do, like see prices or settle a bill. Each app lists its own, with the roles that have each |
| Module | `Module`, `modules.py` | feature | One part of the system, as listed in `docs/MODULES.md`, like Sign-in or Job card |
| Page mark | `@page` | | The line above a page's view that names its module and the permission it needs |
| Tab bar | `tab_bar` | nav bar, top bar | The row of tabs on every page of the app: at the top on a tablet and a laptop, at the bottom on a phone |
| Tab | `tab` | pill | One place on the tab bar, like New or Inventory |
| Role menu | `RoleMenu` | | One role's tabs and menu sections, written once in `apps/accounts/menu.py` |
| Menu | `menu` | drawer, for the menu | The list of every other page, opened from the tab bar's Manage (Office, Owners) or Menu (Floor) |
| Sign in | `sign_in`, the page `sign-in/` | log in, login (as a verb) | Start using the system: an owner types the email and the code sent to it; Office and Floor type a username and the password |
| Sign out | `sign_out`, the page `sign-out/` | log out, logout | End the session on this device |
| Username | `username` | identifier | What Office and Floor type to sign in. It starts with the workshop's short code and a dot, like `ab.floor` |
| Login name | `login_name` | | The part of a username after the short code and its dot: `floor` in `ab.floor`. Small letters and digits |
| Short code | `short_code` | | A workshop's 2 to 8 small letters or digits, set once and unique on the server. Every username of the workshop starts with it |
| Locked | `minutes_locked()` | | An account with a password that cannot sign in for 15 minutes, after 5 wrong passwords in a row |
| Unlock | `unlock()` | | An owner lets a locked Office or Floor account sign in again at once |
| Sign-in code | `SignInCode` | OTP, reset code | 6 digits emailed to an owner, who types them to sign in. It works once, for 10 minutes, in the browser that asked for it |
| Link a device | `link_device`, the page `link-device/` | pair, approve a device | What an approver does so a new device signs in: types its device code, picks a login and agrees (ADR-0027). Not built yet |
| Device code | `DeviceCode` | pairing code, PIN | 8 letters a new device shows while it waits to be linked. It only names the waiting device, and ends after 10 minutes. Not built yet |
| Approver | | | Someone signed in who may link devices: an owner, at first |
| Remove | `remove_device()` | kick out, revoke | An owner ends a device's session from the list of devices. The device is out at its next request. Not built yet |
| Branch Owner | `Role.BRANCH_OWNER` | branch partner | A login limited to one branch, for a partner in that place; read-only for a funder (ADR-0028). Not built yet |
| History switch | | | One per branch: whether its visits show at the workshop's other branches (ADR-0028). Not built yet |
| Overview | `overview` | dashboard, for this page | An owner's first page: cars on the floor, money and what needs a look today. Not built yet |
| Work | | | The owners' tab that opens the live board. Not built yet |
| Fleet account | `FleetAccount` | bulk payer | A company that sends many cars and pays for them together |
| Fleet payment | `FleetPayment` | bulk payment | One payment from a fleet account that settles many of its bills |
| Staff member | `StaffMember` | mechanic, for everyone | A person who works at the workshop. Mechanic is one of the designations |
| Staff list | `staff_list`, the page `staff/` | Staff Registration, roster | The page of a branch's staff members, and the owners' place to add and change them |
| Designation | `Designation`, `designation` | role, for a staff member | A staff member's job: Mechanic, Assistant Mechanic, Office Staff or General Helper. A member's Owner, Office or Floor is their role |
| Lead mechanic | `lead_mechanic` | mechanic (staff), assigned mechanic | The staff member picked on a job card to do its work |
| Job card | `JobCard` | bill, before it is settled | One visit of one car to one branch |
| Job card number | `JobCard.number`, `NumberCounter` | job number, serial | A job card's own number, like JC-0027, given when the card is made |
| Bill number | | invoice number, on a plain bill | A bill's own number, like INV-26-27-0045, given when the bill is final. Old Excel bills keep their JB numbers. Not built yet |
| Open | `JobCardStatus.OPEN` | active, live | A job card that has not ended. A car has one at a time |
| Cancelled | `JobCardStatus.CANCELLED`, `cancel()` | deleted, trashed | A job card that ended with no bill. It keeps its number and everything on it |
| Admitted date | `admitted_date` | check-in date | The day the car came in |
| Car | `Car` | vehicle, except in the app's name `vehicles` | One car in a workshop, with its whole history |
| Plate | `plate` | registration number, reg no | The letters and digits on a car's number plate. The box is called Plate Number |
| Known plate | `known_plate`, `known_car()`, `KnownCar`, the page `job-cards/known-plate/` | autofill | A plate the workshop has seen. On a new job card it fills the car's boxes from its record. Asking the server about a plate is the lookup |
| Old plate | | previous plate, old registration | A plate a car came with on an earlier job card, before it got a new one. It still finds the car |
| RC | | registration certificate | The car's registration paper. It shows the plate, and the VIN as Chassis No. |
| Car brand | `CarBrand` | make, marque | A maker, like BMW, on the workshop's list of brands |
| Car model | `CarModel` | | A model of one brand, like 520d, on that brand's list |
| Chassis code | `chassis_code` | platform code | A car's generation, like F30. Many cars share one |
| VIN | `vin` | chassis number | The 17 characters that name one car, from the RC book's Chassis No. |
| Colour | `colour`, `colour_other` | color, paint | A car's colour: one of the list, or Other with a colour of its own |
| Mileage | `mileage` | odometer, km, kilometres (as a name) | The car's reading at this visit, in whole kilometres |
| Internal note | `note` | notes, remarks | A line about this visit for the workshop only, never printed |
| Customer | `Customer` | owner, client (for a car's owner) | A name and a contact number, as one record in a workshop |
| Contact number | `contact_number` | phone, mobile (as a name) | The number a customer is reached on |
| Last customer | `last_customer()` | owner, for a car | The customer on a car's newest job card that has one. A new job card offers them to Office and owners |
| Concern | `Concern` | complaint | One thing the customer reported, with its status: Pending, Working or Fixed |
| Job line | `JobLine` | labour item, labour line | One job that was done, in words, with no price. The list is called Job Performed |
| Labour charge | `labour` | labour amount, subtotal, total labour | One amount for all the work on a job card |
| Step | `JobCardStep` | event, log | One change in a job card's life, with its time, like Car in or a concern Fixed |
| Move | `move` | transfer, reassign | Putting an open job card on another car, when it was made on the wrong one. It keeps its number and everything on it |
| Question | `Question` | conflict, clash | What a save asks before it uses one car's record for another, with a button for each answer |
| Live board | `live_board` | dashboard, floor board | The home page: every car open in this branch |
| Turned off | `is_active`, `turn_off()`, `turn_on()` | retired, archived, deactivated | A staff member or an account kept on record but no longer in use. Never deleted; Turn on brings them back |
| Supplier | `suppliers` (the app) | | Any shop we buy from: a spare shop or a supplies shop |
| Spare shop | `SpareShop` | | A shop we buy a part from for one job |
| Supplies shop | `SuppliesShop` | supplier shop | A shop we buy stock from, for the shelf |
| Product | `Product` | item | Something the workshop keeps in stock |
| Money column | `MoneyField` | | A database column for an amount of rupees and paise. All have one size, and each says whether zero is allowed |
| Money box | `MoneyFormField` | | The box a person types an amount into |
| Money that moved | `MoneyField()` | | An amount that really changed hands, like a payment. Always above zero |
| Charge | `MoneyField(allow_zero=True)` | | An amount the workshop asks for, like labour or a part's price. It may be zero |

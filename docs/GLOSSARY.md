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
| What Office sees | | Office access, Office permissions | An owner's page of switches that hide a few facts from Office, like customer numbers. Not built yet |
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
| Attendance | | register, roll call, muster | Each working day's marks for the staff members who are turned on, saved by Office or an owner. Floor never sees it. Not built yet |
| Present, Half day, Absent | | P, H, A; leave, for one day | A staff member's mark for one working day. The page starts with everyone Present. Not built yet |
| Not marked | | missing, pending | A past working day with no saved attendance. It is never counted as present. Not built yet |
| Weekly off | | week off, weekly holiday | The days of the week a branch does not work, like Sunday. The owners set them once, with the date they start. Not built yet |
| Paid holiday | | festival leave, public holiday | A day the workshop closes with pay, saved with its name, like Eid ul-Fitr. A day closed with no pay is a normal attendance day, with everybody Absent. Not built yet |
| Leave days | | leaves, absences | The days cut from a staff member's salary in a month: Absent counts 1 and Half day 0.5. Worked out from attendance, never typed. Not built yet |
| OT | | extra hours, extra time | Overtime: extra pay for staying late, or for work on a weekly off or a paid holiday, with its day, a note and its amount. Not built yet |
| OT request | | OT claim | What Floor sends from the floor tablet to ask for OT: a staff member, a day and a note, with no amount. Office or an owner accepts it, with the amount, or declines it. Not built yet |
| Job card | `JobCard` | bill, before it is settled | One visit of one car to one branch |
| Job card number | `JobCard.number`, `NumberCounter` | job number, serial | A job card's own number, like JC-0027, given when the card is made |
| Bill number | `Bill.number`, `BillCounter` | invoice number, on a plain bill | A bill's own number, like INV-26-27-0045, given when the bill is final. Old Excel bills keep their JB numbers |
| Open | `JobCardStatus.OPEN` | active, live | A job card that has not ended. A car has one at a time |
| Cancelled | `JobCardStatus.CANCELLED`, `cancel()` | deleted, trashed | A job card that ended with no bill. It keeps its number and everything on it |
| No charge | `JobCardStatus.NO_CHARGE` | free bill, zero bill; cancelled, for work done | A job card that ended with its work done and nothing to pay, because its bill came to 0, with the reason. It keeps its number and gets no bill number. Not built yet |
| Charge next time | `charge_next_time` | pay later (a SaaS module), deferred charge, unbilled diagnostics, credit | A No charge visit marked to be charged at the car's next visit, with an amount if an owner named one. The car's next job card shows it as a note, and the Charge next time list keeps every one still waiting. Never a debt and never a discount. Not built yet |
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
| Car picture | | profile photo, cover photo | The one photo of a car chosen to show it, small, on its job card and its page. Not built yet |
| Mileage | `mileage` | odometer, km, kilometres (as a name) | The car's reading at this visit, in whole kilometres |
| Internal note | `note` | notes, remarks | A line about this visit for the workshop only, never printed |
| Customer | `Customer` | owner, client (for a car's owner) | A name and a contact number, as one record in a workshop |
| Contact number | `contact_number` | phone, mobile (as a name) | The number a customer is reached on |
| Last customer | `last_customer()` | owner, for a car | The customer on a car's newest job card that has one. A new job card offers them to Office and owners |
| Customer profile | `customer_profile` | customer history, for this page | An owner's page about one customer: their cars, visits, billed and discounts. Not built yet |
| Join | `join_customers()` | merge, for customers | An owner puts two customer records of one person together, so the customer profile shows them as one person with both numbers. It changes no visit and no bill, and it can be undone. Not built yet |
| Concern | `Concern` | complaint | One thing the customer reported, with its status: Pending, Working or Fixed |
| Job line | `JobLine` | labour item, labour line | One job that was done, in words, with no price until Job amounts (Phase 6). The list is called Job Performed |
| Labour charge | `labour` | labour amount, subtotal, total labour | One amount for all the work on a job card. With Job amounts (Phase 6) it is worked out from them, never typed |
| Job amount | `job_amount` | job price, line price | The amount on one job, before the discount. The labour charge adds them up. Not built yet |
| Suggested job amount | `suggested_job_amount()` | autofill, default price | What the same job came to on the last settled bill of a car of the same model, shown in grey in an empty amount box until Fill suggested amounts puts it in. Not built yet |
| Job word | `JobWord` | verb, action, status (for a part's job) | The word after a part's name in Job Performed, like replaced in Engine oil replaced, picked in the part's What was done box. Each workshop keeps its own list, in Master lists. Not built yet |
| No line needed | | skip, not applicable | The choice for a part that needs no line of its own, like grease, or a part another line covers. It prints nothing. Not built yet |
| Step | `JobCardStep` | event, log | One change in a job card's life, with its time, like Car in or a concern Fixed |
| Move | `move` | transfer, reassign | Putting an open job card on another car, when it was made on the wrong one. It keeps its number and everything on it |
| Question | `Question` | conflict, clash | What a save asks before it uses one car's record for another, with a button for each answer |
| Bill | `Bill` | invoice, on a plain bill | What a customer pays for one job card: its jobs, the labour charge and the total; once settled, also its number, date, discount, net and payments |
| Preview | | draft, estimate, pro forma | A bill while its job card is open. It has no number, and it changes with the card |
| Settle | `settle_bill()` | close, finalise, mark paid | Record what the customer paid, by method. The rest of the bill is the discount, and the bill is final |
| Settled | `JobCardStatus.SETTLED`; a bill's `settled_at` and `settled_by` | paid, closed | A job card whose bill is settled. It is locked, and off the live board. The bill keeps when it was settled and by whom |
| Not filled | `unfilled()`, `Unfilled` | preflight, gaps, checklist | What is still empty on a job card. Shown before it is settled, and later on the live report |
| Bill sheet | `bill_sheet()`, `Sheet`, `_sheet.html` | invoice sheet | Everything a bill shows, worked out once, and the bill as it prints |
| Check | `Check` | confirm, review | What the settle box answers first when a settle has a discount: the total, each payment, the discount and the net, before anything is saved. A change of a settled bill's payments that leaves a discount answers with one too, showing what each figure was |
| Payment | `Payment` | receipt, received amount | Money a customer paid toward a bill, by one method. Always above zero |
| Payment method | `PaymentMethod` | mode, payment type | How a payment was made: Cash, UPI, Card or Bank transfer, always in words |
| Total | `total` | grand total, bill amount | What a bill adds up to, before the discount |
| Discount | `discount` | shortfall, write-off, concession | The part of a bill the workshop lets the customer off, kept as its own amount, before tax |
| Net | `net` | paid, amount paid, balance | A bill's total less its discount: what the customer pays |
| Date paid | `paid_on`, saved as the bill's `date` | paid date, payment date | The day the customer paid, as typed in the settle box. The bill is dated that day |
| Financial year | `financial_year` | FY, fiscal year | 1 April to 31 March, as Indian tax counts a year. A bill number carries it, like 26-27 |
| Frozen copy | | snapshot | A settled bill's own copy of what it prints about the customer and the car, so a later change to those records never changes the bill |
| Paid bills | `paid_bills_for()`, the page `paid-bills/` | settled list | The list of a branch's settled bills, newest first; a tap opens the bill. Office sees those settled in the last 7 days |
| Change payments | `change_payments()` | re-settle, settle again | Correcting the payments or the date paid of a settled bill, with the reason |
| Change history | `audit` (the app) | edit history, deletion history, audit trail | The record of every change to money after it was recorded. Its page for the owners comes in Phase 6 |
| Change | `Change`, `keep_change()`, `kept_change()` | edit, edit log, log entry | One kept change to money: each figure before and after, who, when and why. Kept for good |
| Edit window | `edit_window_hours`, `money_change_refusal()` | delete window, lock window | How long Office may change money after recording it: 24 hours at first. Each workshop's own setting |
| Back-date limit | `back_date_days` | backdate floor | How many days back Office may date money: 3 at first. Each workshop's own setting |
| Live board | `live_board` | dashboard, floor board | The home page: every car open in this branch |
| Turned off | `is_active`, `turn_off()`, `turn_on()` | retired, archived, deactivated | A staff member or an account kept on record but no longer in use. Never deleted; Turn on brings them back |
| Supplier | `suppliers` (the app) | | Any shop we buy from: a spare shop or a supplies shop |
| Spare shop | `SpareShop` | | A shop we buy a part from for one job |
| Supplies shop | `SuppliesShop` | supplier shop | A shop we buy stock from, for the shelf |
| Product | `Product` | item | Something the workshop keeps in stock |
| Fits | `Product.fits` | compatibility, fitment | The chassis codes a product fits, like B9 or F30 F31, in one box. Empty means any car. Not built yet |
| Money column | `MoneyField` | | A database column for an amount of rupees and paise. All have one size, and each says whether zero is allowed |
| Money box | `MoneyFormField` | | The box a person types an amount into |
| Money that moved | `MoneyField()` | | An amount that really changed hands, like a payment. Always above zero |
| Charge | `MoneyField(allow_zero=True)` | | An amount the workshop asks for, like labour or a part's price. It may be zero |

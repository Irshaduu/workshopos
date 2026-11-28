# Modules

What the system does, module by module, and when each one is built.
Order of work: `docs/PLAN.md`. Where the code lives: `docs/ARCHITECTURE.md`.

**When:**
- **Go-live:** needed for daily work on day one
- **After:** built after go-live
- **SaaS:** built when a second workshop wants the system (ADR-0004)

The Go-live marks are a draft until the client confirms them (`docs/PLAN.md`,
"Alongside: the client").

---

## Foundation

| Module | What it does | App | When |
|---|---|---|---|
| Phone, tablet and laptop | Laid out for each device; installs on a phone like an app | `core` | Go-live |
| Sign-in | Owners with a code sent to their email; every other role links a device, with no password (ADR-0027). Until that is built, Office and Floor use a password | `accounts` | Go-live |
| Roles | Owner, Office, Floor; each sees only what it needs, in its own tab bar and menu (ADR-0007, ADR-0026) | `accounts` | Go-live |
| Staff logins and devices | Staff logins (one per person, or one shared, like the floor tablet's), Link a device, the list of signed-in devices, and Remove (ADR-0027). The last owner can never be removed; a leaving person's login is turned off, never deleted | `accounts` | Go-live |
| Owner alerts | Push alerts to the owners' phones, and an alert feed | `notifications` | Go-live |
| Change history | Every deleted, edited and back-dated entry, month by month | `audit` | Go-live |
| Master lists | Brands, models, parts and concerns, with rename and merge; and the job words a part's line can take, which owners add, rename, put in order and turn off. The words start as replaced, topped up, refilled, removed and installed, refurbished, inspected and repaired. A word in use is never deleted | `vehicles`, `jobs` | Go-live |
| Confirmations and sounds | A clear question before anything important; a sound for each result | `core` | Go-live |
| Backups and money checks | Database copies; every typed amount checked before saving | `core` | Go-live |
| System guide and map | A tour of every section | to decide | After |
| Dark mode | A dark look for use at night, chosen per person; only if the client asks | `core` | After |
| **Workshop and branches** (new in v2) | The business and its locations (ADR-0006) | `workshops` | Go-live |
| **Workshop profile** (new in v2) | Name, logo, each branch's address and phone, UPI QR, used by every printed document. The GSTIN comes with GST invoicing | `workshops` | Go-live |
| **Workshop settings** (new in v2) | Discount limit, edit window, back-date limit, markup, each beside the rule that uses it (ADR-0024). A settings screen only if the owners want one | each app | Go-live |
| **Workshop status** (new in v2) | Active or suspended. A suspended workshop's pages are blocked, except signing out | `workshops` | Go-live |
| **Create a workshop** (new in v2) | One service creates a workshop, its first branch and its owner | `accounts` | Go-live |
| **Platform accounts** (new in v2) | The company's own staff, kept apart from workshop members (ADR-0007) | `accounts` | Go-live |
| **Module switches** (new in v2) | Each workshop turns modules on or off; off hides, never deletes (ADR-0011). Every page names its module from the first page; the switch is built when a module must first be off | `workshops` | Go-live |
| **What Office sees** (new in v2) | An owner's page of switches that hide a few facts from Office, at first customer numbers, shop phone numbers and shop prices, each turned off or on again at any time. Off hides the fact everywhere: on screen, on paper and in what the server sends, and Office cannot type it, so an owner does that work. Each change is kept in the change history. A short list fixed in the code, never a screen for making roles. It changes ROLE-1 (`docs/rules/roles.md`), so it needs an ADR first | `accounts` | Go-live |

## Job cards and the floor

| Module | What it does | App | When |
|---|---|---|---|
| Job card | Car, concerns, jobs and one labour charge; locked once settled | `jobs` | Go-live |
| Parts on the job card | Shop parts and shelf stock kept apart; ordered, received, expected. Each part also gets its own line in Job Performed, with one box, What was done: red while the part waits, green once a job word is picked, like Engine oil replaced. A shelf part waits from the moment it is added, a shop part once it is received. No line needed, for grease or a part another line covers, prints nothing. The word is kept on the part, so its line follows the part when it is removed, moved or renamed, and it is never picked by itself. A part still waiting is listed before settling, and never stops a settle | `jobs` | Go-live |
| Job amounts | An amount on each job, a part's line too, typed by Office and owners, never on Floor's page. The labour charge is worked out from them and never typed beside them, so the two cannot disagree. A job may be 0 when another job's amount covers it, and Floor cannot remove a job that has an amount. Extra work, like seized bolts cut and removed, is its own job with its own amount, so the usual job keeps its usual price and the bill shows why. The bill prints only the labour charge; a workshop setting also prints each job's amount, on bills settled after it is switched on. It replaces the one typed labour charge (JOB-31), so it needs an ADR first | `jobs`, `billing` | Go-live |
| Known plate | A known or old plate fills the car's brand, model, chassis code, VIN and colour, and offers the last customer; a save asks before it uses one car's record for another; an open job card moves to the right car | `jobs` | Go-live |
| Suggestions as you type | Car, part, concern and job names, so a job is written in the same words each time; the chassis codes already saved on cars of the same model | `jobs` | Go-live |
| Suggested price and markup | Customer price suggested from cost, with a markup badge | `jobs` | Go-live |
| **Suggested job amounts** (new in v2) | An empty amount box shows, in grey, what the same job came to on the last settled bill of a car of the same model, with its date; a model with no such bill shows nothing. One button, Fill suggested amounts, fills every empty box that has one, and the person checks them by eye and saves. Never filled by itself. A bargain goes into the discount at settle, never into a job's amount, so the last amount stays the usual one | `jobs` | After |
| Parts transport | Courier and parcel costs, counted in profit | `jobs` | Go-live |
| Live board | Every car in the workshop, filtered by mechanic | `jobs` | Go-live |
| Live report | Unfilled bills, parts on the way, each mechanic's open work | `reports` | Go-live |
| Job card view | One read-only page for each car; a Copy button for the VIN, which copies its 17 characters with no spaces | `jobs` | Go-live |
| Completed list | Cars ready to bill, with undo | `jobs` | Go-live |
| Ready-date estimate | An expected ready date, from parts on the way and each shop's past delivery times; flags parts not ordered yet | `jobs` | After |

## Appointments

| Module | What it does | App | When |
|---|---|---|---|
| Appointments | Book a date for a car; see how full each day is; suggest free dates | `jobs` | After (client confirms) |

## Bills and cash

| Module | What it does | App | When |
|---|---|---|---|
| Printed bill | A4 on the workshop's letterhead; PDF named after the car; WhatsApp button; a shelf product prints by its category, like Engine oil, never by its brand | `billing` | Go-live |
| Settle bill | Shows anything still unfilled before the bill is settled; takes what was paid by method, and the rest is the discount, shown before saving; gives the bill its number from the branch's own series; its payments are changed later with a reason, by Office within the edit window and by owners any time, and every change is kept | `billing` | Go-live |
| **No charge** (new in v2) | A visit whose bill comes to 0 ends as No charge, with its reason, in place of Settle: a free scan, or a job that takes no customer payment (own car, demo car, free redo). It keeps its job card number and gets no bill number, and the owners are told of each. It may be marked Charge next time, with an amount if an owner names one. The car's next job card then shows a note, Add to this card or Don't charge, and the Charge next time list keeps every one still waiting, oldest first, for follow-up. Never a debt and never a discount: a person always types the labour | `jobs`, `billing` | Go-live |
| Pending and paid bills | Who still owes, and every bill paid, by date | `billing` | Go-live |
| Discount audit | Every bill settled for less, largest first | `billing` | Go-live |
| Cashbook | Money in and out by the day it moved; asks before a double count | `finance` | Go-live |
| Fleet accounts | Company accounts; one payment settles many cars | `billing` | Go-live |

## Spare shops

| Module | What it does | App | When |
|---|---|---|---|
| Spare shop ledgers | Purchases, payments and balance for each shop | `suppliers` | Go-live |
| Unassigned spares | Parts bought ahead, moved onto a car later | `suppliers` | Go-live |
| Shop discounts | A shop's discount, recorded properly | `suppliers` | Go-live |
| Printed shop statement | One shop's purchases and payments, on paper | `suppliers` | Go-live |

## Supplies shops and stock

| Module | What it does | App | When |
|---|---|---|---|
| Supplies shop ledgers | Bills, payments and balance; the oldest bill paid first | `suppliers` | Go-live |
| Shop catalogue | What each shop sells, and which shops sell a product | `suppliers` | Go-live |
| Restock bills | A supplier's bill puts the stock on the shelf, priced as billed | `suppliers` | Go-live |
| Stock list and low stock | Products, categories, low stock, stock history, use by mechanic | `inventory` | Go-live |
| Stock movement | Stock moves as job cards use parts and bills come in, through explicit service calls | `inventory` | Go-live |
| Stock costing | Each part costed at what was really paid, bill by bill | `inventory` | Go-live |
| **Product fits** (new in v2) | One more box on Add product: Fits, the chassis codes a product fits, like B9 or F30 F31. Empty means any car, as for oils and fluids. On a job card, the product search shows the car's own parts first: those used on this car before, those for its chassis code, and those for any car. Parts for other cars wait under one line and never mix in, so a wrong Fits never loses a part. Every typed word counts, in any order. The bill still names the category | `inventory`, `suppliers`, `jobs` | Go-live |

## Go-live tools

| Module | What it does | App | When |
|---|---|---|---|
| Old bills | Earlier bills typed in, so each car's history is complete | `onboarding` | Go-live |
| Fill old bills from PDF | The bill's own PDF fills in the form | `onboarding` | Go-live |
| Opening stock and balances | The starting position, locked once it matches the books | `onboarding` | Go-live |

## Staff, rent and owners

| Module | What it does | App | When |
|---|---|---|---|
| Staff list | The people who work in the workshop, with their designation; a job card's lead mechanic is picked from it; someone who leaves is turned off, never deleted | `staff` | Go-live |
| **Attendance** (new in v2) | Each working day, Office or an owner marks every staff member who is turned on: Present, Half day or Absent. The page starts with everyone Present, and its Save button says the day and the count, like Save Friday: 6 present, 1 absent. A working day nobody saved is Not marked, never present: a card lists each one, oldest first, until it is marked or made a paid holiday, and the month's salary cannot be settled while one is left. Today's card shows at the top of the page, never as a pop-up: to Office from 2 pm, to owners from 6 pm. The owners set the weekly off days once, and a change starts on the date they pick. A paid holiday has its name, like Eid ul-Fitr, and nobody loses pay; every other day, an unpaid closure too, is marked as usual. For the salary, Absent is one leave day and Half day half of one. Floor never sees it. A change after saving is kept in the change history. It starts on the 1st of a month, with the old book kept for that first month | `staff` | After |
| **OT** (new in v2) | Extra pay for staying late, or for work on a weekly off or a paid holiday, each with its day, a note and its amount. On the floor tablet, Floor asks for OT with no amount, and sees each request as Waiting, Accepted or Declined. Office or an owner accepts it with the amount, or declines it, and can also add OT directly. Each request shows what that day was, so a wrong one is easy to see. The month's salary cannot be settled while one of its requests waits. It replaces v1's one OT amount typed for the month. It is a new page for Floor, so ROLE-18 (`docs/rules/roles.md`) gets a line when it is built | `staff` | After |
| Monthly salary | Each leave day takes off one day's pay, the salary divided by 30. Leave days come from Attendance and the month's OT from OT, so nothing is counted by hand at month end. The month's advances are taken off. A settled month locks, with its attendance and OT. A staff member who joins or leaves in a month needs a joining date, which the Staff list does not keep yet | `staff` | After |
| Salary advances | Given any day, taken off at settlement | `staff` | After |
| Rent | How much to hand over today, and every month's position | `finance` | After |
| Owner withdrawals | What each owner took, never counted as an expense | `finance` | After |

## Owner analysis

| Module | What it does | App | When |
|---|---|---|---|
| Overview | An owner's first page: cars on the floor, money and what needs a look today, each number opening its page. It only reads, with no table of its own. Owners' tabs become Overview, Work (the live board), Completed, Alerts and Manage, and the Live tab becomes a tile. First in line after go-live; if the client wants it on day one, it is built last in Phase 6 | `reports` | After |
| Profit | Turnover, expenses and what earned the profit, for any period | `reports` | After |
| Cash and position | Cash in and out; who owes what; stock on the shelf | `reports` | After |
| Deep analysis | Mechanics, parts, stock, cars, fleet, shops and more | `reports` | After |

## Car records

| Module | What it does | App | When |
|---|---|---|---|
| Car profiles | Visits, billed, paid, still owed; every bill in one PDF; the owners' figures (cost and gross profit) in a closed part that opens with a tap, so the page can be shown to a customer; a Copy button for the VIN; Change plate, with Known plate's rules (`docs/rules/known-plate.md`) | `vehicles` | After |
| **Customer profile** (new in v2) | For owners: one customer's cars, visits, billed and discounts, and the first and last visit; the top customers for a period. A customer is a name and a number together (ADR-0030). An owner can join two records of one person, so the page shows them as one person with both numbers; a join changes no visit and no bill, can be undone, and never happens by itself | `vehicles`, `reports` | After |
| Service history sheet | Every visit, and how long each part lasted | `vehicles` | After |
| Service rules and reminders | The workshop's own rules (a service every so many km or days, per model if needed); shows when a service is due | `vehicles` | After |
| Customer consent | Records whether the customer agreed to messages and to AI use | `vehicles` | After |

## More tools

| Module | What it does | App | When |
|---|---|---|---|
| Warranty claims | Claim a failed part from its original bill; track the shop's answer | `jobs` | After |
| Estimates | Quotations on the letterhead, with past prices as a hint | `jobs` | After |
| Photos | Car and part photos from the camera, stored in the cloud; one photo, chosen with a tap, is the car's picture, shown small on its job card and its page | `photos` | After |

## New after go-live

| Module | What it does | App | When |
|---|---|---|---|
| GST invoicing | Tax invoices, only for a workshop with a valid GSTIN | `billing` | After |
| WhatsApp messages | Estimates, bills, "car ready" and service reminders | `notifications` | After |
| Customer history page | A car's service history for its owner, opened from a branded NFC card | `vehicles` | After |
| Mechanic guide | A help page for the floor team | `jobs` | After |
| Branch screens | Switching branch, stock transfers, combined reports, members limited to some branches, and the history switch per branch, when a workshop's second place is real (ADR-0028) | `workshops`, each app | After |

## AI assistant (ADR-0008)

The assistant never calculates. It calls tested, read-only functions and
explains the result in plain words, in English or Malayalam. Every question
is logged, with a limit per question and a monthly limit per workshop.

| Module | What it does | App | When |
|---|---|---|---|
| Owner and office assistant | Answers questions about the workshop's own data; sees only what the role allows | `assistant` | After |
| Customer assistant | On the customer history page: explains one car's service status and offers a booking or a call | `assistant` | After |
| Bill from a photo | A photo of a supplier's bill fills a draft restock bill; Office checks it and saves | `assistant` | After |
| Daily summary | A short daily message for the owners: cars waiting for parts, cash, big discounts | `assistant` | After |
| Voice input | Speak a concern in Malayalam; it fills the line on the job card | `assistant` | After |
| Copy car details for AI | A car's brand, model, chassis code, kilometres, concerns, work done and parts, as text to paste into a person's own AI app, so it costs no AI fee. A fixed list of fields, never name, phone, plate, VIN, price or typed notes; a box shows the text before Copy. Legal advice confirms it is not personal data | `jobs` | After (client confirms) |

---

## SaaS: built when a second workshop wants the system

Everything these modules need in the data is already in **Foundation** above,
so adding them changes no existing table.

| Module | What it does | When |
|---|---|---|
| Self sign-up and trial | A workshop signs up and tries the system | SaaS |
| Subscriptions and payments | Plans, invoices for the subscription, a payment gateway. Paid every month on the start date (start 1 January, next due 1 February); 5 more days with a warning; from the 6th day (6 February) the workshop is blocked until it pays. The details are settled when it is built | SaaS |
| Platform console | The company's view: workshops, plans, payments, suspension | SaaS |
| Support access | Logged, time-limited access to a workshop, with its consent | SaaS |
| Sales and partner accounts | Leads, a demo workshop with fake data, referral tracking | SaaS |
| Plans and limits | Which modules each plan includes; user and branch limits per plan (the switches are in Foundation) | SaaS |
| More roles | Main Manager, Branch Owner, Service Advisor, Floor Supervisor, Parts Manager, a read-only Accountant and a read-only Viewer, each only when a real workshop asks (ADR-0026). Each needs one small migration for the role check and changes no record. A read-only role also needs one check in the guard: any save needs one more permission, which it does not have | SaaS |
| One labour charge | For a workshop that quotes one figure for all the work: one labour box in place of Job amounts, chosen once per workshop. Never a typed labour charge beside job amounts. A job card keeps the way it started with, so the choice never changes an open card or an old bill. Until then, such a workshop types its figure on one job | SaaS |
| Pay later | For a workshop whose customers pay part of a bill later: the rest is still owed, not a discount, and shows in Pending bills. The bill already keeps its discount as its own amount, so this changes no record | SaaS |
| Bill designs | A standard bill design for every new workshop, made its own by its logo, details and one colour from a short list; 3 or 4 ready designs only if workshops ask. Never a one-off design for one workshop, and never one a workshop uploads. The first client's design is used only for that client (ADR-0032) | SaaS |
| Several workshops per account | One sign-in for a person who works in more than one workshop, with a workshop picker | SaaS |
| Export and exit | A workshop's data exported, then deleted when it leaves | SaaS |
| Terms and privacy | Terms of service; privacy policy under India's DPDP Act | SaaS |
| Setup wizard and help | First-day setup and help pages | SaaS |
| Old data import | A workshop's old data from Excel, Tally or another system, read into one standard format; checked, shown as a preview, saved as a batch that can be undone (`docs/ARCHITECTURE.md`, open decision 9) | SaaS |

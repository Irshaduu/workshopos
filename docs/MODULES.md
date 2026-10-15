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
| Sign-in and password reset | Lockout after repeated wrong tries; reset code by email | `accounts` | Go-live |
| Roles | Owner, Office, Floor; each sees only what it needs (ADR-0007) | `accounts` | Go-live |
| Staff logins and devices | Staff list, staff logins, signed-in devices, remote sign-out | `accounts` | Go-live |
| Owner alerts | Push alerts to the owners' phones, and an alert feed | `notifications` | Go-live |
| Change history | Every deleted, edited and back-dated entry, month by month | `audit` | Go-live |
| Master lists | Brands, models, parts and concerns, with rename and merge | `vehicles`, `jobs` | Go-live |
| Confirmations and sounds | A clear question before anything important; a sound for each result | `core` | Go-live |
| Backups and money checks | Database copies; every typed amount checked before saving | `core` | Go-live |
| System guide and map | A tour of every section | to decide | After |
| **Workshop and branches** (new in v2) | The business and its locations (ADR-0006) | `workshops` | Go-live |
| **Workshop profile** (new in v2) | Logo, name, address, GSTIN, UPI QR, used by every printed document | `workshops` | Go-live |
| **Workshop settings** (new in v2) | Discount limit, edit window, back-date limit, markup; bill-number series per branch | `workshops` | Go-live |
| **Workshop status** (new in v2) | Active or suspended. A suspended workshop cannot sign in | `workshops` | Go-live |
| **Create a workshop** (new in v2) | One service creates a workshop, its first branch and its owner | `workshops` | Go-live |
| **Platform accounts** (new in v2) | The company's own staff, kept apart from workshop members (ADR-0007) | `accounts` | Go-live |
| **Module switches** (new in v2) | Each workshop turns modules on or off; off hides, never deletes (ADR-0011) | `workshops` | Go-live |

## Job cards and the floor

| Module | What it does | App | When |
|---|---|---|---|
| Job card | Car, concerns, jobs and one labour charge; locked once settled | `jobs` | Go-live |
| Parts on the job card | Shop parts and shelf stock kept apart; ordered, received, expected | `jobs` | Go-live |
| Known plate | A known number plate fills make, model, chassis code and VIN | `vehicles` | Go-live |
| Suggestions as you type | Car, part and concern names; jobs suggested from the card's parts | `jobs` | Go-live |
| Suggested price and markup | Customer price suggested from cost, with a markup badge | `jobs` | Go-live |
| Parts transport | Courier and parcel costs, counted in profit | `jobs` | Go-live |
| Live board | Every car in the workshop, filtered by mechanic | `jobs` | Go-live |
| Live report | Unfilled bills, parts on the way, each mechanic's open work | `reports` | Go-live |
| Job card view | One read-only page for each car | `jobs` | Go-live |
| Completed list | Cars ready to bill, with undo | `jobs` | Go-live |
| Ready-date estimate | An expected ready date, from parts on the way and each shop's past delivery times; flags parts not ordered yet | `jobs` | After |

## Appointments

| Module | What it does | App | When |
|---|---|---|---|
| Appointments | Book a date for a car; see how full each day is; suggest free dates | `jobs` | After (client confirms) |

## Bills and cash

| Module | What it does | App | When |
|---|---|---|---|
| Printed bill | A4 on the workshop's letterhead; PDF named after the car; WhatsApp button | `billing` | Go-live |
| Settle bill | Shows anything still unfilled before the bill is settled | `billing` | Go-live |
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

## Go-live tools

| Module | What it does | App | When |
|---|---|---|---|
| Old bills | Earlier bills typed in, so each car's history is complete | `onboarding` | Go-live |
| Fill old bills from PDF | The bill's own PDF fills in the form | `onboarding` | Go-live |
| Opening stock and balances | The starting position, locked once it matches the books | `onboarding` | Go-live |

## Staff, rent and owners

| Module | What it does | App | When |
|---|---|---|---|
| Monthly salary | Leave and overtime; a settled month locks | `staff` | After |
| Salary advances | Given any day, taken off at settlement | `staff` | After |
| Rent | How much to hand over today, and every month's position | `finance` | After |
| Owner withdrawals | What each owner took, never counted as an expense | `finance` | After |

## Owner analysis

| Module | What it does | App | When |
|---|---|---|---|
| Profit | Turnover, expenses and what earned the profit, for any period | `reports` | After |
| Cash and position | Cash in and out; who owes what; stock on the shelf | `reports` | After |
| Deep analysis | Mechanics, parts, stock, cars, fleet, shops and more | `reports` | After |

## Car records

| Module | What it does | App | When |
|---|---|---|---|
| Car profiles | Visits, billed, paid, still owed; every bill in one PDF | `vehicles` | After |
| Service history sheet | Every visit, and how long each part lasted | `vehicles` | After |
| Service rules and reminders | The workshop's own rules (a service every so many km or days, per model if needed); shows when a service is due | `vehicles` | After |
| Customer consent | Records whether the customer agreed to messages and to AI use | `vehicles` | After |

## More tools

| Module | What it does | App | When |
|---|---|---|---|
| Warranty claims | Claim a failed part from its original bill; track the shop's answer | `jobs` | After |
| Estimates | Quotations on the letterhead, with past prices as a hint | `jobs` | After |
| Photos | Car and part photos from the camera, stored in the cloud | `photos` | After |

## New after go-live

| Module | What it does | App | When |
|---|---|---|---|
| GST invoicing | Tax invoices, only for a workshop with a valid GSTIN | `billing` | After |
| WhatsApp messages | Estimates, bills, "car ready" and service reminders | `notifications` | After |
| Customer history page | A car's service history for its owner, opened from a branded NFC card | `vehicles` | After |
| Mechanic guide | A help page for the floor team | `jobs` | After |

## AI assistant (ADR-0008)

The assistant never calculates. It calls tested, read-only functions and
explains the result in plain words, in English or Malayalam.

| Module | What it does | App | When |
|---|---|---|---|
| Owner and office assistant | Answers questions about the workshop's own data; sees only what the role allows | `assistant` | After |
| Customer assistant | On the customer history page: explains one car's service status and offers a booking or a call | `assistant` | After |
| Bill from a photo | A photo of a supplier's bill fills a draft restock bill; Office checks it and saves | `assistant` | After |
| Daily summary | A short daily message for the owners: cars waiting for parts, cash, big discounts | `assistant` | After |
| Voice input | Speak a concern in Malayalam; it fills the line on the job card | `assistant` | After |

---

## SaaS: built when a second workshop wants the system

Everything these modules need in the data is already in **Foundation** above,
so adding them changes no existing table.

| Module | What it does | When |
|---|---|---|
| Self sign-up and trial | A workshop signs up and tries the system | SaaS |
| Subscriptions and payments | Plans, invoices for the subscription, a payment gateway | SaaS |
| Platform console | The company's view: workshops, plans, payments, suspension | SaaS |
| Support access | Logged, time-limited access to a workshop, with its consent | SaaS |
| Sales and partner accounts | Leads, a demo workshop with fake data, referral tracking | SaaS |
| Plans and limits | Which modules each plan includes; user and branch limits per plan (the switches are in Foundation) | SaaS |
| Branch screens | Switching branch, stock transfers, combined reports, when a workshop with more than one branch joins | SaaS |
| Export and exit | A workshop's data exported, then deleted when it leaves | SaaS |
| Terms and privacy | Terms of service; privacy policy under India's DPDP Act | SaaS |
| Setup wizard and help | First-day setup and help pages | SaaS |

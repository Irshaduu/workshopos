# Rules: roles

The rules of the Roles module (`docs/MODULES.md`), taken from v1 and
checked in v1's code. Why each choice was made: ADR-0026. Words:
`docs/GLOSSARY.md`. The code: `apps/accounts/`, and each app's own list of
permissions.

- Each rule has an ID. A test names the ID of the rule it protects.
- An ID never changes. A new rule takes the next free number.
- Each rule says where it comes from: **v1** (kept as it was), **v1,
  changed** (and what changed), or **new** (v2 only).
- Every rule is built in Slice 1, unless it says when.

## The roles

- **ROLE-1** A workshop has three roles: Owner, Office and Floor. They are
  fixed in the code. A workshop never makes its own roles, and never
  changes what a role may do. *v1, changed: v1 kept the roles as database
  groups, and a copied database could leave a group empty.*
- **ROLE-2** Each account has one role, in one workshop, from its
  membership (ADR-0007). A shared login, like the one on the floor tablet,
  is one account with one role. *v1.*
- **ROLE-3** Who did a job comes from the mechanic picked on the job card,
  never from the login, so one shared Floor login works for every
  mechanic. The change history then says only "Floor". *v1:
  `JobCard.lead_mechanic`. Built with the job card.*
- **ROLE-4** Platform staff and superusers are never members, so no role
  lets them into a workshop's pages. Being staff never means a role. *v1,
  changed: v1's owners were superusers, and a superuser passed every
  check.*
- **ROLE-5** A new role, like a read-only Accountant or a Storekeeper, is
  added by listing what it may do, in the code, without changing any page.
  *New.*

## How a page is guarded

- **ROLE-6** Every page has one mark that names its module and the
  permission it needs, and one check reads both. *New (`docs/PLAN.md`).*
- **ROLE-7** No page, menu, form or template checks a role by its name. It
  asks for a permission, like "see prices". *v1, changed: v1 had three
  checks named after roles (`owner_required`, `office_required`,
  `staff_required`), and its templates asked "is this an Owner?", so a new
  role meant changing pages.*
- **ROLE-8** A page with no mark is refused to everyone, so a forgotten
  mark fails safe. The sign-in steps and signing out name their module
  and need no permission. *New.*
- **ROLE-9** A visitor who is not signed in goes to the sign-in page, and
  back to the page after (SIGN-38). A signed-in person whose role may not
  open the page gets "Not open to your role" (403), with none of the
  page's data, never the sign-in page. *v1: `_role_required`. v1 first
  sent them to sign in while they were signed in, which looked like being
  signed out.*
- **ROLE-10** A record of another workshop is never found: its page
  answers "Not found" (404), the same as a record that does not exist, so
  it never tells that the record is there. *New (ADR-0023).*
- **ROLE-11** A page may ask what a person may do as often as it likes:
  the role is read once per request, so asking again costs no query. *v1:
  `role_names`. Measured in v1: the job card form asked 19 times, and the
  role question was 32 of its 48 queries, until it was read once.*
- **ROLE-12** What a page lets in and what the screen offers come from one
  answer. A tab, a menu item, a button or a link to a page shows only to
  the roles that page lets in. A door a role can see but not open is worse
  than no door. *v1: "a template gate mirrors its view's check". Before
  that rule, v1's Control Hub showed in the menu to owners only, but Office
  could open it by its address.*
- **ROLE-13** A field a role may not see on any screen is a field it may
  not send from any screen: its form leaves the field out, never hides it.
  *v1: `_floor_locked_data`, after a Floor login sent a price of 1 and
  turned a 5,000 rupee bill into 1 rupee. Built with the first form per
  role (the job card), as `docs/PLAN.md` says.*

## What each role may do

v1's split, the reference for every module's pages. Each module's loop
checks its own line again, and its pages' marks follow it.

- **ROLE-14** Floor sees the whole floor: every car on the live board,
  with a chip for each mechanic. *v1: `home`. ADR-0007 said "its own
  jobs"; ADR-0026 replaces that line.*
- **ROLE-15** Floor makes and changes job cards, looks up a known plate,
  puts a card on hold, marks it completed, and adds photos. It may not
  undo a completion: Office does, because an undo can put a second open
  job card on the floor for one plate. *v1: `undo_completed`.*
- **ROLE-16** Floor never sees a price: no cost, customer price, transport
  cost, markup or suggested price, on any screen. The server keeps to it.
  *v1: `PRICE_FIELDS`, `spare_price_hint`.*
- **ROLE-17** Floor never sees who the customer is: no name and no phone.
  The job card's note about the car is open to every role. Its box is
  called "Customer & Notes" for Office and Owners, and "Workshop Note" for
  Floor. *v1: `OFFICE_ONLY_CARD_FIELDS`.*
- **ROLE-18** Floor's other pages: the stock list, low stock, stock
  history and use by mechanic, all read only; Unassigned Spares, where it
  adds a part with no price; and the warranty card of a claim Office has
  started. Floor opens no other page about stock, shops or money. *v1.*
- **ROLE-19** Office does the daily work and the money: all that Floor
  does, and also bills and settling, the completed list with its undo, the
  live report, the read-only job card, pending and paid bills, the
  cashbook, rent deposits, salary and advances, fleet accounts, estimates,
  car profiles, warranty claims, master lists, old bills, stock and its
  categories, supplies shops with their restock bills, and spare shops.
  *v1: `office_required`.*
- **ROLE-20** Office sees the paid bills of the last 7 days only; owners
  see every bill. The server keeps to it, not a hidden filter. *v1:
  `paid_bills_list`.*
- **ROLE-21** Owners may do everything in the workshop. Only owners open:
  profit and deep analysis, owner withdrawals, the change history, the
  discount audit, opening stock and opening balances, the go-live lock,
  staff logins and the staff list, setting the rent, deleting a salary
  payment, the alerts, and the guide. *v1: `owner_required`.*
- **ROLE-22** Only owners get alerts, so only owners see the bell. *v1.
  Built with the bell (Phase 6).*

## The tab bar

- **ROLE-23** Every page of the app has one tab bar and one menu. There is
  never a second menu: a new page goes into the menu, in its section. The
  sign-in steps, the sign-out card and the state pages (not allowed, not
  found, server error) have neither. *v1.*
- **ROLE-24** Owners and Office have five tabs: the home tab, Completed,
  Live, Alerts (owners only) and Manage. Floor has four: the home tab,
  New, Inventory and Menu. *v1.*
- **ROLE-25** The home tab is named after the role: Owner, Office or
  Floor. It opens the live board. *v1, changed: v1 named the owner's tab
  "Admin". One name per thing (`docs/GLOSSARY.md`), and "admin" is
  Django's admin, which owners never use.*
- **ROLE-26** Owners and Office have no New tab: they start a job card
  from the New button on the live board. Floor makes most job cards, so
  its New is on the bar. *v1.*
- **ROLE-27** On a phone, 640 pixels wide or less, the same bar sits at
  the bottom, floating, where a thumb reaches. On a tablet and a laptop it
  sits at the top. *v1.*
- **ROLE-28** Exactly one tab is lit on every page: the page's own tab, or
  Manage (Menu for Floor) for a page reached from the menu. Floor's stock
  pages light Inventory, not Menu. *v1: `ExactlyOneTabIsLitTests`.*
- **ROLE-29** Every tab has its word. On a tablet and a laptop the bell
  shows only its icon, with its name for a screen reader; on a phone it
  shows its word, Alerts. *v1.*
- **ROLE-30** The bell's count stops at 99+. *v1. Built with the bell
  (Phase 6).*
- **ROLE-31** The bar has no Back button: each page has its own back
  control (`docs/DESIGN.md`). *v1, a decision of 2026-09-05: a sixth tab
  made every tab on a phone 17 percent narrower.*
- **ROLE-32** A tab or a menu item comes with its page. A page that is not
  built yet has neither. *New.*

## The menu

- **ROLE-33** Manage, or Menu for Floor, opens the menu from the right.
  On a phone it covers about 70 percent of the width, so the page still
  shows beside it. A tap beside it, its close button, or the Escape key
  closes it. *v1.*
- **ROLE-34** The menu's head shows who is signed in: their name, and
  their role, like "Owner account". A tap on it opens two rows: Sounds on
  or off, for this device only, and Sign out. *v1.*
- **ROLE-35** Sign out in the menu opens the confirmation card (SIGN-40).
  It is the app's one Sign out control. *v1: `LogoutConfirmationTests`.*
- **ROLE-36** For Office and Owners the menu has these sections, in this
  order. A semicolon marks where a thin line splits a section into its
  smaller groups.
  - Money: General Cashbook, Deposit & Rent; Pending Bills, Paid Bills;
    Salary & Advance, Owner Withdrawals
  - Stock & Suppliers: Inventory; Supplies Shops, Spare Shops
  - Records: Car Profiles, Warranty; Estimates, Master Data, Legacy Data,
    Change History
  - Administration: Control Hub
  - Insights: Analysis & Reports
  - Guide: About

  For Floor: Stock (Low Stock, Stock History) and Spares (Unassigned
  Spares). Each item shows only to the roles its page lets in (ROLE-12),
  so Office never sees the owners' items. *v1.*
- **ROLE-37** The page you are on is lit in the menu too. *v1.*
- **ROLE-38** The words of a page not built yet are settled in its own
  module's loop, in `docs/GLOSSARY.md` first. Until then the menu keeps
  v1's words. *New.*

## Left out from v1

Why each one: ADR-0026.

- Roles as database groups, and owners as superusers: the roles are fixed
  in the code, and platform staff are never members (ROLE-1, ROLE-4).
- The Login tab the bar showed to a visitor who was not signed in: every
  page of the app needs sign-in, and the sign-in steps show no bar.
- A colour for each menu item, and for each role in the menu's head (red
  for an owner, amber for Office): in v2 a colour means a status, never
  decoration (`docs/DESIGN.md`). The shapes stay v1's, in one colour.
- On a phone, the lit tab gliding to the next one, and the faint mark on
  a tapped tab while its page loads: polish, for after go-live if the
  owners miss it. The progress bar at the top already shows that the page
  is on its way (`docs/DESIGN.md`).

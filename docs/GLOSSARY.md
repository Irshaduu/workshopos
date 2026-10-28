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
| Membership | `Membership` | | An account's place in a workshop, with its role |
| Role | `Role` | group | What a member may do: Owner, Office or Floor |
| Sign in | `sign_in`, the page `sign-in/` | log in, login (as a verb) | Start using the system: an owner types the email and the code sent to it; Office and Floor type a username and the password |
| Sign out | `sign_out`, the page `sign-out/` | log out, logout | End the session on this device |
| Username | `username` | identifier | What Office and Floor type to sign in. It starts with the workshop's short code and a dot, like `ab.floor` |
| Login name | `login_name` | | The part of a username after the short code and its dot: `floor` in `ab.floor`. Small letters and digits |
| Short code | `short_code` | | A workshop's 2 to 8 small letters or digits, set once and unique on the server. Every username of the workshop starts with it |
| Locked | `minutes_locked()` | | An account with a password that cannot sign in for 15 minutes, after 5 wrong passwords in a row |
| Unlock | `unlock()` | | An owner lets a locked Office or Floor account sign in again at once |
| Sign-in code | `SignInCode` | OTP, reset code | 6 digits emailed to an owner, who types them to sign in. It works once, for 10 minutes, in the browser that asked for it |
| Fleet account | `FleetAccount` | bulk payer | A company that sends many cars and pays for them together |
| Fleet payment | `FleetPayment` | bulk payment | One payment from a fleet account that settles many of its bills |
| Staff member | `StaffMember` | mechanic, for everyone | A person who works at the workshop. Mechanic is one of the designations |
| Designation | `designation` | role, for a staff member | A staff member's job, like Mechanic or Helper. A member's Owner, Office or Floor is their role |
| Supplier | `suppliers` (the app) | | Any shop we buy from: a spare shop or a supplies shop |
| Spare shop | `SpareShop` | | A shop we buy a part from for one job |
| Supplies shop | `SuppliesShop` | supplier shop | A shop we buy stock from, for the shelf |
| Product | `Product` | item | Something the workshop keeps in stock |

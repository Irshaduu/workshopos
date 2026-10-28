# Rules: sign-in

The rules of the Sign-in module (`docs/MODULES.md`), taken from v1 and
checked in v1's code. Why each choice was made: ADR-0025. Words:
`docs/GLOSSARY.md`. The code: `apps/accounts/`.

- Each rule has an ID. A test names the ID of the rule it protects.
- An ID never changes. A new rule takes the next free number.
- Each rule says where it comes from: **v1** (kept as it was), **v1,
  changed** (and what changed), or **new** (v2 only).
- Every rule is built in Slice 1, unless it says when.

## Who signs in, and how

- **SIGN-1** One sign-in page for every role. It names no role and links
  to no other way in. *v1: `login_view`, "the one door".*
- **SIGN-2** The page asks first for an email or a username. An email goes
  on to a code; a username goes on to a password. *New.*
- **SIGN-3** An owner signs in with their email and a 6-digit code sent to
  it. An owner has no password. *v1, changed: v1 owners had a password,
  and an emailed code only reset it. v1's owners already used the code
  instead: they asked v1 to hide its Change password link.*
- **SIGN-4** Every owner has an email. A workshop cannot get an owner
  without one. *v1, changed: an owner with no email signed in with a
  username.*
- **SIGN-5** An owner's username never signs them in, and a try with it
  does not count towards a lockout. *v1: `resolve_login_identifier`, and
  its tests.*
- **SIGN-6** Office and Floor sign in with their username and password,
  and have no email. An owner sets their passwords (Staff logins, Phase
  6). *v1, changed: v1 also took a mobile number, which was not in use.*
- **SIGN-7** Every username starts with its workshop's short code and a
  dot, like `ab.floor`. So it stays unique on a shared server, and when a
  workshop moves to one. *New.*
- **SIGN-8** A short code is 2 to 8 small letters or digits, set when the
  workshop is made and never changed. No two workshops on a server share
  one. *New.*
- **SIGN-9** Usernames are unique on the server whatever their capitals:
  `AB.Floor` and `ab.floor` are the same username. Emails too. PostgreSQL
  refuses a second one. *v1, changed: v1 checked this only in its forms.*
- **SIGN-10** Capitals never matter when signing in: `AB.FLOOR` finds
  `ab.floor`, and an email in any capitals finds its owner. *v1, changed:
  v1 matched usernames exactly, so a wrong capital was refused.*
- **SIGN-11** A wrong username, an owner's username, a turned-off account
  and a wrong password all get the same answer: "Wrong username or
  password." *v1: "Invalid credentials."*
- **SIGN-12** Someone already signed in who opens the sign-in page goes to
  the home page. *v1.*
- **SIGN-13** After signing in, a person goes to the page they first asked
  for, if it is on this site; otherwise to the home page. *v1:
  `_safe_next`.*
- **SIGN-14** A button shows it is busy after the first tap, and a second
  tap sends nothing. So a double tap never spends two tries, and never
  sends two codes. *v1: the guard in `base_auth.html`.*

## The owner's code

- **SIGN-15** The email step gives one answer, whatever was typed: "If this
  email belongs to an owner, a 6-digit code is on its way. You can ask for
  a new code once a minute." So this step never tells who has an account,
  unless the email cannot be sent (SIGN-25). A turned-off owner gets no
  code. *v1: the first step of its reset.*
- **SIGN-16** The code has 6 digits. It works once, for 10 minutes, and
  only in the browser that asked for it. *v1: `PasswordResetOTP`. Why a
  code and not a link: ADR-0025.*
- **SIGN-17** The code is in the email's subject line, so the phone's
  banner shows it without opening the mail. *v1.*
- **SIGN-18** The email names the owner's own workshop, and says: never
  share this code; nobody will ask you for it. *v1, changed: v1 used one
  name for the whole server, and had no warning against a trick call.*
- **SIGN-19** A new code ends the one before. *v1.*
- **SIGN-20** An account gets at most one code a minute, and 3 an hour,
  counted in the database. *v1.*
- **SIGN-21** When this browser has asked too often, the page says so, and
  when it can ask again. It counts only this browser, never the account,
  so it cannot tell who has an account. *v1.*
- **SIGN-22** Five wrong codes end the code. Each wrong code says how many
  tries are left. *v1.*
- **SIGN-23** A wrong code stays in its box, so one wrong digit can be
  fixed. *v1.*
- **SIGN-24** The code is kept only as a hash made with the server's secret
  key, never as the code itself. *v1, changed: v1 kept a plain hash, and a
  6-digit code can be found from a plain hash in a few seconds.*
- **SIGN-25** If the email cannot be sent, the code is deleted, the page
  says the email did not go out, and the try counts towards no limit.
  *v1.*
- **SIGN-26** The code step cannot be opened without the email step. *v1.*
- **SIGN-27** The right code signs the owner in and ends every code of the
  account. *v1, changed: v1's code only let the owner set a new password.*
- **SIGN-28** When email fails, the developer can make a code on the
  server, for an owner who has started signing in, and give it to them by
  phone. *New.*

## Lockout

For a password: Office, Floor, and the platform's own staff.

- **SIGN-29** Five wrong passwords in a row lock the account for 15
  minutes from the last one. *v1: `AccountLockout`.*
- **SIGN-30** A wrong password more than 15 minutes after the one before
  starts the count again at one. *v1, changed: v1 kept old wrong tries
  until a right password, so a few slips over several weeks could lock
  the shared Floor login.*
- **SIGN-31** The count is kept per account, in the database. One person's
  wrong tries never lock anyone else, though the whole workshop uses one
  internet connection. *v1.*
- **SIGN-32** A locked account is refused even with the right password.
  Its tries are not counted, so the lock never grows longer. *v1.*
- **SIGN-33** The page says the account is locked, and for how long: "Too
  many wrong passwords. Try again in 12 minutes." This tells a stranger
  that the account exists; v1 accepted that, so a locked person knows why.
  *v1.*
- **SIGN-34** The right password clears the count. *v1.*
- **SIGN-35** The lockout guards every way in that takes a password, the
  Django admin's sign-in page too. *New: in v1 no account could enter the
  admin.*

## Staying signed in

- **SIGN-36** A person stays signed in until 40 days after their last
  visit. Each visit starts the 40 days again. *v1: the owners' choice.*
- **SIGN-37** Closing the browser does not sign a person out. *v1.*
- **SIGN-38** A visitor who is not signed in, or whose session has ended,
  goes to the sign-in page, and back to the page after signing in. If they
  were saving something, the sign-in page says it was not saved. *v1, with
  v2's Session expired state (`docs/DESIGN.md`).*
- **SIGN-39** A request from inside a page (htmx) whose session has ended
  sends the whole page to the sign-in page, never just a part of it. *New
  (`docs/DESIGN.md`). Built with the first htmx call.*

## Signing out

- **SIGN-40** Signing out takes two taps: Sign out, then Yes on a
  confirmation card. One tap must never sign a mechanic out in the middle
  of a job card. *v1.*
- **SIGN-41** There is one Sign out button, and it sends a POST. Opening an
  address never signs anyone out. *v1.*
- **SIGN-42** Signing out works even when the workshop is suspended. *New
  (ADR-0023).*
- **SIGN-43** After signing out, the sign-in page shows. *v1.*

## Changing a login (Phase 6)

Built with the Staff logins page.

- **SIGN-44** An owner can unlock an Office or Floor account at once. The
  Unlock button shows only while the account is locked. *v1:
  `manage_unlock_account`.*
- **SIGN-45** An owner's email changes only after a code sent to the new
  email is typed in, and the old email gets a notice. The email is an
  owner's only key. *New.*
- **SIGN-46** A new password for an Office or Floor account signs that
  account out on every device. *v1 (Django's own check).*

## With the bell (Phase 6)

v1's alerts for this module, built with the bell (`notifications`). Each
is one call from a service built in Slice 1. An alert never goes to the
device that caused it.

- **SIGN-47** Every sign-in sends a push alert, "Owner signed in" or
  "Staff signed in", with the role and the device. It goes to the owners,
  and to the account's own other devices. *v1, changed: v1 never told the
  account itself. With codes, a stranger who reads an owner's email could
  sign in quietly; this alert is how the owner finds out.*
- **SIGN-48** An Office or Floor account that locks alerts the owners
  once, saying how the lock ends: by itself in 15 minutes, or with Unlock.
  *v1: `ACCOUNT_LOCKED`.*
- **SIGN-49** Three codes asked for in an hour, or a code guessed wrong 5
  times, alert the owners, at most once an hour each. *v1:
  `RESET_CODE_LIMIT`, `RESET_CODE_ATTEMPTS_SPENT`.*

## Left out from v1

Why each one: ADR-0025.

- Owner passwords, with v1's password reset and its Change password page:
  owners sign in with a code instead (SIGN-3).
- Signing in with a mobile number: not in use.
- An owner with no email signing in with a username: every owner has an
  email now (SIGN-4).
- The limit per internet address (20 wrong tries from one address lock
  that address for 15 minutes): decided in Phase 7, when the host is
  known.
- The old second sign-in address (`/admin-login/`): v2 has no old
  bookmarks to keep.
- The alert for a finished password reset: there is no reset.

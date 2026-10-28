# 0025: Sign-in: a code by email for owners, a password for Office and Floor

**Status:** Proposed (2026-10-28)

## Context

- Slice 1 starts with signing in. Its rules come from v1 and were approved
  on 2026-10-28: `docs/rules/sign-in.md`.
- In v1, owners had a password, and a 6-digit code sent by email reset it.
  The owners asked v1 to hide its Change password link, and used Forgot
  password instead.
- With a reset by email, the email is already the master key: whoever can
  read it can set a new password and sign in.
- People stay signed in for 40 days after their last visit (v1, the
  owners' choice). So an owner signs in again only on a new device, or
  after signing out.
- The Floor login is one shared login for all the mechanics, on the
  workshop's tablet. It has no person and no mailbox. Office works on one
  laptop. An owner sets both passwords (v1).
- Four ways for owners were compared:
  - a password, with a code by email to reset it (v1);
  - a code by email only, with no password;
  - a password and a code each time (two-factor): the strongest, but the
    password comes back, and its reset still goes through the email;
  - a code by SMS or WhatsApp, as many Indian apps do: each message costs
    money, SMS needs DLT registration, WhatsApp needs Meta's approval, and
    a swapped SIM can take an SMS code.
- A code, not a link: an app added to an iPhone's Home Screen keeps its
  cookies apart from Safari, so a link from the mail app signs in Safari,
  not the app (v1's reason). The owners use iPhones, mostly
  (`docs/DESIGN.md`).
- An email service can be down, slow, or put a code in spam. Django 6.1 can
  hold several named mailers (`MAILERS`) and send through a chosen one
  (`using=`), seen in its code on 2026-10-28.
- v1 wrote its own sign-in view. It found the account itself, then called
  Django's `authenticate()`. Django's `ModelBackend` looks an account up by
  its username, with exact capitals, so v1 had to pass an empty name when
  it refused an owner's username, or the owner would sign in by a back
  door.
- Django 6.1 already has most of what v1 rebuilt: `authenticate()` and
  `login()`, a check that a `next` address is on this site, a sign-out view
  that takes only a POST, a password check that takes the same time when
  no account was found, and a session that ends once its account's
  password changes.
- Every way in calls the same `authenticate()`: our pages, the Django
  admin's sign-in page and the tests. It asks each backend in
  `AUTHENTICATION_BACKENDS` in turn. A backend can refuse, but cannot say
  why.
- Django reports a wrong password only through a signal
  (`user_login_failed`). Our rules allow no business logic in signals
  (`CONTRIBUTING.md`). A library such as django-axes counts them through
  the same signals, and would be a new dependency.
- v1 kept its lockout count in a table of its own (`AccountLockout`), with
  a row made at an account's first wrong password.
- v1 also counted wrong passwords per internet address: 20 from one
  address blocked it for 15 minutes. v1 measured on its test host
  (2026-09-21) that the address Django saw was the host's proxy, so every
  visitor shared one count until that was fixed (AUD-0107). The real
  address depends on the host, which Phase 7 chooses.
- Two ways were compared to make a column unique whatever its capitals: a
  unique index on its small-letter form (`Lower()`), as branch names
  already have, or a case-insensitive collation made by a migration.

## Decision

- **Owners sign in with their email and a 6-digit code sent to it. Owners
  have no password.** Their first sign-in proves their email is right.
- **Office and Floor sign in with a username and a password**, set by an
  owner (Staff logins, Phase 6). A code would have nowhere to go for the
  shared Floor login, and the floor's daily work must never wait for an
  email.
- **One sign-in page, in steps:** first an email or a username. An email
  goes on to the code; a username to the password. Our own small views,
  built on Django's `authenticate()`, `login()` and its `next` check.
- **One authentication backend, in place of `ModelBackend`**
  (`apps/accounts/backends.py`), and the only one in
  `AUTHENTICATION_BACKENDS`, so every way in goes through it. It checks:
  - a username and a password, for an account that is not an owner. It
    refuses a locked account before it checks the password, uses Django's
    own password check, and counts a wrong password or clears the count by
    calling the services in `apps/accounts/services.py`;
  - an owner's code, for the account held in the browser's session.

  Capitals never matter, and an owner's username finds no one. The
  password step asks the same lock question first, only to say why
  (SIGN-33); both ask one selector.
- **The lockout count lives on the account:** two columns on `User`, the
  wrong passwords in a row and the time of the last one, changed in one
  transaction with the user's row locked, so two tries at the same moment
  count as two. The numbers (5 tries, 15 minutes) stay in the code, the
  same for every workshop, as in v1.
- **The codes:** a `SignInCode` model in `accounts` holds the code's hash,
  keyed with the server's secret key (Django's `salted_hmac`, compared with
  `constant_time_compare`), when it was made, when it ends, its tries, and
  when it was used. The limits are counted from its rows. The email is sent
  during the request, not as a background job, so the page can say at once
  when it did not go (SIGN-25). Its subject line holds the code; its text
  names the owner's workshop and says never to share the code.
- **A bad day for email:**
  - one good mail service (Phase 7), with the sending domain's SPF, DKIM
    and DMARC records, so codes land in the inbox, not in spam;
  - the 40-day session, so only an owner on a new device needs a code;
  - a command for the developer, on the server: it makes a code for an
    owner who has started signing in, to give to them by phone (SIGN-28);
  - a backup mail service later, as a second named mailer, for SaaS or if
    the first one fails us.
- **Unique whatever their capitals:** a `Lower()` unique constraint on the
  username, and one on the email when it is not empty, the same as branch
  names. Lookups ignore capitals.
- **The short code:** a new column, `Workshop.short_code`: 2 to 8 small
  letters or digits (a PostgreSQL check), unique on the server, given when
  the workshop is made and never changed (read-only in the admin).
- **`create_workshop()` makes the first owner's account itself:** the
  username is the short code, a dot and a name; the email is required;
  there is no password. So SIGN-4 and SIGN-7 hold from the first account,
  and every later service that makes an account checks them too.
- **Staying signed in:** Django's database sessions, for 40 days after the
  last visit (`SESSION_COOKIE_AGE`, with `SESSION_SAVE_EVERY_REQUEST` so
  each visit starts the 40 days again), not ended when the browser closes.
- **Platform staff** sign in at the Django admin's own page, with a username
  and a password, through the same backend. Their two-factor sign-in comes
  in Phase 7 (ADR-0007).
- **Not built now:**
  - a limit per internet address: decided in Phase 7, with the host's
    proxy measured, and needed before a second workshop shares a server;
  - Unlock, an owner's new email, and a new Office or Floor password: with
    the Staff logins page (Phase 6);
  - the alerts: with the bell (Phase 6);
  - codes by SMS or WhatsApp, a backup mail service, and passkeys (Face ID
    or a fingerprint): each later, with its own ADR, if it is needed.

## Consequences

- An owner has nothing to remember, and a guessed or reused password can
  never open an owner's account.
- Every owner sign-in on a new device needs email to work. The 40-day
  session and the developer's command cover a bad day.
- The email is an owner's only key. Each owner must use their own mailbox,
  never one that others can read; the developer checks this at setup
  (`RUNBOOK.md`, Phase 7). Someone who gets into an owner's email can sign
  in quietly. From Phase 6 the sign-in alert goes to the account's own
  other devices and to the other owners, so it shows.
- Someone who knows an owner's email can use up its codes for an hour, as
  with v1's reset. From Phase 6 the alert tells the owners.
- An owner who uses the shared Office laptop needs a new code each time.
- The sign-in page has two steps where v1 had one, so Office and Floor tap
  once more, but rarely.
- Every way in, now and later, is guarded by the same backend and lockout,
  with no second copy.
- Each signed-in request writes its session once more, to move its end
  date: the price of 40 days from the last visit.
- Ended sessions and old codes stay in the database until a scheduled
  clean-up deletes them (the background jobs ADR, Phase 6).
- On a shared server, guesses spread over many owners add up, so the limit
  per address is needed before a second workshop joins.
- `SignInCode` belongs to an account, not to a workshop, so it joins the
  user in the list of models that do not build on `WorkshopModel`
  (`tests/test_tenancy.py`).

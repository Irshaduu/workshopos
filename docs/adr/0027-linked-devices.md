# 0027: Linked devices: no passwords for workshop people

**Status:** Proposed (2026-11-04). Accepted when it is built and proved on
real devices.

## Context

- ADR-0025 gave Office and Floor a username and a password, set by an
  owner. Owners use their email and a code.
- Measured on 2026-11-04, on rows that were rolled back:
  - `authenticate()` with another workshop's username and the same password
    signs in to that workshop. On a shared server, two workshops with
    similar short codes and the same password are one typing slip apart.
  - Django's password checks refuse the worst passwords, but accept a
    common word with digits. v2 does not call them yet.
  - An account with no password opens its pages as usual.
  - Deleting a session's row signs that device out at its next request.
  - A visit after 39 idle days starts the 40 days again, and 40 idle days
    sign the device out (SIGN-36).
- A shared password stays known to anyone who has left, and works from any
  phone. The lockout allows 5 wrong tries in a row on an account, then 15
  minutes later 5 more.
- A person signs in again only on a new device or after 40 idle days, so a
  step that needs an owner is rare.
- Linking a new device from a trusted one is a known pattern. WhatsApp and
  Telegram do it from a phone, and Square's shop tills with a device code.
  RFC 8628 (the OAuth device flow) lists its checks: limit the tries, tell
  the person they are approving a device, and keep the code's life short.
- Its known attack is tricking the approver into approving a stranger's
  code (QRLjacking; WhatsApp Web was a named target).
- On iPhones, read in documents, not yet tried on a real device: the camera
  app opens Safari, not the installed app, and Safari has `BarcodeDetector`
  off by default. From iOS 17.2, Add to Home Screen copies cookies once;
  after that the two keep them apart (WebKit's post on Safari 17.2).
- Three ways were compared:
  - passwords with stricter checks: keeps every password problem;
  - a password, plus an owner's approval of each new device: keeps every
    password problem, needs push, and invites repeated requests until a
    busy owner taps Agree;
  - no passwords, and a trusted person links each new device.

## Decision

- **Owners keep their email and a code (ADR-0025). Every other role links a
  device.** Workshop people have no password and type no username.
- **The steps.** Every person in every workshop opens one address. A new
  device presses Link this device and shows a device code. An approver,
  already signed in, opens Link a device and types the code. The screen
  shows the waiting device and this workshop's logins. The approver picks
  one and agrees, and the device goes in by itself.
- **A device has no workshop until an approver says yes.** So a stranger
  opening the page can send no alert to anyone, and learns nothing about
  who has an account.
- **The device code:** 8 letters from 20, with no vowels and no look-alikes
  (RFC 8628's example). It ends after 10 minutes, limits its tries, and is
  kept only as a hash, like a sign-in code (SIGN-24). It only names a
  waiting device, so guessing one opens nothing. Only the browser that
  asked for it gets the session.
- **Who may link** is a permission (ADR-0026), owners first. A device can
  never link to an Owner login. Only owners link Main Manager and Branch
  Owner logins, and a Branch Owner links only its own branch's logins.
- **Against the wrong login.** Nothing is picked in advance. The role that
  sees least comes first, each row says what it can see, and the button
  says the choice in words, like "Link as Floor". The device then says what
  it became. The other owners get an alert (with the bell, Phase 6). Remove
  fixes a mistake in one tap.
- **Against a trick.** The screen asks the approver to agree only if they
  know this device, and names it by its system and browser, because a
  browser does not give the model.
- **Staying signed in** does not change: 40 days after the last visit
  (SIGN-36).
- **The list of devices:** owners see every signed-in device, with its
  login, its system and browser, and who linked it. Remove deletes its
  session. Floor's menu has no Sign out, because nobody on the floor could
  sign back in alone.
- **A bad day:** a command for the developer on the server, like SIGN-28.
- **A typed code first.** A QR code comes later, beside it, on the same
  backend, after a test on a real iPhone.
- **Platform staff** keep a password and the lockout at the Django admin's
  page, with two-factor sign-in in Phase 7 (ADR-0007), so the emergency
  door does not depend on email.
- **The short code stays** 2 to 8 small letters or digits (SIGN-8), because
  nobody types it now. It is widened only if a workshop's own address is
  wanted, which then only shows its name and logo (Phase 7).
- **How it is built:** a small model like `SignInCode`, a new path in
  `SignInBackend`, an approver's page, and a page that waits (htmx polling
  or a plain reload; SIGN-39 comes with it). The password page and its form
  go. One pull request, step 9 of the build order, so the browser tests
  cover the final page, with the second design of the sign-in page through
  the lab.
- **Proved on real devices before it merges:** an owner types the code in
  Safari, and in the installed app; a tablet links in Chrome, then
  installs; an iPhone links, then is added to the Home Screen; a device is
  still signed in after a week; Remove works from an iPhone.
- **If the trial hurts:** Office may link Floor devices. The last resort is
  the password path, back from git.

## Consequences

- Nothing to remember, and nothing a person who left still knows. A typing
  slip can never open another workshop.
- A new device needs an approver. An owner who is away can type a code that
  staff send by message. That is also the way a trick works, so the alert
  and Remove matter.
- Picking a login is the approver's choice, like handing over a key. The
  system can make a mistake hard, visible, small and quick to fix, but not
  impossible.
- Cleared browser data or a new tablet means linking again.
- An owner's unlocked phone can link devices, and their mailbox is the key
  to their account (ADR-0025). A stolen session lives as long as it is
  used, the price of no forced sign-out.
- `RUNBOOK.md` (Phase 7):
  - change the secret key only with `SECRET_KEY_FALLBACKS` (measured:
    without it, every device is signed out);
  - on a server move, keep the address, the key and the sessions, or every
    device links and installs again; so the address is chosen once, before
    go-live;
  - after a restore, check the list of devices, because a removed device
    comes back.
- When this ADR is accepted: ADR-0025's status line says its staff lines
  are replaced, and that pull request changes SIGN-1, 2, 6, 7, 10, 11, 44
  and 46, the lockout rules (platform staff only), ROLE-34 and ROLE-35, and
  the glossary's sign-in rows.

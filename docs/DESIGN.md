# Design

How screens look and behave. Read it before any UI work.
What is planned: `docs/PLAN.md`. Where the files live: `docs/ARCHITECTURE.md`.
How the UI lab works: `CONTRIBUTING.md`. Words on screen: `docs/GLOSSARY.md`.

CSS base: plain CSS with our own tokens, no framework (ADR-0017).

- Tokens: `static/css/tokens.css`, the only home of every colour and size.
- Components: `static/css/components.css`: card (with a status edge),
  button, field, status badge, chip, back control, payment row,
  confirmation card, list search, info button, and the screen states
  below. Each is v1's, fixed only where a rule breaks.
- Icons: Lucide, only the ones we use, in `static/icons/icons.svg`
  (ADR-0018). An icon never carries meaning alone. Icons go on section
  titles, on buttons, and on the few things that appear on many screens
  (the mechanic, photos, dates), always with the same icon. Never on
  every form label.
- See them all, in every state: `design/lab/system/`.

---

## Design principles

The aim: people are glad to open the system, understand each page at first
sight, and a new workshop is impressed in the demo. Premium comes from
polish, not decoration.

- **Calm and fast.** Every effect must help the task; if it only
  decorates, it goes.
- **One main thing per screen.** The most important number is the
  biggest thing on it.
- **Colour means status, never decoration.** Green is done or paid; an
  amount still owed is never green.
- **Motion only with a purpose:** CSS only, moving and fading only, and
  none when the device asks for less motion.
- **Delight at key moments:** a friendly empty state, a clear success with
  its sound, loading shaped like the content.
- **Measured, not guessed.** Each signature screen's size and speed is
  measured on the floor tablet, and a limit is set from that.

## Devices and their users

All are recent models.

- Owners: mostly iPhones, some Android phones; iPads at home
- Floor team: Android tablets
- Office: a Windows laptop

What this means:
- Two browser engines matter: Safari's (every browser on an iPhone or iPad
  uses it) and Chrome's (Edge uses it too).
- On an iPhone or iPad, push alerts work only after the app is added to the
  Home Screen.

A light theme only: the workshop is well lit, and dark text on a light
screen reads best there. A dark mode can come later as a second set of
token values, so components never hold a raw colour.

Every screen works at phone, tablet and laptop widths. A design is chosen
only after the real users have tried it on these devices.

Every screen uses one frame: content up to 1,200px wide with a 16px side
gutter, 16px between boxes, and 12px corners on every box. A wide screen
fills a laptop; it never gets its own width or spacing.

## Screen states

Each state is designed once, as a shared component, and every screen uses
it. A screen is not done until it handles every state that can happen on it.

| State | What the person sees |
|---|---|
| Loading | A loading sign. The save button stays locked until the answer comes. |
| Slow network | The same as loading. The server never saves the same thing twice (`docs/PLAN.md`, Phase 4). |
| Empty | That there is nothing here yet, and the next step (for example, add the first job card). |
| No search results | That nothing matched the search, with a way to clear it. |
| Form errors | Each error next to its field, in plain words. What was typed stays. |
| Success | A short confirmation, with its sound. |
| Server error | That something went wrong and nothing was saved, with a way to try again. |
| Not found | That the page or record does not exist. |
| Permission denied | That this role cannot open the page. None of its data is shown. |
| Session expired | The full sign-in page, never inside part of a page, saying what was not saved. |
| Offline | That there is no internet. A save says "Not saved", and nothing is sent again later by itself. |

The components, in `static/css/components.css`:
- Loading: the progress bar at the top (`.progress`) and the busy button
  (`aria-busy`); loading rows (`.skeleton`) for a part of a page that
  loads after the page.
- Empty and no search results: `.empty`.
- Form errors, success, a failed save, session expired and offline on a
  save: the notice (`.notice`), with the field errors for a form.
- Server error, not found, permission denied and offline: a page of its
  own (`.state-page`).
- The sound (`static/js/sound.js`, from v1): a short tone for a notice
  that carries `data-sound-tag` (success, error or warning; info stays
  silent), one per page, and a quieter tone when a confirmation card
  opens. It is on unless a device turns it off; that switch comes with
  the app's menu.

## Help notes

A help note is a short line that explains how the system works, for
example "This payment clears the oldest unpaid amount first." Once a
person knows the screen, it only gets in the way, so:

- **Behind the info button:** a note the person does not need to fill the
  form right or to make a decision. The button (an "i" in a circle) sits
  beside the title it explains; a tap shows the note under the title, and
  another tap hides it.
- **Always on the screen:** every note on a report page (the owner
  dashboard, Deep analysis), a warning before an action, a rule for what
  to type, an error, and a fact (a count, or how a figure is worked out).
- **How a note is written:** one or two short sentences in everyday words,
  checked against v1's code so it stays true.

## Accessibility

The target is WCAG 2.2, level AA.

- Contrast: at least 4.5 to 1 for normal text, 3 to 1 for large text and
  for controls. A box's edge is 3 to 1 against what is around it.
- Touch targets: at least 44 by 44 pixels. This is stricter than AA, which
  asks for 24. A control that looks smaller gets an invisible band that
  makes it 44 to a finger.
- Labels: every field has a visible label. In a table it is the column
  heading, and in a list of rows the section title. Two exceptions, both
  v1's: the list search (its search icon and hint say what it is) and the
  payment row's date (its calendar icon and the date itself). A screen
  reader hears a label on every box.
- Focus: a box that gets the keyboard focus is never hidden under a
  pinned header or column; scroll padding keeps it clear.
- Reflow: no sideways page scroll at 320 pixels wide. A wide table
  scrolls inside its own box.
- Checked: every lab page at 320, 375, 768 and 1280 pixels wide, by
  measurement and with the keyboard. Not tried yet: a screen reader, and
  the real devices.

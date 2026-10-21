# Design

How screens look and behave. Read it before any UI work.
What is planned: `docs/PLAN.md`. Where the files live: `docs/ARCHITECTURE.md`.
How the UI lab works: `CONTRIBUTING.md`. Words on screen: `docs/GLOSSARY.md`.

CSS base: plain CSS with our own tokens, no framework (ADR-0017).

- Tokens: `static/css/tokens.css`, the only home of every colour and size.
- Components: `static/css/components.css`: card (with a status edge),
  button, field, status badge, chip, back control. More are added as
  Phase 3 decides them.
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

## Accessibility

The target is WCAG 2.2, level AA.

- Contrast: at least 4.5 to 1 for normal text, 3 to 1 for large text and
  for controls.
- Touch targets: at least 44 by 44 pixels. This is stricter than AA, which
  asks for 24.
- Labels: every field has a visible label.

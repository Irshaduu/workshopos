# 0017: Plain CSS with our own tokens; no CSS framework, no build step

**Status:** Accepted (2026-10-20)

## Context

- Phase 3 builds the design system: tokens, about ten components and the
  screen states (`docs/DESIGN.md`). It needs a CSS base first.
- v1 kept Bootstrap 5.3.0 in the repo, then wrote its own look on top.
  Measured on `titan-final`: its own CSS files hold 2,899 lines
  (`style.css` 1,511, `analysis.css` 1,388), 78 of its 140 templates hold a
  `<style>` block, and the templates carry 672 `style="..."` attributes.
  Most of the look was overrides, many of them inside templates.
- v1 called Bootstrap's JavaScript in 16 templates, for modals, dropdowns,
  side panels and collapsing sections. HTML now has its own elements for
  these: `<dialog>` and `<details>`.
- v1 loaded one font (Inter) from Google Fonts.
- The plan asks for a strict Content-Security-Policy, with no CSS or JS
  inside templates. Every new dependency needs an ADR. The toolchain is
  Python and uv (ADR-0010); nothing needs Node.js today.
- The users work on iPhones, iPads, Android tablets and phones, and a
  Windows laptop, all recent models (`docs/DESIGN.md`). So the browsers
  are Safari and Chrome.

## Options

**A. Bootstrap 5 again**
- For: known from v1; many ready components; good documentation; no build
  step when the compiled file is used.
- Against: v1 shows the cost: 2,899 lines of overrides, and the look came
  from those, not from Bootstrap. Changing its own tokens properly needs
  Sass, which is a build step. Its JavaScript components would sit beside
  htmx and our modules: two ways to open a dialog.

**B. Tailwind CSS**
- For: popular; tokens kept in one config; the output holds only the
  classes in use; screens are quick to build.
- Against: a build step in development, CI and every deploy, and one more
  tool to pin and update. Long lists of classes in every template are hard
  to read and review, for people and for agents. A change to one component
  means editing many class lists.

**C. A small classless framework (for example Pico CSS)**
- For: tiny; good defaults for plain HTML; no build step.
- Against: it brings its own look, so we would override it, as in v1. Its
  defaults suit simple pages, not dense screens such as the live board or a
  ledger.

**D. Plain CSS with our own tokens**
- For: nothing to install, build or update. The files in the repo are what
  the browser gets. One file holds every colour and size. Modern CSS covers
  what v1 used Bootstrap for: grid and flexbox for layout, `<dialog>` and
  `<details>` for dialogs and collapsing sections. Easy to read for the
  developer, for a new developer and for agents. Fits the strict CSP.
- Against: we write every component ourselves. Accessibility is our job,
  not a framework's. There is no outside documentation, so `docs/DESIGN.md`
  and the lab page must be kept up to date.

## Decision

Option D.

- **Plain CSS, no CSS framework, no build step.** Files under `static/` are
  served as they are written.
- **Tokens are CSS custom properties in one file,** `static/css/tokens.css`:
  colour, type, spacing, radius, shadow. Components use tokens only, never a
  raw colour or size.
- **Cascade layers set the order:** reset, base, components, page. A page
  style then never beats a component by accident.
- **Native HTML first:** `<dialog>` for dialogs and side panels, `<details>`
  for sections that open and close. A small JS module only where HTML is not
  enough (ADR-0016).
- **Only CSS features that are Baseline "widely available"** (supported by
  every major browser for at least 30 months), and checked on the real
  devices in Phase 3.
- **Fonts and icons are kept in the repo,** never loaded from another site,
  like the htmx file (ADR-0016). Which ones is decided with the tokens. The
  font must also show Malayalam (ADR-0015).
- **Page-specific CSS** goes in `static/<app>/` (`docs/ARCHITECTURE.md`),
  never inside a template.
- **Any CSS library later needs its own ADR.**

## Consequences

- Phase 3 builds the components by hand, in the UI lab first. This is the
  work already planned, not extra work.
- The lab page shows every token and component in every state. It is the
  reference that people and agents check before writing a screen.
- Nothing checks CSS automatically yet: CSS linters need Node.js. Review
  checks that components use tokens only. If raw values start to appear, a
  small pre-commit check can refuse them outside `tokens.css`.
- If a real device lacks a feature, the Phase 3 device check shows it, and
  that feature waits or gets a simple fallback.
- No framework upgrade can break the screens, and there is none to keep
  updated.

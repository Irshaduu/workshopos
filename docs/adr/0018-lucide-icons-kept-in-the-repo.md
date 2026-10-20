# 0018: Icons: Lucide, only the icons we use, kept in the repo

**Status:** Accepted (2026-10-20)

## Context

- Phase 3 needs one icon set for the components and the signature screens,
  drawn in one style so every screen looks like one product.
- v1 used Bootstrap Icons as a font file, loaded on every page from
  `base.html`. With an icon font the browser downloads the whole font, an
  icon shows as an empty box if the font fails, and a screen reader may
  read an odd character.
- ADR-0017: no build step, and fonts and icons are kept in the repo, never
  loaded from another site. The strict CSP allows files from our own site
  only (ADR-0016).
- The icons a workshop needs, checked on 2026-10-20: car, wrench, rupee,
  engine, gauge, receipt, package, calendar, bell, camera, printer, phone,
  users, battery.

## Options

Facts read from the npm registry and GitHub on 2026-10-20.

**A. Lucide** (ISC licence, and MIT for the icons that came from Feather;
release 1.59.0)
- For: every icon on the list except a steering wheel; outline icons drawn
  on one grid with one line width, so they look like one family; the line
  width can be set in CSS; widely used, so other developers know it.
- Against: fewer icons than Tabler; no brand logos.

**B. Tabler Icons** (MIT licence, release 3.49.0)
- For: every icon on the list, plus a steering wheel and a garage; the
  most icons of all (its package holds 11,446 files).
- Against: the bigger set gives more choice, but more to search and more to
  keep alike.

**C. Heroicons** (MIT licence, release 2.2.0)
- For: small and neat.
- Against: no car, no engine and no gauge icon.

**D. Bootstrap Icons** (MIT licence, release 1.13.2; what v1 used)
- For: familiar from v1.
- Against: a mixed set of outline and filled icons, and it belongs to the
  Bootstrap look we left (ADR-0017).

## Decision

Option A.

- **Lucide, pinned to one release** (1.59.0 now).
- **Only the icons we use** are copied into one file,
  `static/icons/icons.svg` (an SVG sprite), with the release number noted
  at the top. Lucide's licence sits beside it in `static/icons/LICENSE`.
- The release file is downloaded once into a folder outside the repo; it
  never enters the repo.
- **Used as** `<svg class="icon"><use href="icons.svg#car"></use></svg>`.
  In the app this markup lives in one template component (Phase 4).
- **An icon takes the text's colour and size** by default; tokens set its
  size and line width.
- **An icon never carries meaning alone:** a visible word sits next to it,
  or it has a label for screen readers.
- A missing icon (a steering wheel) is drawn from Lucide's own shapes in
  the same style, or the screen uses a word. Brand logos (WhatsApp) come
  from the brand's own files, with the brand's rules, when they are needed.
- **Any other icon set needs its own ADR.**

## Consequences

- One small file holds every icon, cached once, with no font and nothing
  from another site.
- Adding an icon is a small step by hand: copy its SVG from the pinned
  release into the sprite. For the few dozen icons a workshop needs, a
  script is not worth it.
- The icons do not update themselves. The release is updated by hand with
  the monthly dependency updates (Phase 10), like the htmx file (ADR-0016).

# 0016: htmx 4 for server calls; small JavaScript modules for the rest

**Status:** Accepted (2026-10-16)

## Context

- Django renders every page on the server. Many screens still need one part
  of a page to change without a full reload: suggestions as you type, adding
  a part to a job card, the payment row, the live board.
- v1 did this with plain JavaScript. Measured on `titan-final`: 52 of its 142
  templates hold inline script, 31 use `onclick`-style attributes, and the
  templates call `fetch()` 19 times. Its 10 script files hold 3,747 lines.
  Some rules lived only in the browser: the suggested price is worked out in
  `pricing-core.js`, and the server holds no copy.
- The plan asks for a strict Content-Security-Policy (no inline script), one
  implementation per rule, and browser tests for the key flows.
- Django 6.1 has template partials (`{% partialdef %}`), so one template can
  render the whole page or only one part of it (ADR-0009).
- htmx is a small script (about 14 KB) with no build step. HTML attributes
  send a request, and the HTML the server answers with replaces a part of
  the page.
- htmx 4.0.0 was released on 2026-08-28. htmx 2 stays supported with no end
  date, and stays the default npm version until early 2027.

## Decision

- **htmx 4 for every interaction with the server.** The server answers with
  HTML, made by a partial of the same template that renders the full page.
- **Rules and numbers stay on the server.** JavaScript never works out money
  or decides a rule. Suggested prices, totals and checks come from services
  and selectors, tested in Python.
- **Small plain JavaScript modules** in static files, only for what happens
  in the browser alone: sounds, confirmation cards, the camera, push alerts.
  They hold no business rules.
- **Nothing that needs `eval`:** no `hx-on` attributes, no `js:` values, no
  trigger filters. With these left out, the CSP needs no `unsafe-eval`. Event
  handling lives in the JavaScript modules instead.
- **Every POST is a real `<form>` with `{% csrf_token %}`,** and with its
  normal `action` and `method`. Django's CSRF check then works with no extra
  header, and the form still posts if htmx does not load.
- **An invalid form answers 422** with the form and its errors. htmx 4 shows
  that answer in place by default.
- **The htmx file is kept in the repo** under `static/vendor/htmx/`, at an
  exact version, with its checksum noted. No CDN: the CSP allows scripts only
  from our own site, and pages never depend on another site being up. It is
  added with the first page that uses it (Phase 3, UI lab).
- **No other front-end library for now** (for example `django-htmx`). Each
  one needs its own ADR, when a real need appears.

**Why not plain JavaScript alone:** every interaction needs its own request,
page update and error handling. v1 shows where that leads: requests written
inside templates, and rules copied into the browser.

**Why not a framework such as React or Vue:** it means a second codebase
(an API and a front end), a build step, and rules on both sides. For
server-rendered pages, the cost is far above the benefit.

**Why htmx 4 and not 2:** no htmx code exists yet, so starting on 4 costs
nothing now. Starting on 2 means a move later, and some of its changes fail
silently. Its defaults also fit our rules:
- Attributes pass to child elements only when marked (`:inherited`). Nothing
  invisible, like the rule of no business logic in signals.
- Form errors (422) are shown, not dropped.
- It keeps no copies of pages in the browser's storage, so customer details
  are not left behind on a shared tablet.

## Consequences

- Most interactions are a round trip to the server. On a slow connection
  they feel slower than pure JavaScript. A loading indicator shows that work
  is in progress.
- htmx 4 is new, so there are fewer examples, and AI agents often write
  htmx 2 habits: attributes inherited without `:inherited`, and old event
  names such as `htmx:afterRequest` (now `htmx:after:request`). These fail
  silently. They are a code rule in `CONTRIBUTING.md`, checked in review, and
  the browser tests (Phase 5) cover the key flows.
- Each partial is a view that answers with HTML, so it is tested like any
  other view, with the Django test client.
- The pinned htmx file does not update itself. It is updated by hand with
  the monthly dependency updates (Phase 10), like the CI pins (ADR-0014).

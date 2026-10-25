# 0020: JavaScript unit tests with Node's own test runner

**Status:** Accepted (2026-10-25)

## Context

- ADR-0016: small plain JavaScript modules in static files, only for what
  happens in the browser alone (sounds, confirmation cards, the camera,
  push alerts), with no business rules and no build step.
- The plan sets up JavaScript unit tests with the first module. The first
  module is the outcome sound, rebuilt from v1's `sound.js`.
- v1 tested three of its modules with Node's own test runner:
  `node --test "workshop/tests/js/*.test.js"`. No npm, no `package.json`,
  no `node_modules`. The tests sat outside the static folder, so a test
  file was never served to a browser.
- Node 24.19.0 is on the laptop (checked 2026-10-25). Node 24 is a long
  term support line. Its test runner (`node:test`) and its assertions
  (`node:assert`) are built in.
- A test library such as Jest or Vitest comes from npm: a `package.json`,
  a lock file, a `node_modules` folder with many packages, and a second
  dependency audit.

## Decision

- **JavaScript unit tests use Node's own test runner**, `node:test` with
  `node:assert`. No npm, no `package.json`, no test library.
- Modules are ES modules in `static/js/`. Their rules are plain functions
  that need no page, and a module touches the page only in a browser.
- Tests live in `tests/js/<module>.test.js`, outside `static/`, so a test
  file is never served.
- What needs a real page (a dialog opening, a tap, a sound playing) is
  tested by the browser tests (Playwright, Phase 5).
- **CI runs them in the Tests job**, so the four required checks stay the
  same. Node there is pinned to the laptop's version, through
  `actions/setup-node` pinned to a commit ID (ADR-0014).
- Node is a tool for tests, like uv. The app never needs Node to run.

## Consequences

- Nothing to install or audit beyond Node itself.
- One command runs them: `node --test "tests/js/*.test.js"`.
- Only plain functions are tested here. A module's page work waits for the
  browser tests in Phase 5.
- No package.json means Node decides from the file itself that it is an ES
  module. Node 24 does this with no warning (checked 2026-10-25).
- The Node version on the laptop and in CI is updated by hand, together,
  with the monthly updates (Phase 10).

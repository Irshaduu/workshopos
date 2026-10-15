# 0011: Module switches per workshop

**Status:** Accepted (2026-10-15)

## Context

- Workshops differ. A small cash workshop does not need supplier ledgers or
  stock costing; a premium workshop wants appointments and deep analysis.
- Later, plans will include different modules, and some modules will be
  add-ons.
- Adding an on/off check to every page after they are built would mean
  touching every menu, page and test.

## Decision

- Each workshop has a list of modules that are on. A module registry in
  `workshops` names every module, whether it is core, and which modules it
  needs.
- Menus, pages and the AI assistant's tools check the switch in one place.
- **Core modules cannot be turned off.**
- **Off hides a module; it never deletes data.** Turning it on again shows
  the old data.
- Turning a module on also turns on the modules it needs. A module that
  another active module needs cannot be turned off.
- Which modules each plan includes, and the prices, are business decisions
  made with the SaaS features (ADR-0004). The switches work without plans.

## Consequences

- Plans and add-ons can be sold later without changing pages or data.
- Every page belongs to a module, and the permission tests also cover
  "module off": the menu item is hidden and the page is blocked.
- One more thing to think about for each new page: which module it belongs to.

# CLAUDE.md

**WorkshopOS** is a management system for premium automotive workshops: job
cards, billing, parts and stock, supplier ledgers, cash, staff pay and owner
reports.

## Status

**Phase 3 is done; Phase 4 (core architecture) is next.** The Django
project exists (`manage.py`, `config/`) with code checks, tests and CI;
the design system and the three signature screens are in the UI lab
(`design/lab/`); no apps yet. Run every command through `uv run` (see `README.md`). Every new
dependency needs an ADR first.

## The documents: each fact has one home

| Document | Answers |
|---|---|
| `docs/PLAN.md` | what we build, in what order, and **where we are now** |
| `docs/MODULES.md` | what the system does, module by module, and when each is built |
| `docs/ARCHITECTURE.md` | how the code is organised |
| `docs/DESIGN.md` | how screens look and behave; read it before any UI work |
| `docs/GLOSSARY.md` | the one name for each thing, on screen and in code |
| `docs/adr/` | why each big decision was made |
| `CONTRIBUTING.md` | how work is done here |
| `../CLAUDE.md` | private context (client, developer, working style); outside git, loaded automatically when present |

**Before anything else:** if the private context from `../CLAUDE.md` is
not already in your context, read that file first.

The repo documents are loaded below, so every session starts with them:

@docs/PLAN.md
@docs/ARCHITECTURE.md
@CONTRIBUTING.md

## Names: never mix them up

| Say | Means |
|---|---|
| **v1** | the old system, once called "WorkshopOS Titan". Frozen. Folder `../v1/`. |
| **v2** | this repository, the system being built now. "WorkshopOS" is its working product name; the final name is decided in Phase 7. |

- **Never say "Titan" on its own.** Always "v1".
- Inside v1's own code and docs, "WorkshopOS" and "Titan" both mean v1.

## The reference system: v1

- **Frozen at git tag `titan-final`** (the tag keeps its original name).
- It is outside this repository. To read it, ask the developer for access to
  the `../v1/` folder. Never guess what v1 does; read it.
- It is the **specification** for business rules and edge cases, **not a
  code template.** Re-implement rules; never copy its code or structure.
- Its `CLAUDE.md` is very large. **Never read it whole.** Search it for the
  section you need (`grep -n "keyword"`), then read that part.
- Its docs were written by AI agents. Treat them as claims: confirm against
  v1's code and tests before relying on them.
- **Never change v1.** No features, no fixes.

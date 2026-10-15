# 0001 — Record architecture decisions

**Status:** Accepted · **Date:** 2026-10-08

## Context

The previous system recorded its decisions inside one very large instruction
file. Reasons were hard to find, and some decisions were reversed without the
earlier reasoning being visible.

## Decision

Every significant decision gets a short ADR in `docs/adr/`, in the format set
out in `docs/adr/README.md`. Accepted ADRs are not rewritten; a new ADR
supersedes an old one.

## Consequences

- Anyone — a new developer or a new AI session — can find why something is
  the way it is.
- A small extra effort for each decision.

# 0009: Django 6.1 now, then 6.2 LTS

**Status:** Accepted (2026-10-15)

## Context

- Checked 2026-10-15 on djangoproject.com:
  - 6.1 is the current release (6.1.2), supported until December 2027.
  - 6.2 LTS is planned for April 2027, supported until April 2030.
  - 5.2 LTS is supported until April 2028.
- The 6.x line has a built-in Content-Security-Policy, template partials and
  a background-tasks interface. The plan asks for a strict CSP and simple,
  htmx-friendly templates.
- Starting on 5.2 would mean a bigger jump to the next LTS later.

## Decision

- Use Django 6.1, pinned to the 6.1 series (`>=6.1,<6.2`).
- Move to 6.2 LTS after it is released, as its own small, tested step.
- In production, stay on LTS releases after that.

## Consequences

- One planned upgrade in 2027.
- No separate CSP library is needed.
- Some add-on libraries can be slow to support a new Django, so each one is
  checked for 6.1 support before it is added (and gets its own ADR).

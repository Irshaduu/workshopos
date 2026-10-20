# 0008: AI assistant: tools over tested read-only functions

**Status:** Proposed (2026-10-15)

## Context

- Owners and office staff need quick answers from their own data: when a car
  will be ready, why a profit figure looks wrong, which parts are late.
- Customers want to know their car's service status without calling.
- An AI model understands questions well, in English and in Malayalam. But it
  can get numbers wrong, it can be tricked by what people type, each question
  costs money, and customer data is personal data under India's DPDP Act.

## Decision (proposed)

- **One assistant, three audiences:** owner, office and customer. What it can
  see is set by the person's role (ADR-0007), never by the prompt.
- **The assistant never calculates.** It calls tools: read-only functions
  built on the same tested selectors the screens use, always scoped to the
  workshop. For a customer, scoped to one vehicle.
- **No tool changes data.** When the assistant prepares something (for
  example a draft bill from a photo), a person checks it and saves it.
- **Input helpers** (voice input, bill from a photo) only fill a form the
  person can already use, so Floor may use them too. They read no data.
- **The customer assistant** sees one vehicle only. "Service due" comes from
  the workshop's own service rules. It never diagnoses a fault, and it always
  offers to contact the workshop or book a visit.
- **Personal data:** only what the question needs is sent to the AI service.
  No phone numbers. The customer agrees first.
- **Tested with an eval set:** fixed questions with expected answers on fake
  data, run in CI.
- **The AI provider and model** are chosen when this is built (their own ADR).
  The code talks to the provider through one module, so it can be changed.
- **Built after go-live.** The cost per question is measured on the first
  version before it is priced.

## Consequences

- Numbers stay correct and tested, because the same functions feed the screens.
- Safety comes from the tools' scope: even a tricked assistant cannot see more
  than its tools allow.
- Every question has a cost, so the assistant may become part of a higher plan.
- The data it needs must be recorded from go-live: kilometres as a number,
  and times of status changes (`docs/ARCHITECTURE.md`, Shared rules).

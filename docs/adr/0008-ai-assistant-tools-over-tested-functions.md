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
- **The workshop and the role come from the signed-in request**, never from
  what the model or a person types. Each tool runs in a read-only database
  transaction, so even a bug cannot change data.
- **Every question is logged:** who asked, which tools ran and the cost,
  with no personal data. The rows live in `assistant`, and totals are worked
  out from them. This log gives the cost per question.
- **Cost limits, from the first version:** a limit per question (answer
  length, tool rounds), so a bug or a retry stays small; and a monthly limit
  per workshop. At the limit the assistant pauses, and everything else keeps
  working.
- **No prepaid wallet for now.** It waits for measured numbers. It would not
  end the risk: the provider still bills us, the cost is known only after
  each call, and unused balance is customers' money we hold (the accountant
  answers on GST for a recharge, refunds and the rules for prepaid money).
  It also needs a payment gateway. If the market asks, a recharge only adds
  to the month's limit: new rows, no change to real records.
- **No MCP server and no webhooks for now.** Each is a new door with its own
  sign-in.
- **Built after go-live.** The cost per question is measured on the first
  version before it is priced.

## Consequences

- Numbers stay correct and tested, because the same functions feed the screens.
- Safety comes from the tools' scope: even a tricked assistant cannot see more
  than its tools allow.
- Every question has a cost, so the assistant may become part of a higher plan.
- The data it needs must be recorded from go-live: kilometres as a number,
  and times of status changes (`docs/ARCHITECTURE.md`, Shared rules).

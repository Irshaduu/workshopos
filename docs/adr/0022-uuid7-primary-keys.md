# 0022: Primary keys: UUID7, made by Python, with PostgreSQL as backup

**Status:** Accepted (2026-10-26)

## Context

- A key is in every table and in every link between tables. Changing it
  after the first migration means rebuilding all of them.
- The first workshop will probably run on its own server, and may later
  move to a shared one with other workshops (ADR-0003). Number keys from two
  servers clash, so every key and every link would need new numbers.
- On a shared server, number keys show how many records all workshops make
  together, and they can be guessed. The leak tests still block access.
- A workshop's old data will be imported in bulk, with records linked
  before they are saved: customer, car, bill, bill lines.
- Measured on 2026-10-26 with Django 6.1 and PostgreSQL 18.6, on throwaway
  tables:
  - With a key made only by PostgreSQL (`db_default=UUID7()`), a record
    linked to another before that one was saved failed to save. When the
    link was allowed to be empty, it saved with no link and no error.
  - With the key made by Python as well, every case worked: one by one and
    in bulk, with one INSERT per save. A row added outside Django still got
    its key from PostgreSQL.
- Options compared: plain numbers (small and easy to read; the clash and the
  counts above), UUID4 (random, so the index scatters), UUID7 (ordered by
  time), and numbers inside with a UUID for addresses (two IDs on every row;
  the clash stays).

## Decision

- **Every model in our apps gets a UUID7 key from `core`'s base model**
  (`apps/core/models.py`):
  - Python makes it when the record is created (`default=uuid.uuid7`);
  - PostgreSQL makes it for a row added outside Django
    (`db_default=UUID7()`).
- A test checks that every model in our apps has this key.
- Django's own tables keep number keys (sessions, permissions, its
  many-to-many link tables). `DEFAULT_AUTO_FIELD` says so.
- People never see or use the key. Job card and bill numbers are separate,
  per branch (Slice 1).

## Consequences

- Records move between servers without new numbers, and records can be
  linked before they are saved.
- A key takes 16 bytes instead of 8, and web addresses are longer.
- A key shows when its record was made. Nothing is put in order by its key;
  dates and numbers give the order.
- A key exists from the start, so "is this record saved?" is never asked as
  "is the key empty?". Django's own `_state.adding` answers it.

# 0029: Money: one column and one box for every amount

**Status:** Accepted (2026-11-04)

## Context

- Correct money comes first (`docs/ARCHITECTURE.md`). The first money column is
  the job card's labour charge, and many more follow it.
- v1 mixed two sizes, numeric(10, 2) and numeric(12, 2). Its own database checks
  show two kinds of amount: 9 money columns must be above zero, 6 may be zero,
  and none of those checks allows a negative amount.
- The plan said a zero or negative amount is refused everywhere. That is wrong
  for a charge: plenty of job cards have no labour.
- Measured on Django 6.1 and PostgreSQL 18:
  - PostgreSQL rounds a third decimal with no error: saving 2950.555 stores
    2950.56, and a float is rounded the same way. Django stops this only when the
    code calls `full_clean()` first.
  - PostgreSQL calls NaN above zero, so a check alone would let it in. Django
    refuses NaN and Infinity on every save.
  - Django lets a field carry its own check (`db_check()`), and it makes that
    check when the table is made. When the column changes later, Django never asks
    again (`_field_db_check`), so PostgreSQL keeps the old rule, with no error.
  - Django's decimal form field refuses commas, NaN and Infinity, but in words
    staff will not follow. Python's `Decimal` also reads `2_95` as 295 and `1e3` as
    1000, and `0e99999999999` reaches PostgreSQL and crashes the page.
  - A form that never sent a box cleans it to None, the same as a box left empty.
    A service gets only that answer, so a saved price would be wiped with no error.
- By the HTML standard, a number box hands the server an empty value for `2,950`,
  and on a laptop the mouse wheel can change it.

## Decision

- **One column:** `MoneyField` (`apps/core/money.py`), one size, numeric(12, 2).
- **Two kinds, and nothing is ever negative:** `MoneyField()` is money that moved,
  like a payment, and must be above zero. `MoneyField(allow_zero=True)` is a
  charge, like labour, and may be zero. The stricter kind is the default, so
  forgetting is safe.
- **Three guards, one rule:** the model refuses a wrong amount in plain words;
  every save of a plain amount runs the same rules, even with no `full_clean()`;
  and a check in the model's `Meta` makes PostgreSQL refuse it too.
- **The check is a plain line in `Meta`, not built into the field,** because of
  `db_check()` above. It is the plain Django any developer knows.
- **A float or a third decimal is refused at save, never rounded.** It raises
  `TypeError` or `ValueError`, not `ValidationError`: what a person typed was
  checked long before, so here it is a programmer's mistake, which no page may show
  as a message on a form. A calculation rounds on purpose before it saves. Its rule
  comes with the first calculation that needs one (`docs/PLAN.md`, Phase 6).
- **One box:** `MoneyFormField`, Django's decimal form field with no parser of our
  own. It is a text box with a number keypad, and it speaks in plain words.
- **A person may type only digits, one point and a minus.** A comma is refused, not
  removed, because a slip like `2,95` would become 295 on a bill. `2_95` and `1e3`
  are refused for the same reason, by the box and by the column, so an import that
  hands over text gets the same answer.
- **The box gives an amount with two decimals, like a saved one.** A saved amount
  shows ready to type over: 8500.00 shows as 8500.
- **Empty means 0 only on a column that cannot be empty,** like labour. On a column
  that may be empty, like a part's price, empty means not priced yet and 0 means
  free.
- **A box never sent refuses the whole form,** so nothing is wiped (v1's lesson). A
  form holds only what its role may change (ROLE-13), so a right form always sends
  its boxes. A field marked `disabled` keeps its saved amount.
- **A test walks every column** (`tests/test_money.py`), generated ones too: a
  decimal column that is not a `MoneyField`, a float column, another size, or a
  missing or wrong check fails it. A decimal column that is not money, like a
  quantity, gets a short list in that test, with why, when the first one comes.
  The same test reads every form: a number box or another decimal box fails it.

## Consequences

- A new money column is one field and one line in `Meta`, and the test says which
  line is missing.
- `apps.core.money.MoneyField` is named in every migration with a money column, so
  moving the class means leaving its old path working.
- A later calculation fails loudly until it rounds on purpose. That is the point.
- An expression, like `F("amount") * Decimal("1.18")` or `Value(...)`, goes straight
  to PostgreSQL: its check still guards zero and negative, but a third decimal would
  be rounded. So it rounds on purpose first.
- A `Sum` with a default inside a saved expression, like `update(paid=Subquery(...))`,
  is refused when the default breaks the column's rule. Give that default a plain
  `DecimalField` as its output. A total is worked out when read (`CONTRIBUTING.md`),
  so this should be rare.
- `full_clean()` sends one small query for each check, Django's own way. It is
  measured with the first job lines (Phase 6), where many rows save together.
- Someone who types `1,47,500` has to type it again without the commas.
- A column that truly must go negative would need a new kind. One to decide when
  Monthly salary is built: in v1, a month's net salary goes below zero when the
  advance is bigger than the salary. A refund, if a workshop ever needs one, is its
  own row with a positive amount.

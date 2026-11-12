# Rules: change history

The rules of the Change history module (`docs/MODULES.md`): what is kept when money is
changed after it was recorded, and what Office may change or date by itself. Taken from v1
and checked in v1's code (`EditLog` and `DeletionLog` in `workshop/models.py`,
`workshop/delete_window.py`, `workshop/money_dates.py`, `notify_changed` and
`notify_dated_back` in `workshop/notifications.py`, and their tests in
`test_delete_window.py`, `test_backdate_floor.py`, `test_backdated_history.py`,
`test_money_change_rules.py` and `test_edit_history.py`). Settle bill builds the first part
(`docs/rules/settle-bill.md`); each later money record joins with its own module. Why each
workshop has its own limits: ADR-0024. Words: `docs/GLOSSARY.md`. The code: `apps/audit/`.

- Each rule has an ID. A test names the ID of the rule it protects.
- An ID never changes. A new rule takes the next free number.
- Each rule says where it comes from: **v1** (kept as it was), **v1, changed** (and what
  changed), or **new** (v2 only).
- Every rule is built with Settle bill, unless it says when.

v1's owners decided on 2026-09-22 that Office does the day's money, and that changing older
money, or dating money further back, is an owner's to do, and never silent. These rules
keep that for every money record, in one place.

## What is kept

- **CHANGE-1** A change to money after it was recorded is kept for good, as one change:
  what it was about, each figure before and after, who made it, when, and why. *v1:
  `EditLog`, "a history that forgets on a timer is a loophole with a waiting period".*
- **CHANGE-2** A change names its record in words, frozen when it is kept, like
  "INV-26-27-0045, KL07AB1234", and keeps the record's key, with no link to it, so the
  change outlives the record. *v1: "NO FOREIGN KEY to the edited row, deliberately".*
- **CHANGE-3** A change is kept in the same transaction as what it changed, so a save that
  fails keeps nothing, and nothing changes without its change kept. *v1: `EditLog.record`.*
- **CHANGE-4** Only the figures that moved are kept, each as it was saved: an amount with
  its paise, a date as a date. A save that moves nothing keeps nothing. *v1:
  `EditLog.change`, "Stored RAW".*
- **CHANGE-5** Every change says why, in a box that must be filled, up to 255 characters.
  *New (`docs/PLAN.md`: who, when and why). v1 kept no reason for an edit.*
- **CHANGE-6** A change is never changed or removed by anyone, in the app or in the Django
  admin. *v1: "Immutable".*
- **CHANGE-7** Recording money the first time is not a change: settling a bill keeps none,
  and changing it does. *v1: `test_a_first_settlement_is_not_an_edit`.*
- **CHANGE-8** The first changes kept are those of a settled bill (SETTLE-41). Each later
  money record, like the cashbook or a payment to a shop, adds its own with its module. A
  delete of money is kept the same way, with the first one. *v1: `EditLog` and
  `DeletionLog`, here in one table.*

## The edit window

- **CHANGE-9** Office may change money for 24 hours after it was recorded. After that,
  only an owner may. A settled bill counts from the moment it was settled. *v1:
  `delete_window`, the owners' decision of 2026-09-22.*
- **CHANGE-10** The window counts from the moment the money was typed in, never from its
  money date, so Office can fix a back-dated payment typed a minute ago. *v1: "THE WINDOW
  IS MEASURED ON WHEN THE ROW WAS TYPED".*
- **CHANGE-11** An owner is never refused, and the change is kept like any other. *v1.*
- **CHANGE-12** A refusal says how long ago the money was recorded, the rule, and who can
  do it: "Settled 30 hours ago. Office can change money only within 24 hours. Ask an
  owner." It counts in hours for two days, then in days. A page that knows in advance
  says this in place of the button (ROLE-12). *v1: `refusal`, `_how_long_ago`,
  `is_past_window`.*

## Money dates and the back-date limit

- **CHANGE-13** A typed money date starts at today, India time. *v1: `posted_date`.*
- **CHANGE-14** A money date in the future is refused, never moved to today, because it is
  a mistyped year far more often than a plan. *v1: `is_future`.*
- **CHANGE-15** Office may date money up to 3 days back: on the 22nd, the 19th at the
  earliest. An older date is refused, naming the earliest day and saying to ask an owner.
  The date box shows that earliest day, but only the server decides. *v1: `money_dates`,
  the owners' decision of 2026-09-22.*
- **CHANGE-16** An owner may date money any day. It is never silent: the change history
  shows it (Phase 6). *v1: `too_far_back`, "an owner is never refused".*
- **CHANGE-17** Back-dated money keeps nothing of its own: the record already keeps the day
  the money moved and the moment it was typed, and who typed it. Whether it was dated past
  the limit is judged on the day it was typed, so money never becomes past the limit as
  time goes by. *v1: the Back-dated tab, "NOTHING IS STORED FOR IT", and
  `filed_past_limit`.*

## The settings

- **CHANGE-18** The 24 hours and the 3 days are each workshop's own settings, the edit
  window and the back-date limit, beside these rules (ADR-0024). A workshop that never chose
  its own uses v1's values. A new value acts from the next action, never on what is saved.
  Only an owner changes one, and the change is kept (CHANGE-1). *New (ADR-0024).*

## Left out for now

- The owners' page, Change history: changes, deletes and back-dated money, month by month,
  with the bell (Phase 6). Only owners open it (ROLE-21).
- The alerts: a change Office may make goes to the bell; one only an owner may make, or a
  date past the limit, goes to the other owners' phones. *v1: `notify_changed`,
  `notify_dated_back`.* With the bell (Phase 6).
- A settings screen: only if the owners want one (`docs/MODULES.md`). Until then the
  developer changes a value for them.

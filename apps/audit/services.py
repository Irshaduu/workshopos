"""Changes in audit: keeping a change to money in the change history
(docs/rules/change-history.md, ADR-0032)."""

import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.http import Http404

from apps.audit.models import Change
from apps.core.money import ONE_PAISA
from apps.core.text import tidy_spaces

MONEY = "money"
DATE = "date"


def keep_change(workshop, branch, by, *, key, what, record_key, label, before, after, reason):
    """Keeps one change to money, with only the figures that moved, in the caller's own
    transaction (CHANGE-1 to CHANGE-5). Nothing moved: nothing is kept, and the answer is
    None.

    `key` is the change's own key, made when its box opened, like every new record's
    (CONTRIBUTING.md), so a caller asks kept_change() first and a double tap keeps one
    change. `before` and `after` hold each figure by its name, in the order to show them:
    an amount as a Decimal, a day as a date, or None for no figure, like a method with no
    payment.
    """
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("A change is kept in the transaction of what it changed (CHANGE-3).")
    # An address can be typed by hand, and only a UUID7 may become a key (ADR-0022).
    if key.version != 7:
        raise Http404
    figures = [
        _figure(name, before.get(name), after.get(name))
        for name in dict.fromkeys([*before, *after])
        if before.get(name) != after.get(name)
    ]
    if not figures:
        return None
    change = Change(
        id=key,
        workshop=workshop,
        branch=branch,
        what=what,
        record_key=record_key,
        label=label,
        figures=figures,
        reason=tidy_spaces(reason),
        by=by,
    )
    # The words in plain words, with no query: the links and the key are the caller's, and
    # PostgreSQL checks them on the insert.
    change.clean_fields(exclude={"id", "workshop", "branch", "by"})
    try:
        # Its own savepoint, so a refused key leaves the caller's transaction able to end.
        with transaction.atomic():
            change.save(force_insert=True)
    except IntegrityError:
        # The key is another change's: typed by hand, or sent for two records at one moment.
        raise Http404 from None
    return change


def _figure(name, before, after):
    """One figure that moved, each side as it was saved (CHANGE-4)."""
    kinds = {_kind_of(value) for value in (before, after) if value is not None}
    if len(kinds) != 1:
        raise TypeError(f"{name} was {before!r} and is {after!r}: one kind on both sides.")
    return {
        "figure": name,
        "kind": kinds.pop(),
        "before": _as_saved(before),
        "after": _as_saved(after),
    }


def _kind_of(value):
    if isinstance(value, Decimal):
        return MONEY
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return DATE
    raise TypeError(f"A change keeps amounts and days, not {value!r}.")


def _as_saved(value):
    """An amount with its paise, like 40000.00, and a day as 2026-11-18; None as none."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value.quantize(ONE_PAISA))
    return value.isoformat()

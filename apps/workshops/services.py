"""Changes in workshops: rules that change data (ADR-0005)."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import Http404


def save_once(record, *, parent=None):
    """Saves a new record once, however many times its form is sent (docs/PLAN.md, Phase 5).

    The page made the record's key when it opened the form, and put it in the
    form's address (a UUID7 key exists before saving, ADR-0022). So a double tap,
    or a second try after a slow network, sends the same key, and PostgreSQL
    refuses a second copy.

    It answers with the record and whether this call saved it, like Django's
    get_or_create. A repeat gets the record saved first, with its first values, so
    a service with more to save, like a job card's lines, knows to skip that part.

    A key taken by a record of another workshop or branch answers "not found", like
    any record of another workshop: it never shows that record, and never calls it a
    success. A record under a parent, like a bill under its job card, names its link
    as `parent`: a key taken under another parent answers "not found" too, so a key
    sent again for another parent never adds to that record (v1's lesson).
    """
    # An address can be typed by hand, and only a UUID7 may become a key (ADR-0022).
    if record.pk.version != 7:
        raise Http404
    try:
        # The key is left to PostgreSQL: its check holds even when two sends meet.
        record.full_clean(exclude={"id"})
        # Its own savepoint, so a refused save leaves a bigger transaction working.
        with transaction.atomic():
            record.save(force_insert=True)
    except ValidationError, IntegrityError:
        # Either this key is saved already, or a real rule refused.
        # not for_workshop: a key is unique across workshops, and _place() checks the workshop.
        saved = type(record).objects.filter(pk=record.pk).first()
        if saved is None:
            raise
        if _place(saved) != _place(record) or _parent(saved, parent) != _parent(record, parent):
            raise Http404 from None
        return saved, False
    return record, True


def _parent(record, link):
    """The key of a record's parent, through its link; None when no link is named."""
    return getattr(record, record._meta.get_field(link).attname) if link else None


def _place(record):
    """A record's workshop and branch. A workshop-wide record has no branch."""
    return record.workshop_id, getattr(record, "branch_id", None)

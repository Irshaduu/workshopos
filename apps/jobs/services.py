"""Changes in jobs: rules that change data (ADR-0005)."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from apps.core.text import tidy_spaces
from apps.jobs.models import (
    CONCERN_STEPS,
    Concern,
    ConcernStatus,
    JobCard,
    JobCardStatus,
    JobCardStep,
    JobLine,
    NumberCounter,
    StepKind,
    number_from,
)
from apps.jobs.selectors import open_card_of, saved_job_card
from apps.vehicles.services import car_on_a_new_card, change_car, customer_for
from apps.workshops.services import save_once

#: The boxes of a job card that belong to the car (JOB-12).
CAR_BOXES = ("plate", "brand", "car_model", "chassis_code", "vin", "colour", "colour_other")
#: The boxes that belong to this visit, and live on the card itself.
CARD_BOXES = ("lead_mechanic", "admitted_date", "mileage", "note", "labour")


class CarHasOpenCard(ValidationError):
    """A second open job card for a car (JOB-4). It carries the open one, so the page can
    link to it when it is in this branch."""

    def __init__(self, card):
        words = _("This car already has an open job card, %(number)s.") % {"number": card.number}
        super().__init__({"plate": words})
        self.card = card


class RowRefused(ValidationError):
    """A saved row changed to repeat another row (JOB-37). It carries the row's key, so the
    page can show the error next to that row."""

    def __init__(self, key, words):
        super().__init__(words)
        self.key = key


def _step(card, by, kind, concern=None):
    """One change in the card's life, with who acted and the lead mechanic at this moment
    (JOB-39, JOB-40)."""
    JobCardStep(
        workshop=card.workshop,
        job_card=card,
        kind=kind,
        concern=concern,
        by=by,
        mechanic=card.lead_mechanic,
    ).save()


def _add_concerns(card, by, rows, saved_words):
    """Adds new concerns, leaving out repeats with no error, so a slow network can never
    add lines twice (JOB-37). A new concern already Working or Fixed gets its step (JOB-41)."""
    for row in rows:
        text = tidy_spaces(row["text"])
        if text and text.lower() not in saved_words:
            saved_words.add(text.lower())
            concern = Concern(workshop=card.workshop, job_card=card, text=text)
            concern.status = row.get("status") or ConcernStatus.PENDING
            concern.save()
            if concern.status != ConcernStatus.PENDING:
                _step(card, by, CONCERN_STEPS[concern.status], concern)


def _add_job_lines(card, rows, saved_words):
    """Adds new job lines, leaving out repeats, the same way (JOB-37)."""
    for row in rows:
        text = tidy_spaces(row["text"])
        if text and text.lower() not in saved_words:
            saved_words.add(text.lower())
            JobLine(workshop=card.workshop, job_card=card, text=text).save()


def _refuse_a_second_open_card(workshop, car):
    if (open_card := open_card_of(workshop, car)) is not None:
        raise CarHasOpenCard(open_card)


def make_job_card(workshop, branch, key, by, *, typed, concerns=(), job_lines=()):
    """Makes a job card once, with its car, customer, number, rows and steps, however many
    times the form is sent (JOB-42). It answers with the card saved.

    The counter's lock comes first, and the question whether the key is saved comes after
    it, because a second tap waits at that lock. So a double tap uses no number (JOB-6). A
    refusal undoes all of it, so a save that fails uses no number either.
    """
    with transaction.atomic():
        counter, _made = (
            NumberCounter.objects.for_workshop(workshop)
            .for_branch(branch)
            .select_for_update()
            .get_or_create(workshop=workshop, branch=branch)
        )
        saved = saved_job_card(workshop, branch, key)
        if saved is not None:
            return saved

        car = car_on_a_new_card(workshop, **{box: typed[box] for box in CAR_BOXES if box in typed})
        _refuse_a_second_open_card(workshop, car)
        counter.last_number += 1
        counter.save(update_fields=["last_number"])
        card = JobCard(
            id=key,
            workshop=workshop,
            branch=branch,
            number=number_from(counter.last_number),
            car=car,
            plate=car.plate,
            customer=customer_for(
                workshop, typed.get("customer_name", ""), typed.get("contact_number", "")
            ),
            lead_mechanic=typed.get("lead_mechanic"),
            admitted_date=typed["admitted_date"],
            mileage=typed.get("mileage"),
            note=typed.get("note", ""),
            labour=typed.get("labour", Decimal("0")),
        )
        try:
            card, _saved_now = save_once(card)
        except IntegrityError:
            # The car had no open card when it was checked, then another send made one.
            _refuse_a_second_open_card(workshop, car)
            raise
        _step(card, by, StepKind.CAR_IN)
        _add_concerns(card, by, concerns, set())
        _add_job_lines(card, job_lines, set())
    return card


def _locked(workshop, branch, key):
    """The job card with this key, locked until the transaction ends."""
    return get_object_or_404(
        JobCard.objects.for_workshop(workshop)
        .for_branch(branch)
        .select_for_update(of=("self",))
        .select_related("car__car_model__brand", "customer"),
        pk=key,
    )


def _change_customer(card, changes):
    """Points the card to the record its two boxes name, and no other card changes
    (JOB-28). A box that did not change comes from the card's customer."""
    if {"customer_name", "contact_number"} & changes.keys():
        now = card.customer
        card.customer = customer_for(
            card.workshop,
            changes.get("customer_name", now.name if now else ""),
            changes.get("contact_number", now.contact_number if now else ""),
        )


def _changed_words(rows, key, typed):
    """A saved row's new words; refused when they repeat another row's (JOB-37)."""
    words = tidy_spaces(typed)
    for other_key, other in rows.items():
        if other_key != key and other.text.lower() == words.lower():
            raise RowRefused(key, _("This is already on the card."))
    return words


def _remove_emptied(rows, saved):
    """Emptied words remove a saved row (JOB-36). These go first, so a row's old words are
    free for another row in the same save (JOB-37)."""
    for key, changes in saved:
        if key in rows and "text" in changes and not tidy_spaces(changes["text"]):
            rows.pop(key).delete()


def _change_concerns(card, by, saved, new):
    """Applies what changed on each saved concern. An emptied row goes with its steps (JOB-36,
    JOB-41). A row someone else removed stays removed (JOB-43). A status that is already set
    adds no step, so a repeat adds none (JOB-41)."""
    rows = {row.pk: row for row in card.concerns.all()}
    _remove_emptied(rows, saved)
    for key, changes in saved:
        row = rows.get(key)
        if row is None:
            continue
        if "text" in changes:
            row.text = _changed_words(rows, key, changes["text"])
        status = changes.get("status") or row.status
        moved = status != row.status
        row.status = status
        row.save()
        if moved:
            _step(card, by, CONCERN_STEPS[status], row)
    _add_concerns(card, by, new, {row.text.lower() for row in rows.values()})


def _change_job_lines(card, saved, new):
    """The same for job lines, which have no status (JOB-36, JOB-43)."""
    rows = {row.pk: row for row in card.job_lines.all()}
    _remove_emptied(rows, saved)
    for key, changes in saved:
        row = rows.get(key)
        if row is None or "text" not in changes:
            continue
        row.text = _changed_words(rows, key, changes["text"])
        row.save()
    _add_job_lines(card, new, {row.text.lower() for row in rows.values()})


def change_job_card(
    workshop,
    branch,
    key,
    by,
    *,
    changes,
    saved_concerns=(),
    new_concerns=(),
    saved_lines=(),
    new_lines=(),
):
    """Applies only what this person changed since opening the page, in one locked
    transaction (JOB-43). So a tablet left open all morning can never put back Office's fix
    or a concern's old status. A repeat changes nothing more (JOB-37, JOB-41)."""
    with transaction.atomic():
        card = _locked(workshop, branch, key)
        if not card.is_open:
            raise ValidationError(_("This job card is cancelled, so nothing was saved."))

        car_changes = {box: changes[box] for box in CAR_BOXES if box in changes}
        if car_changes:
            card.car = change_car(workshop, card.car, car_changes)
            card.plate = card.car.plate
        _change_customer(card, changes)
        for box in CARD_BOXES:
            if box in changes:
                setattr(card, box, changes[box])
        if changes:
            card.full_clean()
            card.save()
        _change_concerns(card, by, saved_concerns, new_concerns)
        _change_job_lines(card, saved_lines, new_lines)
    return card


def cancel_job_card(workshop, branch, key, by, reason):
    """Ends a job card with no bill: it keeps its number and everything on it, and its car is
    free at once for a new card (JOB-49, JOB-51). A repeat changes nothing."""
    with transaction.atomic():
        card = _locked(workshop, branch, key)
        if card.is_open:
            card.status = JobCardStatus.CANCELLED
            card.cancel_reason = tidy_spaces(reason)
            card.save(update_fields=["status", "cancel_reason"])
            _step(card, by, StepKind.CANCELLED)
    return card

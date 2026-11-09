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
from apps.jobs.selectors import (
    car_for_plate,
    has_other_visits,
    newest_visit,
    open_card_of,
    saved_job_card,
)
from apps.vehicles.models import tidy_plate
from apps.vehicles.selectors import car_brand_named, car_with_vin
from apps.vehicles.services import (
    change_car,
    customer_for,
    empty_plate,
    empty_vin,
    new_car,
    remove_if_unused,
)
from apps.workshops.services import save_once

#: The boxes of a job card that belong to the car, besides its plate, brand and model.
CAR_OWN_BOXES = ("chassis_code", "vin", "colour", "colour_other")
#: All the boxes of a job card that belong to the car (JOB-12).
CAR_BOXES = ("plate", "brand", "car_model", *CAR_OWN_BOXES)
#: The boxes that belong to this visit, and live on the card itself.
CARD_BOXES = ("lead_mechanic", "admitted_date", "mileage", "note", "labour")


class CarHasOpenCard(ValidationError):
    """A second open job card for a car (JOB-4), or a VIN on a car with an open job card
    (KNOWN-12). It carries the open card and the box it is about, so the page can link to the
    card next to that box when it is in this branch."""

    def __init__(self, card, box="plate", words=None):
        if words is None:
            words = _("This car already has an open job card, %(number)s.") % {
                "number": card.number
            }
        super().__init__({box: words})
        self.card = card
        self.box = box


class Question(Exception):
    """A save that asks first, because the records disagree (KNOWN-13).

    It names the car it is about. A button answers it by sending "question:answer:car key", so
    an answer about any other car is no answer, and if the records changed in between, the save
    asks again. `plate` is the plate typed, `old` says it is only an old plate of the car, `same`
    says whether "same car" is offered, and `last_in` is the day the car was last in.
    """

    def __init__(self, kind, car, *, plate, old, same, last_in):
        super().__init__(kind)
        self.kind = kind
        self.car = car
        self.plate = plate
        self.old = old
        self.same = same
        self.last_in = last_in


def _answered(answers, question, answer, car):
    return f"{question}:{answer}:{car.pk}" in answers


def _another_brand(workshop, car, typed):
    """Whether typed words name another brand than the car's, by the list's own rule (JOB-17)."""
    return car_brand_named(workshop, typed) != car.car_model.brand


def _ask(workshop, kind, car, plate, *, card=None, same=False):
    """The question about this car, with the day it was last in, besides this card."""
    newest = newest_visit(workshop, car, besides=card)
    return Question(
        kind,
        car,
        plate=plate,
        old=car.plate != plate,
        same=same,
        last_in=newest.admitted_date if newest is not None else None,
    )


def _is_another_car(workshop, car, plate, answers, card=None):
    """Whether the car in front of you is another car than this one, as the person answered.
    Until they do, the save asks (KNOWN-10). Another car, checked against its RC, takes the
    plate when this car has it today."""
    if _answered(answers, "brand", "another", car):
        if car.plate == plate:
            empty_plate(workshop, car)
        return True
    if not _answered(answers, "brand", "same", car):
        raise _ask(workshop, "brand", car, plate, card=card)
    return False


def _car_by_its_vin(workshop, vin, car, brand, plate, answers, *, alone, card=None):
    """The car the card is for once the VIN typed is settled (KNOWN-11, KNOWN-12): `car`, or the
    car the VIN is on, when the person says it is the same one. That is offered only for a car
    with no record of its own yet (`alone`), of the same brand. Otherwise this car keeps the VIN,
    and the other car's is emptied."""
    if car is not None and car.vin == vin:
        return car
    holder = car_with_vin(workshop, vin, besides=car)
    if holder is None:
        return car
    open_card = open_card_of(workshop, holder)
    # Not this card itself: the car it is leaving can hold the VIN typed again.
    if open_card is not None and open_card != card:
        words = _("This VIN is on %(car)s, %(plate)s, which has an open job card, %(number)s.") % {
            "car": holder.name,
            "plate": holder.plate or _("no plate now"),
            "number": open_card.number,
        }
        raise CarHasOpenCard(open_card, box="vin", words=words)
    same = alone and not _another_brand(workshop, holder, brand)
    if same and _answered(answers, "vin", "same", holder):
        return holder
    if _answered(answers, "vin", "keep", holder):
        empty_vin(workshop, holder)
        return car
    raise _ask(workshop, "vin", holder, plate, card=card, same=same)


def _not_what_it_holds(filled, car):
    """What a new car takes from the boxes: never what the other car holds, because the fill
    wrote that there (KNOWN-10). The two colour boxes are one answer."""
    kept = dict(filled)
    for box in ("chassis_code", "vin"):
        if kept.get(box) == getattr(car, box):
            del kept[box]
    if (kept.get("colour"), kept.get("colour_other", "")) == (car.colour, car.colour_other):
        kept.pop("colour", None)
        kept.pop("colour_other", None)
    return kept


def _car_for_a_new_card(workshop, typed, answers):
    """The car a new job card is for, saved with what was typed on it (JOB-14).

    The plate finds its car, by its plate today or an old one (KNOWN-1). A car with that plate
    today and an open job card is refused first (JOB-4). An old plate always asks first, and
    so does another brand (KNOWN-10) or a VIN saved on another car (KNOWN-11, KNOWN-12). A box
    left empty changes nothing.
    """
    plate = tidy_plate(typed["plate"])
    brand, car_model = typed["brand"], typed["car_model"]
    filled = {box: typed[box] for box in CAR_OWN_BOXES if typed.get(box)}

    car = car_for_plate(workshop, plate)
    if car is not None:
        old = car.plate != plate
        if not old:
            _refuse_a_second_open_card(workshop, car)
        if (old or _another_brand(workshop, car, brand)) and _is_another_car(
            workshop, car, plate, answers
        ):
            filled = _not_what_it_holds(filled, car)
            car = None
        elif old:
            _refuse_a_second_open_card(workshop, car)

    car = _car_by_its_vin(
        workshop, filled.get("vin", ""), car, brand, plate, answers, alone=car is None
    )
    if car is None:
        return change_car(workshop, new_car(workshop, plate, brand, car_model), filled)
    return change_car(
        workshop, car, {"plate": plate, "brand": brand, "car_model": car_model, **filled}
    )


def _moved_onto(workshop, card, target, plate, shown, answers):
    """The car a card moves to takes the plate typed, and nothing else from boxes that showed
    another car (KNOWN-14).

    A car with no other visit was typed for the car in front of you, so what it holds goes
    into the boxes the target has empty, never over what the target holds (KNOWN-16). It gives
    up the plate and the VIN first, so neither is ever on two cars. A VIN typed in this save
    may be on a third car, which asks first (KNOWN-11, KNOWN-12).
    """
    car = card.car
    changes = {"plate": plate}
    if not has_other_visits(workshop, car, card):
        if shown["chassis_code"] and not target.chassis_code:
            changes["chassis_code"] = shown["chassis_code"]
        if shown["colour"] and not target.colour:
            changes["colour"] = shown["colour"]
            changes["colour_other"] = shown["colour_other"]
        if shown["vin"] and not target.vin:
            if car.vin == shown["vin"]:
                empty_vin(workshop, car)
            else:
                _car_by_its_vin(
                    workshop,
                    shown["vin"],
                    target,
                    shown["brand"],
                    plate,
                    answers,
                    alone=False,
                    card=card,
                )
            changes["vin"] = shown["vin"]
    if car.plate == plate:
        empty_plate(workshop, car)
    return change_car(workshop, target, changes)


def _car_after_changes(workshop, card, car_changes, answers):
    """The car an open job card is on after this save, with what this person changed on it
    saved (JOB-12, JOB-43).

    A plate that names another car moves the card there (KNOWN-14). A plate that names no car
    is the car's new plate, or another car's (KNOWN-15). Another brand on a car with other
    visits asks first (KNOWN-10), and so does a VIN saved on another car (KNOWN-11). Each move
    asks first, and the answers come back with the next send (KNOWN-13).
    """
    car = card.car
    # The car's boxes as the page shows them: the car's own, with what this person changed.
    shown = {
        "brand": car.car_model.brand.name,
        "car_model": car.car_model.name,
        "chassis_code": car.chassis_code,
        "vin": car.vin,
        "colour": car.colour,
        "colour_other": car.colour_other,
        **car_changes,
    }
    plate = tidy_plate(car_changes.get("plate", card.plate))
    target = car  # the car the card ends on; None for a new car

    if "plate" in car_changes and plate != car.plate:
        other = car_for_plate(workshop, plate)
        old = other is not None and other.plate != plate
        if other == car or (old and _answered(answers, "move", "another", other)):
            # Its own old plate, or another car's, which takes nothing from that car.
            other = None
        if other is not None:
            moving = _answered(answers, "move", "move", other)
            # An old plate asks first, because "another car" takes nothing from that car.
            if moving or not old:
                _refuse_a_second_open_card(workshop, other)
            if not moving:
                raise _ask(workshop, "move", other, plate, card=card)
            target = other
        elif has_other_visits(workshop, car, card):
            if _answered(answers, "plate", "another", car):
                target = None
            elif not _answered(answers, "plate", "new", car):
                raise _ask(workshop, "plate", car, plate, card=card)

    if (
        "brand" in car_changes
        and target == car
        and _another_brand(workshop, car, car_changes["brand"])
        and has_other_visits(workshop, car, card)
        and _is_another_car(workshop, car, plate, answers, card=card)
    ):
        target = None

    # A card moving to another car asks about a typed VIN only if that car takes it, below.
    if car_changes.get("vin") and (target is None or target == car):
        alone = target is None or not has_other_visits(workshop, car, card)
        target = _car_by_its_vin(
            workshop,
            car_changes["vin"],
            target,
            shown["brand"],
            plate,
            answers,
            alone=alone,
            card=card,
        )

    if target is None:
        # The brand and model shown, and only what was typed: the rest shows the car it leaves
        # (KNOWN-16).
        typed = {box: car_changes[box] for box in CAR_OWN_BOXES if box in car_changes}
        return change_car(
            workshop, new_car(workshop, plate, shown["brand"], shown["car_model"]), typed
        )
    if target != car:
        return _moved_onto(workshop, card, target, plate, shown, answers)
    return change_car(workshop, car, car_changes)


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


def make_job_card(
    workshop, branch, key, by, *, typed, concerns=(), job_lines=(), answers=frozenset()
):
    """Makes a job card once, with its car, customer, number, rows and steps, however many
    times the form is sent (JOB-42). It answers with the card saved.

    The counter's lock comes first, and the question whether the key is saved comes after
    it, because a second tap waits at that lock. So a double tap uses no number (JOB-6). A
    refusal or a question undoes all of it, so a save that stops uses no number either
    (KNOWN-13). `answers` are the answers to questions this form already asked.
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

        car = _car_for_a_new_card(workshop, typed, answers)
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
    """The job card with this key, locked until the transaction ends. It joins nothing, so a
    save that waited here reads the card's car afterwards, as the first save left it."""
    return get_object_or_404(
        JobCard.objects.for_workshop(workshop).for_branch(branch).select_for_update(),
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
    answers=frozenset(),
):
    """Applies only what this person changed since opening the page, in one locked
    transaction (JOB-43). So a tablet left open all morning can never put back Office's fix
    or a concern's old status. A repeat changes nothing more (JOB-37, JOB-41).

    A change of the car's boxes can move the card to the right car, after asking (KNOWN-14,
    KNOWN-15), and a car the move leaves with no job card is removed (KNOWN-16). A question
    undoes all of it, and `answers` are the answers to questions this form already asked.
    """
    with transaction.atomic():
        card = _locked(workshop, branch, key)
        if not card.is_open:
            raise ValidationError(_("This job card is cancelled, so nothing was saved."))

        left = None
        car_changes = {box: changes[box] for box in CAR_BOXES if box in changes}
        if car_changes:
            car = _car_after_changes(workshop, card, car_changes, answers)
            if car != card.car:
                left = card.car
            card.car = car
            card.plate = car.plate
        _change_customer(card, changes)
        for box in CARD_BOXES:
            if box in changes:
                setattr(card, box, changes[box])
        if changes:
            card.full_clean()
            try:
                # Its own savepoint, so the refusal below can still ask the database.
                with transaction.atomic():
                    card.save()
            except IntegrityError:
                # The car had no open card when it was checked, then another send made one.
                _refuse_a_second_open_card(workshop, card.car)
                raise
        if left is not None:
            remove_if_unused(workshop, left)
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

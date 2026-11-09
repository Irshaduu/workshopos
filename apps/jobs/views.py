"""Pages of jobs: thin, from the request to the forms, a service and the answer (ADR-0005).

A GET on an address that saves shows a real page: a session can end while someone saves, and
signing in brings them back with a GET (SIGN-38).
"""

import uuid

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.views.decorators.http import require_GET, require_http_methods

from apps.accounts.decorators import page
from apps.accounts.menu import on_the_tab_bar
from apps.jobs.forms import CancelForm, CardForms
from apps.jobs.selectors import (
    cancelled_step,
    job_card,
    known_car,
    open_job_cards,
    saved_job_card,
)
from apps.jobs.services import (
    CarHasOpenCard,
    Question,
    RowRefused,
    cancel_job_card,
    change_job_card,
    make_job_card,
)
from apps.vehicles.models import plate_problem, tidy_plate


@page("live_board", "jobs.see_live_board")
@require_GET
def live_board(request):
    """The first, plain live board, so a card can be found (JOB-61). Its New shows unless the
    tab bar already has one (JOB-62)."""
    context = {
        "cards": open_job_cards(request.workshop, request.branch),
        "new_on_the_bar": on_the_tab_bar(request, "jobs:new"),
    }
    return render(request, "jobs/live_board.html", context)


@page("job_card", "jobs.save_job_card")
@require_http_methods(["GET", "POST"])
def job_card_new(request):
    """The form for a new card, with the new record's key in its address (JOB-42). A send with
    no key has nothing to save under, so it starts again."""
    if request.method == "POST":
        return redirect("jobs:new")
    forms = CardForms.of(request.user, request.workshop, request.branch)
    return _card_page(request, forms, new_key=uuid.uuid7())


@page("known_plate", "jobs.see_known_plate")
@require_GET
def known_plate(request):
    """What the workshop knows about a typed plate, as a part of the job card's page (KNOWN-4,
    KNOWN-19). The customer comes only for a role whose form has the customer (KNOWN-8)."""
    known = _known_for(request, request.GET.get("plate", ""))
    return render(request, "jobs/job_card.html#known_plate", {"known": known})


@page("job_card", "jobs.save_job_card")
@require_http_methods(["GET", "POST"])
def job_card_create(request, key):
    """Makes a job card, once (JOB-42). A save that asks first shows its question (KNOWN-13)."""
    # First, because the form's checks would refuse a repeat as a second open card.
    saved = saved_job_card(request.workshop, request.branch, key)
    if saved is not None:
        return _repeat(request, saved) if request.method == "POST" else _open(saved)
    if request.method == "GET":
        return redirect("jobs:new")
    forms = CardForms.of(request.user, request.workshop, request.branch, data=request.POST)
    answers = request.POST.getlist("answers")
    stopped = {}
    if forms.is_valid():
        try:
            card = make_job_card(
                request.workshop,
                request.branch,
                key,
                request.user,
                typed=forms.main.cleaned_data,
                concerns=forms.concerns.new_rows(),
                job_lines=forms.job_lines.new_rows(),
                answers=answers,
            )
        except Question as asked:
            stopped = {"question": asked}
        except CarHasOpenCard as refused:
            stopped = {"open_card": refused.card, "open_card_box": refused.box}
            forms.refuse(refused)
        except ValidationError as refused:
            forms.refuse(refused)
        else:
            return _made(request, card)
    return _card_page(request, forms, new_key=key, answers=answers, **stopped)


@page("job_card", "jobs.save_job_card")
@require_http_methods(["GET", "POST"])
def job_card_edit(request, key):
    """A job card: its page, and saving what this person changed (JOB-43, JOB-45)."""
    card = job_card(request.workshop, request.branch, key)
    data = request.POST if request.method == "POST" and card.is_open else None
    forms = CardForms.of(request.user, request.workshop, request.branch, card=card, data=data)
    if request.method == "GET":
        return _card_page(request, forms, card=card)
    if not card.is_open:
        messages.error(request, _("This job card is cancelled, so nothing was saved."))
        return _open(card)
    answers = request.POST.getlist("answers")
    stopped = {}
    if forms.is_valid():
        try:
            saved = change_job_card(
                request.workshop,
                request.branch,
                key,
                request.user,
                changes=forms.main.changes(),
                saved_concerns=forms.concerns.saved_changes(),
                new_concerns=forms.concerns.new_rows(),
                saved_lines=forms.job_lines.saved_changes(),
                new_lines=forms.job_lines.new_rows(),
                answers=answers,
            )
        except Question as asked:
            stopped = {"question": asked}
        except CarHasOpenCard as refused:
            stopped = {"open_card": refused.card, "open_card_box": refused.box}
            forms.refuse(refused)
        except RowRefused as refused:
            forms.refuse_row(refused)
        except ValidationError as refused:
            forms.refuse(refused)
        else:
            messages.success(request, _("%(plate)s updated.") % {"plate": saved.plate})
            return _open(card)
    return _card_page(request, forms, card=card, answers=answers, **stopped)


@page("job_card", "jobs.cancel_job_card")
@require_http_methods(["GET", "POST"])
def job_card_cancel(request, key):
    """Cancels a job card, after asking, with a reason (JOB-50)."""
    card = job_card(request.workshop, request.branch, key)
    forms = CardForms.of(request.user, request.workshop, request.branch, card=card)
    if request.method == "GET":
        return _card_page(request, forms, card=card)
    if not card.is_open:
        return _open(card)
    cancel_form = CancelForm(request.POST)
    if not cancel_form.is_valid():
        return _card_page(request, forms, card=card, cancel_form=cancel_form)
    cancel_job_card(
        request.workshop, request.branch, key, request.user, cancel_form.cleaned_data["reason"]
    )
    messages.success(request, _("%(number)s cancelled.") % {"number": card.number})
    return _open(card)


def _open(card):
    return redirect("jobs:edit", key=card.pk)


def _made(request, card):
    """The card stays open, with its notice (JOB-45)."""
    messages.success(
        request,
        _("Job card %(number)s saved for %(plate)s.")
        % {"number": card.number, "plate": card.plate},
    )
    return _open(card)


def _repeat(request, saved):
    """A send whose key is already saved (JOB-42). The same plate is a double tap, and gets the
    same notice. Another plate came from an old form, like a page brought back by Back: it was
    not saved, and the notice must say so."""
    typed = tidy_plate(request.POST.get("plate", ""))
    if not typed or typed == saved.plate:
        return _made(request, saved)
    messages.warning(
        request,
        _("This form already made job card %(number)s, so %(plate)s was not saved. Start it again.")
        % {"number": saved.number, "plate": typed},
    )
    return _open(saved)


def _known_for(request, typed):
    """What the workshop knows about a typed plate (KNOWN-1): nothing for what cannot be a plate,
    and the customer only for a role whose form has the customer (KNOWN-8). A form sent with no
    plate box at all has None here."""
    plate = tidy_plate(typed or "")
    if plate_problem(plate):
        return None
    return known_car(
        request.workshop,
        plate,
        with_customer=request.user.has_perm("jobs.save_customer_and_labour"),
    )


def _card_page(
    request,
    forms,
    *,
    card=None,
    new_key=None,
    open_card=None,
    open_card_box=None,
    question=None,
    answers=(),
    cancel_form=None,
):
    """The one page of a job card, new, saved, refused, asking or cancelled."""
    bound = forms.main.is_bound
    problems = forms.problems() if bound else []
    context = {
        "card": card,
        "new_key": new_key,
        "forms": forms,
        "form": forms.main,
        "problems": problems,
        "problems_word": ngettext(
            "Not saved: %(count)d thing to fix. Nothing you typed was lost.",
            "Not saved: %(count)d things to fix. Nothing you typed was lost.",
            len(problems),
        )
        % {"count": len(problems)},
        "question": question,
        # The answers given come back only with the next question. A refused save forgets them,
        # so each can be given again, differently (KNOWN-13).
        "kept_answers": answers if question is not None else (),
        # A page that comes back keeps what the plate found (KNOWN-5, KNOWN-7, KNOWN-9).
        "known": _known_for(request, forms.main["plate"].value()) if new_key and bound else None,
        "open_card": open_card,
        "open_card_box": open_card_box,
        "cancel_form": cancel_form or CancelForm(),
        "cancelled": (
            cancelled_step(request.workshop, card)
            if card is not None and not card.is_open
            else None
        ),
        "locked": card is not None and not card.is_open,
    }
    return render(request, "jobs/job_card.html", context)

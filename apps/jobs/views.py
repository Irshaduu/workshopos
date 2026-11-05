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
from apps.jobs.selectors import cancelled_step, job_card, open_job_cards, saved_job_card
from apps.jobs.services import (
    CarHasOpenCard,
    RowRefused,
    cancel_job_card,
    change_job_card,
    make_job_card,
)
from apps.vehicles.models import tidy_plate


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


@page("job_card", "jobs.save_job_card")
@require_http_methods(["GET", "POST"])
def job_card_create(request, key):
    """Makes a job card, once (JOB-42)."""
    # First, because the form's checks would refuse a repeat as a second open card.
    saved = saved_job_card(request.workshop, request.branch, key)
    if saved is not None:
        return _repeat(request, saved) if request.method == "POST" else _open(saved)
    if request.method == "GET":
        return redirect("jobs:new")
    forms = CardForms.of(request.user, request.workshop, request.branch, data=request.POST)
    open_card = None
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
            )
        except CarHasOpenCard as refused:
            open_card = refused.card
            forms.refuse(refused)
        except ValidationError as refused:
            forms.refuse(refused)
        else:
            return _made(request, card)
    return _card_page(request, forms, new_key=key, open_card=open_card)


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
            )
        except RowRefused as refused:
            forms.refuse_row(refused)
        except ValidationError as refused:
            forms.refuse(refused)
        else:
            messages.success(request, _("%(plate)s updated.") % {"plate": saved.plate})
            return _open(card)
    return _card_page(request, forms, card=card)


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


def _card_page(request, forms, *, card=None, new_key=None, open_card=None, cancel_form=None):
    """The one page of a job card, new, saved, refused or cancelled."""
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
        # A link to the open card only when it is in this branch: another branch's is
        # never found (JOB-4).
        "open_card": open_card if open_card and open_card.branch_id == request.branch.pk else None,
        "cancel_form": cancel_form or CancelForm(),
        "cancelled": (
            cancelled_step(request.workshop, card)
            if card is not None and not card.is_open
            else None
        ),
        "locked": card is not None and not card.is_open,
    }
    return render(request, "jobs/job_card.html", context)

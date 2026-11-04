"""Pages of staff: thin, from the request to a form, a service and the answer (ADR-0005).

One page, the list, and four addresses that save. A GET on an address that saves goes
to the list: a session can end while someone saves, and signing in brings them back
with a GET (SIGN-38), so it must not be a dead end.
"""

import uuid

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods

from apps.accounts.decorators import page
from apps.staff.forms import StaffMemberForm
from apps.staff.models import Designation, tidy_name
from apps.staff.selectors import saved_staff_member, staff_by_designation, staff_member
from apps.staff.services import add_staff_member, change_staff_member, turn_off, turn_on

#: v1's icon for each designation's card.
ICONS = {
    Designation.MECHANIC: "star",
    Designation.ASSISTANT_MECHANIC: "star-half",
    Designation.OFFICE_STAFF: "building",
    Designation.GENERAL_HELPER: "id-card",
}


@page("staff_list", "staff.see_staff_list")
@require_GET
def staff_list(request):
    """The list, with a new record's key in the add form's address (STAFF-9)."""
    return _list_page(request, uuid.uuid7(), StaffMemberForm())


@page("staff_list", "staff.save_staff_member")
@require_http_methods(["GET", "POST"])
def staff_new(request, key):
    """Adds a staff member, once (STAFF-8, STAFF-9)."""
    if request.method == "GET":
        return redirect("staff:list")
    # First, because the form's checks would refuse a repeat as a taken name.
    saved = saved_staff_member(request.workshop, request.branch, key)
    if saved is not None:
        return _repeat(request, saved)
    form = StaffMemberForm(request.POST)
    if form.is_valid():
        try:
            member = add_staff_member(request.workshop, request.branch, key, **form.cleaned_data)
        except ValidationError as refused:
            form.add_error("name", refused.messages)
        else:
            return _added(request, member)
    return _list_page(request, key, form)


@page("staff_list", "staff.save_staff_member")
@require_http_methods(["GET", "POST"])
def staff_edit(request, key):
    """Changes a staff member's name and designation (STAFF-10)."""
    staff_member(request.workshop, request.branch, key)
    if request.method == "GET":
        return redirect("staff:list")
    form = StaffMemberForm(request.POST)
    if form.is_valid():
        try:
            member = change_staff_member(request.workshop, request.branch, key, **form.cleaned_data)
        except ValidationError as refused:
            form.add_error("name", refused.messages)
        else:
            messages.success(request, _("%(name)s updated.") % {"name": member.name})
            return redirect("staff:list")
    return _list_page(request, uuid.uuid7(), StaffMemberForm(), key, form)


@page("staff_list", "staff.save_staff_member")
@require_http_methods(["GET", "POST"])
def staff_turn_off(request, key):
    """Turns a staff member off. It asks no question: Turn on undoes it (STAFF-14)."""
    return _turn(request, key, turn_off, _("%(name)s turned off."))


@page("staff_list", "staff.save_staff_member")
@require_http_methods(["GET", "POST"])
def staff_turn_on(request, key):
    """Turns a staff member back on (STAFF-13)."""
    return _turn(request, key, turn_on, _("%(name)s turned on."))


def _turn(request, key, turn, done):
    """A send turns the person off or on, and the service finds them. A GET only asks
    that they are this branch's, so anyone else is "not found" either way (STAFF-4)."""
    if request.method == "POST":
        member = turn(request.workshop, request.branch, key)
        messages.success(request, done % {"name": member.name})
    else:
        staff_member(request.workshop, request.branch, key)
    return redirect("staff:list")


def _added(request, member):
    """The list, with its notice."""
    messages.success(request, _("%(name)s added.") % {"name": member.name})
    return redirect("staff:list")


def _repeat(request, saved):
    """A send whose key is already saved (STAFF-9). The same name is a double tap, and
    gets the same notice. Another name came from an old form, like a page brought back
    by Back: that person was not saved, and the notice must say so."""
    typed = tidy_name(request.POST.get("name", ""))
    if not typed or typed.lower() == saved.name.lower():
        return _added(request, saved)
    messages.warning(
        request,
        _("This form already added %(saved)s, so %(typed)s was not saved. Add %(typed)s again.")
        % {"saved": saved.name, "typed": typed},
    )
    return redirect("staff:list")


def _list_page(request, add_key, add_form, edit_key=None, edit_form=None):
    """The page (STAFF-20). A refused form comes back with its error and what was typed
    (STAFF-24): the add form here, or the one person's Edit card, open by itself
    (STAFF-23)."""

    def row(member):
        form = edit_form if member.pk == edit_key else StaffMemberForm(instance=member)
        return {"member": member, "form": form}

    cards = [
        {
            "word": designation.label,
            "icon": ICONS[designation],
            "rows": [row(member) for member in members],
        }
        for designation, members in staff_by_designation(request.workshop, request.branch)
    ]
    context = {
        "cards": cards,
        "add_key": add_key,
        "add_form": add_form,
        "designations": Designation.choices,
    }
    return render(request, "staff/staff_list.html", context)

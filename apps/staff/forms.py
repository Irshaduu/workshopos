"""Checks what was typed on the Staff list (ADR-0005)."""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.staff.models import StaffMember


class StaffMemberForm(forms.ModelForm):
    """Adding or changing a staff member: only what an owner may change here.

    The name's one rule this form cannot check, that it is free in the branch, comes
    from the service, because the form never holds the workshop or the branch.
    """

    class Meta:
        model = StaffMember
        fields = ["name", "designation"]
        error_messages = {
            "name": {"required": _("Type a name.")},
            "designation": {"required": _("Choose a designation.")},
        }

"""Checks what was typed on the sign-in pages (ADR-0005)."""

import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class WhoForm(forms.Form):
    """Step 1, for every role: an email or a username (SIGN-2)."""

    who = forms.CharField(label=_("Email or username"), max_length=254)

    def is_email(self):
        """An email goes on to a code; a username to a password (SIGN-2)."""
        return "@" in self.cleaned_data["who"]


class CodeForm(forms.Form):
    """An owner's 6-digit code. Spaces are dropped, so 482 915 is 482915."""

    code = forms.CharField(label=_("6-digit code"), max_length=20)

    def clean_code(self):
        code = "".join(self.cleaned_data["code"].split())
        # Refused here, before the code is checked, so it spends no try.
        if not re.fullmatch(r"[0-9]{6}", code):
            raise ValidationError(_("The code has 6 digits."))
        return code


class PasswordForm(forms.Form):
    """Office and Floor's password. Never typed back into the page (SIGN-11)."""

    password = forms.CharField(label=_("Password"), strip=False)

"""Pages of accounts: thin, from the request to a form, a service and the answer (ADR-0005).

Signing in is one page in steps (ADR-0025): step 1 takes an email or a
username, then an owner types a code and Office or Floor a password. Each
step has its own address, and a form that went through answers with a
redirect, so Back or refresh never sends it again.
"""

import math
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_not_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_http_methods

from apps.accounts.forms import CodeForm, PasswordForm, WhoForm
from apps.accounts.selectors import (
    CODE_GAP,
    CODE_TIME,
    CODES_PER_HOUR,
    WRONG_CODES,
    account_by_username,
    code_tries_left,
    minutes_locked,
)
from apps.accounts.services import CodeNotSent, send_sign_in_code

# What the browser's session keeps between the steps, under one key that is
# removed at sign-in: what was typed ("who"), the step it reached, the page
# first asked for ("next"), and on the code step the code's id ("code"),
# when it was asked for ("asked_at"), and the wrong tries of an email with
# no code behind it ("wrong").
PENDING = "sign_in"

# This browser's code requests in the last hour (SIGN-21), kept apart, so a
# new email typed in step 1 does not wipe them.
ASKED = "sign_in_codes_asked"


@login_not_required  # The first step of signing in: nobody is signed in yet.
@never_cache
@require_http_methods(["GET", "POST"])
def sign_in(request):
    """Step 1, for every role (SIGN-1): an email goes on to a code, a username to a
    password (SIGN-2)."""
    if request.user.is_authenticated:
        return redirect("accounts:home")
    pending = request.session.get(PENDING, {})
    if request.method == "POST":
        form = WhoForm(request.POST)
        if form.is_valid():
            who = form.cleaned_data["who"]
            next_url = request.POST.get("next", "")
            if form.is_email():
                return _ask_for_code(request, who, next_url)
            request.session[PENDING] = {"who": who, "step": "password", "next": next_url}
            return redirect("accounts:sign_in_password")
    else:
        form = WhoForm(initial={"who": pending.get("who", "")})
    next_url = request.GET.get("next") or pending.get("next", "")
    return render(request, "accounts/sign_in.html", {"form": form, "next": next_url})


@login_not_required  # A step of signing in: nobody is signed in yet.
@never_cache
@sensitive_post_parameters("code")
@require_http_methods(["GET", "POST"])
def sign_in_code(request):
    """Step 2 for an owner: the 6-digit code from the email (SIGN-3, SIGN-22, SIGN-23)."""
    if request.user.is_authenticated:
        return redirect("accounts:home")
    pending = request.session.get(PENDING, {})
    if pending.get("step") != "code":
        return redirect("accounts:sign_in")  # SIGN-26
    form = CodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        code = form.cleaned_data["code"]
        if pending["code"]:
            owner = authenticate(request, sign_in_code_id=pending["code"], code=code)
            if owner is not None:
                return _signed_in(request, owner)
            left = code_tries_left(pending["code"])
        else:
            # No code went out for this email. It is answered as a real code
            # would be, so this step never tells who has an account (SIGN-15).
            pending["wrong"] += 1
            request.session[PENDING] = pending
            left = _tries_left_without_a_code(pending)
        if not left:
            # Used, too old, or guessed wrong 5 times: back to step 1, with
            # the email kept (SIGN-16, SIGN-22).
            request.session[PENDING] = {"who": pending["who"], "next": pending["next"]}
            messages.error(
                request, _("That code no longer works. Press Continue to get a new one.")
            )
            return redirect("accounts:sign_in")
        form.add_error(
            "code",
            ngettext("Wrong code. %(left)d try left.", "Wrong code. %(left)d tries left.", left)
            % {"left": left},
        )
    context = {
        "form": form,
        "email": pending["who"],
        "next": pending["next"],
        "minutes": int(CODE_TIME.total_seconds() // 60),
    }
    return render(request, "accounts/sign_in_code.html", context)


@login_not_required  # A step of signing in: nobody is signed in yet.
@never_cache
@sensitive_post_parameters("password")
@require_http_methods(["GET", "POST"])
def sign_in_password(request):
    """Step 2 for Office and Floor: the password (SIGN-6, SIGN-11, SIGN-33)."""
    if request.user.is_authenticated:
        return redirect("accounts:home")
    pending = request.session.get(PENDING, {})
    if pending.get("step") != "password":
        return redirect("accounts:sign_in")
    username = pending["who"]
    form = PasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid() and not _said_locked(request, username):
        account = authenticate(request, username=username, password=form.cleaned_data["password"])
        if account is not None:
            return _signed_in(request, account)
        # This wrong password may have just locked it: then say so at once.
        if not _said_locked(request, username):
            form.add_error("password", _("Wrong username or password."))
    return render(request, "accounts/sign_in_password.html", {"form": form, "username": username})


@require_GET
def home(request):
    """The page after signing in. For now it shows who is signed in, and where;
    Roles (step 2 of Slice 1) brings v1's top bar and menu."""
    return render(request, "accounts/home.html")


def _ask_for_code(request, email, next_url):
    """Sends a code, unless this browser asked too often (SIGN-15, SIGN-21, SIGN-25)."""
    pending = request.session.get(PENDING, {})
    wait = _too_often(request)
    if wait:
        # No code is sent. The code step shows when this browser can ask
        # again; for the same email, the code it holds still works.
        same = pending.get("step") == "code" and pending["who"].lower() == email.lower()
        request.session[PENDING] = (
            {**pending, "next": next_url} if same else _code_step(email, next_url, None)
        )
        messages.warning(request, wait)
        return redirect("accounts:sign_in_code")
    _log_ask(request)
    try:
        record = send_sign_in_code(email)
    except CodeNotSent:
        # Said plainly, and this try counts towards no limit (SIGN-25).
        _forget_last_ask(request)
        request.session[PENDING] = {"who": email, "next": next_url}
        messages.error(
            request,
            _(
                "The email did not go out, so no code was sent. Try again in a moment. "
                "If it keeps happening, tell your developer."
            ),
        )
        return redirect("accounts:sign_in")
    request.session[PENDING] = _code_step(email, next_url, record)
    messages.info(
        request,
        _(
            "If this email belongs to an owner, a 6-digit code is on its way. "
            "You can ask for a new code once a minute."
        ),
    )
    return redirect("accounts:sign_in_code")


def _code_step(email, next_url, record):
    return {
        "who": email,
        "step": "code",
        "next": next_url,
        "code": str(record.pk) if record else None,
        "asked_at": timezone.now().isoformat(),
        "wrong": 0,
    }


def _tries_left_without_a_code(pending):
    """For an email with no code behind it: the tries a real code would have
    left, and none after the 10 minutes a real code lasts (SIGN-15)."""
    if timezone.now() - parse_datetime(pending["asked_at"]) >= CODE_TIME:
        return 0
    return max(0, WRONG_CODES - pending["wrong"])


def _codes_asked(request):
    """This browser's code requests in the last hour, oldest first (SIGN-21)."""
    now = timezone.now()
    times = [parse_datetime(value) for value in request.session.get(ASKED, [])]
    return sorted(time for time in times if time and now - time < timedelta(hours=1))


def _too_often(request):
    """What to say when this browser asked too often; None when it may ask (SIGN-21).

    It counts this browser only, never the account, so it cannot tell who has
    an account. The account's own limits stay underneath, unseen (SIGN-20).
    """
    asked = _codes_asked(request)
    now = timezone.now()
    if asked and now - asked[-1] < CODE_GAP:
        seconds = math.ceil((asked[-1] + CODE_GAP - now).total_seconds())
        return ngettext(
            "A code was asked for on this device a moment ago. "
            "You can ask for another in %(seconds)d second.",
            "A code was asked for on this device a moment ago. "
            "You can ask for another in %(seconds)d seconds.",
            seconds,
        ) % {"seconds": seconds}
    if len(asked) >= CODES_PER_HOUR:
        minutes = math.ceil((asked[0] + timedelta(hours=1) - now).total_seconds() / 60)
        return ngettext(
            "%(count)d codes were asked for on this device in the last hour. "
            "You can ask for another in %(minutes)d minute.",
            "%(count)d codes were asked for on this device in the last hour. "
            "You can ask for another in %(minutes)d minutes.",
            minutes,
        ) % {"count": len(asked), "minutes": minutes}
    return None


def _log_ask(request):
    request.session[ASKED] = [time.isoformat() for time in [*_codes_asked(request), timezone.now()]]


def _forget_last_ask(request):
    request.session[ASKED] = [time.isoformat() for time in _codes_asked(request)[:-1]]


def _said_locked(request, username):
    """Says on the page that the account is locked, and for how long (SIGN-33).

    True when it is. This tells a stranger that the account exists; v1
    accepted that, so a locked person knows why.
    """
    account = account_by_username(username)
    minutes = minutes_locked(account) if account else 0
    if minutes:
        messages.error(
            request,
            ngettext(
                "Too many wrong passwords. Try again in %(minutes)d minute.",
                "Too many wrong passwords. Try again in %(minutes)d minutes.",
                minutes,
            )
            % {"minutes": minutes},
        )
    return bool(minutes)


def _signed_in(request, account):
    """Signs the account in on this device, then opens the page first asked
    for, if it is on this site; otherwise the home page (SIGN-13)."""
    next_url = request.session.get(PENDING, {}).get("next", "")
    request.session.pop(PENDING, None)
    request.session.pop(ASKED, None)
    login(request, account)
    on_this_site = url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )
    return redirect(next_url if on_this_site else "accounts:home")

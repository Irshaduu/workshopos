"""The developer's sign-in code by phone (apps/accounts/management/commands/sign_in_code.py)."""

import io
import re

import pytest
from django.core import mail
from django.core.management import CommandError, call_command

from apps.accounts.models import SignInCode
from apps.accounts.selectors import tries_left
from apps.accounts.services import check_sign_in_code, code_hash, send_sign_in_code
from apps.accounts.tests.factories import MembershipFactory

OWNER_EMAIL = "ravi@example.com"


@pytest.fixture
def owner():
    return MembershipFactory(owner=True, user__email=OWNER_EMAIL).user


def phoned_code(email):
    out = io.StringIO()
    call_command("sign_in_code", email, stdout=out)
    return re.match(r"Code (\d{6}), for the browser that asked at", out.getvalue()).group(1)


@pytest.mark.django_db
def test_sign_28_the_code_by_phone_works_for_the_code_the_owners_browser_holds(owner):
    record = send_sign_in_code(OWNER_EMAIL)
    emailed = re.match(r"\d{6}", mail.outbox[-1].subject).group()

    phoned = phoned_code(OWNER_EMAIL)

    record.refresh_from_db()
    assert record.code_hash == code_hash(phoned)
    assert record.code_hash != code_hash(emailed)
    assert check_sign_in_code(record.pk, phoned) == owner


@pytest.mark.django_db
def test_sign_28_the_code_by_phone_spends_no_limit_and_starts_its_tries_again(owner):
    record = send_sign_in_code(OWNER_EMAIL)
    for _ in range(3):
        check_sign_in_code(record.pk, "abcdef")

    phoned_code(OWNER_EMAIL)

    record.refresh_from_db()
    assert tries_left(record) == 5
    assert SignInCode.objects.count() == 1


@pytest.mark.django_db
def test_sign_28_with_no_open_code_the_command_says_what_to_do(owner):
    with pytest.raises(CommandError, match="type their email on the sign-in page first"):
        phoned_code(OWNER_EMAIL)


@pytest.mark.django_db
def test_sign_28_an_email_with_no_owner_gets_no_code():
    with pytest.raises(CommandError):
        phoned_code("nobody@example.com")

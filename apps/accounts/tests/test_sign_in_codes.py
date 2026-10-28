"""Sign-in codes for owners (apps/accounts/services.py, selectors.py and backends.py)."""

import hashlib
import re
from datetime import timedelta

import pytest
from django.contrib.auth import authenticate
from django.core import mail
from django.core.mail.backends.base import BaseEmailBackend

from apps.accounts.models import SignInCode
from apps.accounts.selectors import tries_left
from apps.accounts.services import (
    CodeNotSent,
    check_sign_in_code,
    code_hash,
    send_sign_in_code,
)
from apps.accounts.tests.factories import MembershipFactory

OWNER_EMAIL = "ravi@example.com"


class BrokenMailer(BaseEmailBackend):
    """A mail service that is down."""

    def send_messages(self, email_messages):
        raise OSError("The mail service is down.")


@pytest.fixture
def owner():
    return MembershipFactory(owner=True, workshop__name="Workshop A", user__email=OWNER_EMAIL).user


def code_in_last_email():
    return re.fullmatch(r"(\d{6}) is your sign-in code", mail.outbox[-1].subject).group(1)


def made_minutes_ago(record, minutes):
    record.created_at -= timedelta(minutes=minutes)
    record.ends_at -= timedelta(minutes=minutes)
    record.save()


def wrong_code(right):
    return "000000" if right != "000000" else "111111"


@pytest.mark.django_db
def test_sign_15_only_a_turned_on_owner_gets_a_code(owner):
    office = MembershipFactory(user__email="office@example.com").user
    turned_off = MembershipFactory(owner=True, user__is_active=False).user

    assert send_sign_in_code(OWNER_EMAIL) is not None
    assert send_sign_in_code(office.email) is None
    assert send_sign_in_code(turned_off.email) is None
    assert send_sign_in_code("nobody@example.com") is None
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_sign_10_an_email_in_any_capitals_finds_its_owner(owner):
    assert send_sign_in_code(" Ravi@EXAMPLE.com ").user == owner


@pytest.mark.django_db
def test_sign_16_the_code_has_6_digits_and_works_once(owner):
    record = send_sign_in_code(OWNER_EMAIL)
    code = code_in_last_email()

    assert check_sign_in_code(record.pk, code) == owner
    assert check_sign_in_code(record.pk, code) is None


@pytest.mark.django_db
def test_sign_16_the_code_ends_after_10_minutes(owner):
    record = send_sign_in_code(OWNER_EMAIL)
    made_minutes_ago(record, 10)

    assert check_sign_in_code(record.pk, code_in_last_email()) is None


@pytest.mark.django_db
def test_sign_16_a_code_works_only_for_the_code_its_browser_holds(owner):
    other = MembershipFactory(owner=True).user
    record = send_sign_in_code(OWNER_EMAIL)
    code = code_in_last_email()
    elsewhere = send_sign_in_code(other.email)

    assert check_sign_in_code(elsewhere.pk, code) is None
    assert check_sign_in_code(record.pk, code) == owner


@pytest.mark.django_db
def test_sign_17_the_code_is_in_the_emails_subject_line(owner):
    send_sign_in_code(OWNER_EMAIL)

    assert re.fullmatch(r"\d{6} is your sign-in code", mail.outbox[-1].subject)


@pytest.mark.django_db
def test_sign_18_the_email_names_the_workshop_and_says_never_to_share_the_code(owner):
    send_sign_in_code(OWNER_EMAIL)

    body = mail.outbox[-1].body
    assert f"sign in to Workshop A is {code_in_last_email()}." in body
    assert "Never share this code. Nobody will ever ask you for it" in body


@pytest.mark.django_db
def test_sign_19_a_new_code_ends_the_one_before(owner):
    first = send_sign_in_code(OWNER_EMAIL)
    first_code = code_in_last_email()
    made_minutes_ago(first, 2)

    second = send_sign_in_code(OWNER_EMAIL)

    assert check_sign_in_code(first.pk, first_code) is None
    assert check_sign_in_code(second.pk, code_in_last_email()) == owner


@pytest.mark.django_db
def test_sign_20_an_account_gets_one_code_a_minute(owner):
    send_sign_in_code(OWNER_EMAIL)

    assert send_sign_in_code(OWNER_EMAIL) is None
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_sign_20_an_account_gets_3_codes_an_hour(owner):
    for _ in range(3):
        made_minutes_ago(send_sign_in_code(OWNER_EMAIL), 20)

    assert send_sign_in_code(OWNER_EMAIL) is None

    oldest = SignInCode.objects.order_by("created_at").first()
    made_minutes_ago(oldest, 41)
    assert send_sign_in_code(OWNER_EMAIL) is not None


@pytest.mark.django_db
def test_sign_22_five_wrong_codes_end_the_code_and_each_says_how_many_tries_are_left(owner):
    record = send_sign_in_code(OWNER_EMAIL)
    code = code_in_last_email()

    for left in [4, 3, 2, 1, 0]:
        assert check_sign_in_code(record.pk, wrong_code(code)) is None
        record.refresh_from_db()
        assert tries_left(record) == left

    assert check_sign_in_code(record.pk, code) is None


@pytest.mark.django_db
def test_sign_24_the_code_is_kept_only_as_a_hash_made_with_the_secret_key(owner, settings):
    record = send_sign_in_code(OWNER_EMAIL)
    code = code_in_last_email()

    assert code not in record.code_hash
    assert record.code_hash != hashlib.sha256(code.encode()).hexdigest()
    settings.SECRET_KEY = "another server's secret key"
    assert code_hash(code) != record.code_hash


@pytest.mark.django_db
def test_sign_25_an_email_that_cannot_be_sent_leaves_no_code_and_spends_no_limit(owner, settings):
    earlier = send_sign_in_code(OWNER_EMAIL)
    earlier_code = code_in_last_email()
    made_minutes_ago(earlier, 2)
    settings.MAILERS = {"default": {"BACKEND": f"{__name__}.BrokenMailer"}}

    with pytest.raises(CodeNotSent):
        send_sign_in_code(OWNER_EMAIL)

    assert SignInCode.objects.count() == 1
    assert check_sign_in_code(earlier.pk, earlier_code) == owner


@pytest.mark.django_db
def test_sign_25_after_a_failed_email_a_new_code_can_be_asked_for_at_once(owner, settings):
    settings.MAILERS = {"default": {"BACKEND": f"{__name__}.BrokenMailer"}}
    with pytest.raises(CodeNotSent):
        send_sign_in_code(OWNER_EMAIL)
    settings.MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}

    assert send_sign_in_code(OWNER_EMAIL) is not None


@pytest.mark.django_db
def test_sign_27_the_right_code_ends_every_code_of_the_account(owner):
    record = send_sign_in_code(OWNER_EMAIL)
    other = SignInCode.objects.create(
        user=owner,
        code_hash=code_hash("123456"),
        created_at=record.created_at,
        ends_at=record.ends_at,
    )

    check_sign_in_code(record.pk, code_in_last_email())

    other.refresh_from_db()
    assert tries_left(other) == 0


@pytest.mark.django_db
def test_sign_3_an_owner_signs_in_with_the_right_code(owner):
    record = send_sign_in_code(OWNER_EMAIL)

    assert authenticate(None, sign_in_code_id=record.pk, code=code_in_last_email()) == owner


@pytest.mark.django_db
def test_sign_3_an_owner_turned_off_after_the_code_was_sent_does_not_sign_in(owner):
    record = send_sign_in_code(OWNER_EMAIL)
    owner.is_active = False
    owner.save()

    assert authenticate(None, sign_in_code_id=record.pk, code=code_in_last_email()) is None


@pytest.mark.django_db
def test_sign_3_an_account_that_is_no_longer_an_owner_does_not_sign_in_with_a_code(owner):
    record = send_sign_in_code(OWNER_EMAIL)
    MembershipFactory._meta.model.objects.filter(user=owner).update(role="office")

    assert authenticate(None, sign_in_code_id=record.pk, code=code_in_last_email()) is None

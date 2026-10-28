"""The sign-in pages (apps/accounts/views.py, forms.py, middleware.py and templates).

The rules themselves are tested at their services and backend; these tests
check the pages' wiring and what each page says.
"""

import re
from datetime import timedelta

import pytest
from django.contrib.sessions.models import Session
from django.core import mail
from django.utils import timezone

from apps.accounts.services import count_wrong_password
from apps.accounts.tests.factories import PASSWORD, MembershipFactory
from apps.workshops.tests.factories import WorkshopFactory

STEP_1 = "/sign-in/"
CODE_STEP = "/sign-in/code/"
PASSWORD_STEP = "/sign-in/password/"
HOME = "/"
OWNER_EMAIL = "ravi@example.com"
WRONG = "Wrong username or password."
BROKEN_MAILER = {"default": {"BACKEND": "apps.accounts.tests.test_sign_in_codes.BrokenMailer"}}


@pytest.fixture
def workshop():
    return WorkshopFactory(short_code="ab")


@pytest.fixture
def owner(workshop):
    return MembershipFactory(owner=True, workshop=workshop, user__email=OWNER_EMAIL).user


@pytest.fixture
def floor(workshop):
    return MembershipFactory(workshop=workshop, user__username="ab.floor").user


def code_in_last_email():
    return re.fullmatch(r"(\d{6}) is your sign-in code", mail.outbox[-1].subject).group(1)


def signed_in(client):
    return "_auth_user_id" in client.session


def page(response):
    return response.content.decode()


@pytest.mark.django_db
def test_sign_1_one_sign_in_page_names_no_role_and_links_nowhere(client):
    html = page(client.get(STEP_1))

    assert "Email or username" in html
    assert "<a " not in html
    for word in ["Owner", "Office", "Floor", "admin"]:
        assert word not in html


@pytest.mark.django_db
def test_sign_2_an_email_goes_on_to_a_code_and_a_username_to_a_password(client, owner, floor):
    assert client.post(STEP_1, {"who": OWNER_EMAIL}).url == CODE_STEP
    assert client.post(STEP_1, {"who": "ab.floor"}).url == PASSWORD_STEP


@pytest.mark.django_db
def test_sign_3_an_owner_signs_in_with_the_code_from_the_email(client, owner):
    client.post(STEP_1, {"who": OWNER_EMAIL})

    response = client.post(CODE_STEP, {"code": code_in_last_email()})

    assert response.url == HOME
    assert signed_in(client)


@pytest.mark.django_db
def test_sign_6_office_and_floor_sign_in_with_a_password(client, floor):
    client.post(STEP_1, {"who": "ab.floor"})

    response = client.post(PASSWORD_STEP, {"password": PASSWORD})

    assert response.url == HOME
    assert signed_in(client)


@pytest.mark.django_db
def test_sign_11_every_wrong_try_gets_the_same_answer(client, owner, floor):
    owner.set_password(PASSWORD)
    owner.save()
    for who, password in [
        ("ab.floor", "wrong"),
        ("ab.nobody", PASSWORD),
        (owner.username, PASSWORD),
    ]:
        client.post(STEP_1, {"who": who})
        html = page(client.post(PASSWORD_STEP, {"password": password}))

        assert WRONG in html
        assert 'value="wrong"' not in html
        assert not signed_in(client)


@pytest.mark.django_db
@pytest.mark.parametrize("step", [STEP_1, CODE_STEP, PASSWORD_STEP])
def test_sign_12_someone_already_signed_in_goes_to_the_home_page(client, floor, step):
    client.force_login(floor)

    assert client.get(step).url == HOME


@pytest.mark.django_db
def test_sign_13_after_signing_in_a_person_goes_to_the_page_they_asked_for(client, floor):
    client.post(STEP_1, {"who": "ab.floor", "next": "/health/"})

    assert client.post(PASSWORD_STEP, {"password": PASSWORD}).url == "/health/"


@pytest.mark.django_db
def test_sign_13_a_page_on_another_site_is_never_opened_after_signing_in(client, floor):
    client.post(STEP_1, {"who": "ab.floor", "next": "https://another.example/"})

    assert client.post(PASSWORD_STEP, {"password": PASSWORD}).url == HOME


@pytest.mark.django_db
def test_sign_15_the_email_step_gives_one_answer_whatever_was_typed(client, owner):
    answers = []
    for email in [OWNER_EMAIL, "nobody@example.com"]:
        client.cookies.clear()
        response = client.post(STEP_1, {"who": email}, follow=True)
        answers.append(re.search(r'<p class="notice__text">(.*?)</p>', page(response)).group(1))

    assert answers[0] == answers[1]
    assert answers[0].startswith("If this email belongs to an owner, a 6-digit code is on its way.")
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_sign_15_an_email_with_no_owner_gets_the_same_wrong_code_answers(client):
    client.post(STEP_1, {"who": "nobody@example.com"})

    assert "Wrong code. 4 tries left." in page(client.post(CODE_STEP, {"code": "123456"}))


@pytest.mark.django_db
def test_sign_21_this_browser_is_told_when_it_asked_too_often(client, owner):
    client.post(STEP_1, {"who": OWNER_EMAIL})

    html = page(client.post(STEP_1, {"who": OWNER_EMAIL}, follow=True))

    assert "A code was asked for on this device a moment ago." in html
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_sign_21_the_browsers_limit_says_the_same_for_an_email_with_no_owner(client):
    client.post(STEP_1, {"who": "nobody@example.com"})

    html = page(client.post(STEP_1, {"who": "nobody@example.com"}, follow=True))

    assert "A code was asked for on this device a moment ago." in html


@pytest.mark.django_db
def test_sign_22_a_wrong_code_says_how_many_tries_are_left(client, owner):
    client.post(STEP_1, {"who": OWNER_EMAIL})

    assert "Wrong code. 4 tries left." in page(client.post(CODE_STEP, {"code": "000000"}))


@pytest.mark.django_db
def test_sign_22_the_fifth_wrong_code_goes_back_to_step_1_with_the_email_kept(client, owner):
    client.post(STEP_1, {"who": OWNER_EMAIL})
    right = code_in_last_email()
    wrong = "000000" if right != "000000" else "111111"
    for _ in range(4):
        client.post(CODE_STEP, {"code": wrong})

    response = client.post(CODE_STEP, {"code": wrong}, follow=True)

    html = page(response)
    assert response.redirect_chain[-1][0] == STEP_1
    assert "That code no longer works. Press Continue to get a new one." in html
    assert f'value="{OWNER_EMAIL}"' in html


@pytest.mark.django_db
def test_sign_23_a_wrong_code_stays_in_its_box(client, owner):
    client.post(STEP_1, {"who": OWNER_EMAIL})

    assert 'value="000000"' in page(client.post(CODE_STEP, {"code": "000000"}))


@pytest.mark.django_db
def test_a_code_that_is_not_6_digits_spends_no_try(client, owner):
    client.post(STEP_1, {"who": OWNER_EMAIL})

    assert "The code has 6 digits." in page(client.post(CODE_STEP, {"code": "12"}))
    assert "Wrong code. 4 tries left." in page(client.post(CODE_STEP, {"code": "000000"}))


@pytest.mark.django_db
def test_sign_25_the_page_says_when_the_email_did_not_go_out(client, owner, settings):
    settings.MAILERS = BROKEN_MAILER

    response = client.post(STEP_1, {"who": OWNER_EMAIL}, follow=True)

    html = page(response)
    assert response.redirect_chain[-1][0] == STEP_1
    assert "The email did not go out, so no code was sent." in html
    assert f'value="{OWNER_EMAIL}"' in html
    # It spent no limit of this browser either: the next try is not told to wait.
    again = page(client.post(STEP_1, {"who": OWNER_EMAIL}, follow=True))
    assert "a moment ago" not in again


@pytest.mark.django_db
@pytest.mark.parametrize("step", [CODE_STEP, PASSWORD_STEP])
def test_sign_26_a_second_step_cannot_be_opened_without_step_1(client, step):
    assert client.get(step).url == STEP_1


@pytest.mark.django_db
def test_sign_33_the_page_says_the_account_is_locked_and_for_how_long(client, floor):
    for _ in range(5):
        count_wrong_password(floor)
    client.post(STEP_1, {"who": "ab.floor"})

    html = page(client.post(PASSWORD_STEP, {"password": PASSWORD}))

    assert "Too many wrong passwords. Try again in 15 minutes." in html
    assert not signed_in(client)


@pytest.mark.django_db
def test_sign_33_the_fifth_wrong_password_says_locked_at_once(client, floor):
    client.post(STEP_1, {"who": "ab.floor"})
    for _ in range(4):
        client.post(PASSWORD_STEP, {"password": "wrong"})

    html = page(client.post(PASSWORD_STEP, {"password": "wrong"}))

    assert "Too many wrong passwords. Try again in 15 minutes." in html
    assert WRONG not in html


@pytest.mark.django_db
def test_sign_36_each_visit_starts_the_40_days_again(client, floor):
    client.post(STEP_1, {"who": "ab.floor"})
    client.post(PASSWORD_STEP, {"password": PASSWORD})
    session = Session.objects.get(session_key=client.session.session_key)
    session.expire_date = timezone.now() + timedelta(days=1)
    session.save()

    client.get(HOME)

    session.refresh_from_db()
    assert session.expire_date > timezone.now() + timedelta(days=39)


@pytest.mark.django_db
def test_sign_37_closing_the_browser_does_not_sign_a_person_out(client, floor):
    client.post(STEP_1, {"who": "ab.floor"})

    response = client.post(PASSWORD_STEP, {"password": PASSWORD})

    assert response.cookies["sessionid"]["max-age"] == 60 * 60 * 24 * 40


@pytest.mark.django_db
def test_sign_38_a_change_sent_after_the_session_ended_is_said_not_saved(client):
    response = client.post(HOME, {"anything": "typed"})

    assert response.url == f"{STEP_1}?next={HOME}"
    html = page(client.get(response.url))
    assert "your last change was not saved" in html
    assert "your last change was not saved" not in page(client.get(STEP_1))


@pytest.mark.django_db
def test_sign_38_a_visitor_who_only_opened_a_page_is_told_nothing_was_lost(client):
    response = client.get(HOME)

    assert "not saved" not in page(client.get(response.url))


@pytest.mark.django_db
def test_the_sign_in_pages_are_never_kept_by_the_browser(client):
    assert "no-store" in client.get(STEP_1)["Cache-Control"]


@pytest.mark.django_db
def test_the_home_page_says_who_is_signed_in_and_where(client, floor):
    client.force_login(floor)

    html = page(client.get(HOME))

    assert "Signed in as ab.floor (Floor)." in html

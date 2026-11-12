"""The bill page and its settle boxes (docs/rules/settle-bill.md): the page's wiring only.
The rules are tested at the service (test_services.py); who may open each page is in
tests/test_permissions.py."""

import re
from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.accounts.tests.factories import MembershipFactory
from apps.billing.forms import SettleForm
from apps.billing.models import Bill, PaymentMethod
from apps.jobs.models import ConcernStatus, JobCard, JobCardStatus
from apps.jobs.services import cancel_job_card
from apps.jobs.tests.page_reader import FormReader, notices_of

pytestmark = pytest.mark.django_db


@pytest.fixture
def office(office, client):
    """Office of a workshop (billing/tests/conftest.py), signed in."""
    client.force_login(office.by)
    return office


def address(name, card):
    return reverse(name, kwargs={"key": card.pk})


def settle_box(client, card):
    """The bill page, the settle box's address, and what the box sends as it came, with its
    Settle bill pressed, which sends the total the box shows (SETTLE-26)."""
    html = client.get(address("billing:bill", card)).text
    action = re.search(r'id="settle-form" method="post" action="([^"]+)"', html)[1]
    reader = FormReader("settle-form")
    reader.feed(html)
    return html, action, {**reader.sent, **reader.pressed}


def send(client, card, **typed):
    """Sends the settle box, as the page holds it, with these boxes typed over it."""
    _html, action, sent = settle_box(client, card)
    return action, client.post(action, {**sent, **typed})


def seen(client, response):
    """Opens the page a send went on to, as a browser does, so its notice is shown and gone."""
    client.get(response.url)
    return response


def sheet_of(html):
    """Only the bill as it prints, without the page around it."""
    return html[html.index('<article class="sheet"') : html.index("</article>")]


def bills_of(place):
    return Bill.objects.for_workshop(place.workshop)


def test_settle_2_6_an_open_cards_bill_is_a_preview_with_its_jobs_and_total(client, office):
    card = office.card(number="JC-0027")

    html = client.get(address("billing:bill", card)).text

    assert ">Preview<" in html
    assert "PREVIEW" in html
    assert "JOB CARD: JC-0027" in html
    assert "Clutch plate replaced" in html
    assert "43,000.00" in html
    assert "INV-" not in html
    assert f'href="{address("jobs:edit", card)}"' in html


def test_settle_8_every_amount_on_the_bill_shows_its_paise(client, office):
    sheet = sheet_of(client.get(address("billing:bill", office.card(labour="17800"))).text)

    assert "17,800.00" in sheet
    # The parts' subtotal, with no parts yet.
    assert ">0.00<" in sheet


def test_settle_9_the_bill_is_titled_bill(client, office):
    sheet = sheet_of(client.get(address("billing:bill", office.card())).text)

    assert ">BILL<" in sheet
    assert "INVOICE" not in sheet.upper()


def test_settle_5_47_the_job_card_has_a_bill_button_for_office_and_none_for_floor(client, office):
    floor = MembershipFactory(role=Role.FLOOR, workshop=office.workshop)
    card = office.card()
    bill_link = f'href="{address("billing:bill", card)}"'

    assert bill_link in client.get(address("jobs:edit", card)).text
    client.force_login(floor.user)
    assert bill_link not in client.get(address("jobs:edit", card)).text


def test_settle_4_a_cancelled_card_has_no_bill(client, office):
    card = office.card()
    cancel_job_card(office.workshop, card.branch, card.pk, office.by, "Customer left")

    assert address("billing:bill", card) not in client.get(address("jobs:edit", card)).text
    response = client.get(address("billing:bill", card))
    assert response.url == address("jobs:edit", card)


def test_settle_10_12_before_you_settle_lists_each_thing_not_filled_and_goes_on_to_the_box(
    client, office
):
    card = office.card(mileage=None)
    office.concern(card, text="AC not cooling")
    office.concern(card, status=ConcernStatus.FIXED)

    html = client.get(address("billing:bill", card)).text

    assert 'data-dialog-open="settle-unfilled"' in html
    assert "2 things are not filled. Settling locks the job card." in html
    assert "no mileage" in html
    assert "AC not cooling" in html
    assert "not fixed" in html
    assert 'data-dialog-close data-dialog-open="settle-box">Continue' in html
    assert f'class="btn" href="{address("jobs:edit", card)}">Open job card' in html


def test_settle_10_a_card_with_nothing_to_fill_opens_the_box_straight(client, office):
    html = client.get(address("billing:bill", office.card())).text

    assert 'data-dialog-open="settle-box"' in html
    assert 'id="settle-unfilled"' not in html


def test_settle_18_a_bill_of_zero_offers_no_settle_and_says_why(client, office):
    html = client.get(address("billing:bill", office.card(labour="0"))).text

    assert 'data-dialog-open="settle-box"' not in html
    assert 'data-dialog-open="settle-unfilled"' not in html
    assert "This bill comes to 0.00, so there is nothing to settle." in html


def test_settle_15_the_box_has_one_money_box_for_each_method_in_its_order_and_word():
    boxes = [name for name in SettleForm.base_fields if name != "paid_on"]

    assert boxes == PaymentMethod.values
    assert [SettleForm.base_fields[name].label for name in boxes] == PaymentMethod.labels


def test_settle_15_21_the_box_has_the_date_paid_and_a_box_for_each_method(client, office):
    today = timezone.localdate()
    card = office.card(admitted_date=today - timedelta(days=10))

    html, _action, sent = settle_box(client, card)

    assert sent == {
        "csrfmiddlewaretoken": sent["csrfmiddlewaretoken"],
        "paid_on": today.isoformat(),
        "cash": "",
        "upi": "",
        "card": "",
        "bank_transfer": "",
        "seen": "43000.00",
    }
    for word in ("Cash", "UPI", "Card", "Bank transfer", "Date paid", 'data-today="Today"'):
        assert word in html
    # The chip's script gets the month words every date on the page uses.
    assert 'data-months="Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"' in html
    # The date box offers Office only the days it may choose (CHANGE-15).
    assert f'max="{today.isoformat()}"' in html
    assert f'min="{(today - timedelta(days=3)).isoformat()}"' in html


def test_settle_20_a_discount_answers_first_with_the_check_and_saves_nothing(client, office):
    card = office.card()

    _action, response = send(client, card, cash="20000", upi="20000")

    assert response.status_code == 200
    html = response.text
    assert 'id="settle-check" aria-labelledby="settle-check-title" data-open-now' in html
    assert "Discount &#8377; 3,000.00" in html
    assert "&#8377; 40,000.00" in html
    assert 'form="settle-form" name="checked" value="43000.00"' in html
    # The boxes keep what was typed, so the check's Settle bill sends them again.
    assert 'value="20000"' in html
    # The check opens alone: the settle box waits behind it for Go back.
    assert 'id="settle-box" aria-labelledby="settle-title" data-open-now' not in html
    assert not bills_of(office).exists()


def test_settle_20_24_the_checks_settle_bill_settles_with_its_notice(client, office):
    card = office.card(plate="KL10AA1000", car__plate="KL10AA1000")

    _action, response = send(client, card, cash="40000", checked="43000.00")

    bill = bills_of(office).get()
    assert response.url == address("billing:bill", card)
    assert notices_of(response) == [f"KL10AA1000 settled. Its bill number is {bill.number}."]
    html = client.get(address("billing:bill", card)).text
    assert ">Settled<" in html
    assert bill.number in html
    assert "Cash &#8377; 40,000.00" in html
    assert 'id="settle-form"' not in html


def test_settle_7_a_settled_bill_shows_its_discount_and_net_and_never_says_paid(client, office):
    card = office.card()
    send(client, card, cash="40000", checked="43000.00")

    sheet = sheet_of(client.get(address("billing:bill", card)).text)

    assert ">DISCOUNT<" in sheet
    assert "3,000.00" in sheet
    assert ">NET<" in sheet
    assert "40,000.00" in sheet
    assert "PAID" not in sheet.upper()


def test_settle_7_a_bill_settled_with_no_discount_shows_no_discount_line(client, office):
    card = office.card()
    send(client, card, upi="43000")

    sheet = sheet_of(client.get(address("billing:bill", card)).text)

    assert "DISCOUNT" not in sheet
    assert ">NET<" in sheet


def test_settle_20_a_settle_with_no_discount_saves_at_once(client, office):
    card = office.card()

    _action, response = send(client, card, upi="43000")

    assert response.url == address("billing:bill", card)
    assert bills_of(office).get().discount == Decimal("0")


def test_settle_17_a_refusal_opens_the_box_again_with_what_was_typed(client, office):
    card = office.card()

    _action, response = send(client, card, cash="50000")

    assert response.status_code == 200
    html = response.text
    assert "The payments come to 50,000.00, more than the total of 43,000.00." in html
    assert 'id="settle-box" aria-labelledby="settle-title" data-open-now' in html
    assert 'value="50000"' in html
    assert not bills_of(office).exists()


def test_settle_17_a_boxs_own_problem_is_named_for_a_screen_reader(client, office):
    # A third decimal is refused by the box itself (ADR-0029).
    _action, response = send(client, office.card(), cash="1.005")

    html = response.text
    assert 'aria-describedby="id_cash_error"' in html
    assert '<p class="field__error" id="id_cash_error">' in html


def test_settle_25_a_double_tap_shows_the_bill_settled_the_first_time(client, office):
    card = office.card()
    _html, action, sent = settle_box(client, card)
    typed = {**sent, "upi": "43000"}

    first = client.post(action, typed)
    first_notices = notices_of(first)
    seen(client, first)
    again = client.post(action, typed)

    assert again.url == first.url == address("billing:bill", card)
    assert notices_of(again) == first_notices
    assert bills_of(office).count() == 1


def test_settle_25_a_settle_from_another_page_says_who_settled_it_and_when(client, office):
    card = office.card()
    _html, first_action, first_sent = settle_box(client, card)
    _html, second_action, second_sent = settle_box(client, card)
    seen(client, client.post(first_action, {**first_sent, "upi": "43000"}))

    response = client.post(second_action, {**second_sent, "upi": "43000"})

    assert response.url == address("billing:bill", card)
    (notice,) = notices_of(response)
    assert notice.startswith(f"{office.by.get_full_name() or office.by.get_username()} settled")
    assert notice.endswith("so nothing was saved.")
    assert bills_of(office).count() == 1


def test_settle_25_a_settle_sent_to_a_card_cancelled_first_says_so(client, office):
    card = office.card()
    _html, action, sent = settle_box(client, card)
    cancel_job_card(office.workshop, card.branch, card.pk, office.by, "Customer took the car")

    response = client.post(action, {**sent, "upi": "43000"})

    assert response.url == address("jobs:edit", card)
    assert notices_of(response) == ["This job card is cancelled, so nothing was saved."]
    assert not bills_of(office).exists()


def test_settle_26_a_total_that_moved_after_the_check_is_refused_with_the_new_total(client, office):
    card = office.card()
    _html, action, sent = settle_box(client, card)
    JobCard.objects.filter(pk=card.pk).update(labour=Decimal("45000"))

    response = client.post(action, {**sent, "cash": "40000", "checked": "43000.00"})

    assert response.status_code == 200
    assert "its total is now 45,000.00" in response.text
    assert "&#8377; 45,000.00" in response.text
    assert not bills_of(office).exists()


@pytest.mark.parametrize(
    ("moved_to", "paid"),
    [
        # Down to what was paid: with no discount, it would save at once on a total nobody saw.
        pytest.param("40000", "40000", id="down, no discount left"),
        # Up: the discount would be worked out on a total nobody saw.
        pytest.param("45000", "40000", id="up, a bigger discount"),
    ],
)
def test_settle_26_a_total_that_moved_before_the_first_send_is_refused(
    client, office, moved_to, paid
):
    card = office.card()
    _html, action, sent = settle_box(client, card)
    JobCard.objects.filter(pk=card.pk).update(labour=Decimal(moved_to))

    response = client.post(action, {**sent, "cash": paid})

    assert response.status_code == 200
    html = response.text
    assert f"its total is now {int(moved_to):,}.00" in html
    assert 'id="settle-check"' not in html
    # The box opens again, and now sends the total it shows.
    assert 'id="settle-box" aria-labelledby="settle-title" data-open-now' in html
    assert f'name="seen" value="{moved_to}.00"' in html
    assert not bills_of(office).exists()


@pytest.mark.parametrize(
    "shown",
    [
        pytest.param({}, id="no total"),
        pytest.param({"seen": "a lot"}, id="not an amount"),
        pytest.param({"checked": "sNaN"}, id="not a number"),
        pytest.param({"checked": "Infinity"}, id="no end"),
    ],
)
def test_settle_26_a_send_that_does_not_say_what_total_it_saw_saves_nothing(client, office, shown):
    card = office.card()
    _html, action, sent = settle_box(client, card)
    del sent["seen"]

    response = client.post(action, {**sent, "upi": "43000", **shown})

    assert response.status_code == 200
    assert "its total is now 43,000.00" in response.text
    assert not bills_of(office).exists()


def test_settle_49_a_get_on_the_settle_address_shows_the_bill_page(client, office):
    card = office.card()
    _html, action, _sent = settle_box(client, card)

    response = client.get(action)

    assert response.status_code == 200
    assert 'id="settle-form"' in response.text


def test_settle_36_a_settled_cards_page_says_who_settled_it_and_every_box_is_locked(client, office):
    card = office.card()
    send(client, card, upi="43000")

    html = client.get(address("jobs:edit", card)).text

    assert 'class="job-settled__title"' in html
    assert f"{office.by.get_full_name() or office.by.get_username()}, " in html
    assert "The bill is final, so every box is locked." in html
    assert '<fieldset class="job-form" disabled>' in html
    assert f'href="{address("billing:bill", card)}"' in html
    assert "Cancel job card" not in html
    assert ">Cancelled<" not in html


def test_settle_27_a_save_sent_to_a_settled_card_saves_nothing(client, office):
    card = office.card()
    seen(client, send(client, card, upi="43000")[1])

    response = client.post(address("jobs:edit", card), {"plate": "KL99ZZ9999"})

    assert notices_of(response) == ["This job card is settled, so nothing was saved."]
    card.refresh_from_db()
    assert card.plate != "KL99ZZ9999"


def test_settle_37_a_settled_card_is_never_cancelled(client, office):
    card = office.card()
    send(client, card, upi="43000")

    client.post(address("jobs:cancel", card), {"reason": "By mistake"})

    card.refresh_from_db()
    assert card.status == JobCardStatus.SETTLED

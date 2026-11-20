"""The Change payments page and its boxes (docs/rules/settle-bill.md): the page's wiring only.
The rules are tested at the service (test_change_payments.py); who may open each page is in
tests/test_permissions.py."""

import re
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.billing.models import Bill
from apps.billing.tests.conftest import Place, changes, payments, settled, settled_hours_ago
from apps.billing.tests.factories import BillFactory, PaymentFactory
from apps.jobs.models import JobCard
from apps.jobs.tests.page_reader import FormReader, notices_of
from apps.workshops.tests.factories import BranchFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def office(office, client):
    """Office of a workshop (billing/tests/conftest.py), signed in."""
    client.force_login(office.by)
    return office


def address(name, card):
    return reverse(name, kwargs={"key": card.pk})


def change_box(client, card):
    """The bill page, the change box's address, and what the box sends as it came, with its
    Change payments pressed, which sends the total the box shows (SETTLE-26)."""
    html = client.get(address("billing:bill", card)).text
    action = re.search(r'id="change-form" method="post" action="([^"]+)"', html)[1]
    reader = FormReader("change-form")
    reader.feed(html)
    return html, action, {**reader.sent, **reader.pressed}


def send(client, card, **typed):
    """Sends the change box, as the page holds it, with these boxes typed over it."""
    _html, action, sent = change_box(client, card)
    return client.post(action, {**sent, "reason": "Part was UPI", **typed})


def test_settle_38_a_settled_bill_offers_change_payments_as_saved(client, office):
    card = settled(office, cash="40000")

    html, action, sent = change_box(client, card)

    # The box's address holds the new change's key (SETTLE-52).
    assert re.fullmatch(rf"/job-cards/{card.pk}/bill/payments/[0-9a-f-]{{36}}/", action)
    assert 'data-dialog-open="change-box"' in html
    assert sent["cash"] == sent["initial-cash"] == "40000"
    assert sent["upi"] == sent["initial-upi"] == ""
    assert sent["paid_on"] == sent["initial-paid_on"] == timezone.localdate().isoformat()
    assert sent["reason"] == ""
    assert sent["seen"] == "43000.00"
    assert "Why are you changing this bill?" in html
    assert "Kept in the change history, with what it was." in html
    assert 'id="change-box" aria-labelledby="change-title" data-open-now' not in html


def test_settle_46_office_past_the_window_sees_why_in_place_of_the_button(client, office):
    card = settled(office)
    settled_hours_ago(card, 30)
    owner = Place(Role.OWNER, workshop=office.workshop)

    html = client.get(address("billing:bill", card)).text
    client.force_login(owner.by)
    owners_html = client.get(address("billing:bill", card)).text

    assert (
        "Settled 30 hours ago. Office can change money only within 24 hours. Ask an owner."
    ) in html
    assert 'id="change-box"' not in html
    assert 'data-dialog-open="change-box"' in owners_html


def test_settle_39_a_change_that_leaves_a_discount_answers_with_the_check_and_what_was(
    client, office
):
    card = settled(office, cash="40000")

    response = send(client, card, cash="20000", upi="19000")

    assert response.status_code == 200
    html = response.text
    assert 'id="change-check" aria-labelledby="change-check-title" data-open-now' in html
    assert "Discount &#8377; 4,000.00" in html
    for was in ("40,000.00", "0.00", "3,000.00"):
        assert f"was &#8377; {was}" in html
    assert 'form="change-form" name="checked" value="43000.00"' in html
    assert 'id="change-box" aria-labelledby="change-title" data-open-now' not in html
    assert not changes(office).exists()


def test_settle_39_the_checks_button_saves_with_its_notice(client, office):
    card = settled(office, cash="40000")
    number = office.bill_of(card).number

    response = send(client, card, cash="20000", upi="19000", checked="43000.00")

    assert response.url == address("billing:bill", card)
    assert notices_of(response) == [
        f"The payments of {number} are changed. The change is kept in the change history."
    ]
    assert changes(office).count() == 1
    assert "UPI &#8377; 19,000.00" in client.get(address("billing:bill", card)).text


def test_settle_39_a_change_that_leaves_no_discount_saves_at_once(client, office):
    card = settled(office, cash="40000")

    response = send(client, card, cash="", upi="43000")

    assert response.url == address("billing:bill", card)
    assert office.bill_of(card).discount == Decimal("0.00")


def test_settle_52_a_send_that_changes_nothing_says_so(client, office):
    card = settled(office, cash="40000")

    response = send(client, card)

    assert notices_of(response) == ["Nothing changed, so nothing was saved."]
    assert not changes(office).exists()


def test_settle_52_a_double_tap_shows_the_same_notice_and_keeps_one_change(client, office):
    card = settled(office, cash="40000")
    _html, action, sent = change_box(client, card)
    typed = {**sent, "reason": "Part was UPI", "cash": "", "upi": "43000"}

    first = client.post(action, typed)
    first_notices = notices_of(first)
    client.get(first.url)
    again = client.post(action, typed)

    assert notices_of(again) == first_notices
    assert changes(office).count() == 1


def test_settle_52_a_change_after_someone_else_changed_it_opens_the_box_as_it_is_now(
    client, office
):
    card = settled(office, cash="40000")
    _html, action, sent = change_box(client, card)
    Place(Role.OWNER, workshop=office.workshop).change(card, cash="39000")

    response = client.post(action, {**sent, "reason": "Part was UPI", "upi": "3000"})

    assert response.status_code == 200
    html = response.text
    assert "Someone changed this bill while you had it open." in html
    assert 'id="change-box" aria-labelledby="change-title" data-open-now' in html
    reader = FormReader("change-form")
    reader.feed(html)
    assert reader.sent["cash"] == reader.sent["initial-cash"] == "39000"
    assert reader.sent["upi"] == ""
    assert reader.sent["reason"] == "Part was UPI"
    assert changes(office).count() == 1


def test_settle_17_52_a_refused_change_keeps_what_was_typed_and_what_the_box_opened_with(
    client, office
):
    card = settled(office, cash="40000")
    _html, action, sent = change_box(client, card)

    response = client.post(action, {**sent, "reason": "Part was UPI", "cash": "50000"})

    html = response.text
    assert "The payments come to 50,000.00, more than the total of 43,000.00." in html
    reader = FormReader("change-form")
    reader.feed(html)
    assert (reader.sent["cash"], reader.sent["initial-cash"]) == ("50000", "40000")
    # So sending it again, put right, is no clash with itself.
    again = client.post(action, {**reader.sent, **reader.pressed, "cash": "43000"})
    assert again.url == address("billing:bill", card)
    assert changes(office).count() == 1


def test_settle_54_the_date_box_takes_a_saved_date_office_could_not_type_today(client, office):
    card = settled(office)
    five_back = timezone.localdate() - timedelta(days=5)
    Bill.objects.filter(job_card=card).update(date=five_back)
    JobCard.objects.filter(pk=card.pk).update(admitted_date=date(2026, 1, 1))

    html, _action, sent = change_box(client, card)

    assert sent["paid_on"] == five_back.isoformat()
    assert f'min="{five_back.isoformat()}"' in html


def test_settle_44_the_date_box_ends_with_the_bills_financial_year(client, owner):
    card = owner.card(labour="43000", admitted_date=date(2026, 3, 30))
    owner.settle(card, paid_on=date(2026, 3, 31))
    client.force_login(owner.by)

    html, _action, _sent = change_box(client, card)

    assert 'max="2026-03-31"' in html
    assert f'data-today-iso="{timezone.localdate().isoformat()}"' in html


def test_settle_49_a_get_on_the_change_address_shows_the_bill_page(client, office):
    card = settled(office)
    _html, action, _sent = change_box(client, card)

    response = client.get(action)

    assert response.status_code == 200
    assert 'id="change-form"' in response.text


def test_settle_38_an_open_cards_change_address_goes_to_its_bill(client, office):
    card = office.card()

    change_address = reverse(
        "billing:change_payments", kwargs={"key": card.pk, "change_key": uuid.uuid7()}
    )

    response = client.post(change_address, {"cash": "1"})

    assert response.url == address("billing:bill", card)


def test_change_9_a_send_past_the_window_is_refused_with_why(client, office):
    card = settled(office, cash="40000")
    _html, action, sent = change_box(client, card)
    settled_hours_ago(card, 25)

    response = client.post(action, {**sent, "reason": "Part was UPI", "cash": "39000"})

    assert response.url == address("billing:bill", card)
    assert notices_of(response) == ["Nothing was saved."]
    # The bill page says why, in place of the button, once (SETTLE-46).
    html = client.get(response.url).text
    assert html.count("Office can change money only within 24 hours.") == 1
    assert payments(office.bill_of(card)) == {"cash": Decimal("40000.00")}


def test_change_5_a_send_that_changes_nothing_needs_no_reason(client, office):
    card = settled(office, cash="40000")

    response = send(client, card, reason="")

    assert notices_of(response) == ["Nothing changed, so nothing was saved."]


def test_change_5_a_change_with_no_reason_asks_why_in_plain_words(client, office):
    card = settled(office, cash="40000")

    response = send(client, card, reason="  ", cash="39000")

    assert response.status_code == 200
    assert "Type why you are changing this bill." in response.text
    assert 'id="change-box" aria-labelledby="change-title" data-open-now' in response.text
    assert not changes(office).exists()


@pytest.mark.parametrize("where", ["another workshop", "another branch"])
def test_settle_50_a_change_sent_for_another_places_bill_is_not_found_and_changes_nothing(
    client, office, where
):
    # A whole, right send, so only the place could refuse it.
    _html, action, sent = change_box(client, settled(office, cash="40000"))
    if where == "another branch":
        there = BranchFactory(workshop=office.workshop)
        theirs = BillFactory(workshop=office.workshop, branch=there, job_card__labour="43000")
    else:
        theirs = BillFactory(job_card__labour="43000")
    PaymentFactory(workshop=theirs.workshop, bill=theirs, amount=Decimal("40000"))
    theirs_address = re.sub(r"/job-cards/[0-9a-f-]+/", f"/job-cards/{theirs.job_card_id}/", action)

    response = client.post(theirs_address, {**sent, "reason": "Not ours", "cash": "39000"})

    assert response.status_code == 404
    assert payments(theirs) == {"cash": Decimal("40000.00")}
    theirs.refresh_from_db()
    assert theirs.discount == Decimal("0")

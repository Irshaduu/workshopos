"""The wiring of the job card's pages (apps/jobs/views.py). The rules themselves are tested at
their service, selector and form.

Who may open each page, and a record of another workshop: tests/test_permissions.py. Typing
into the open row, the colour choices and the meter need a browser: that test comes with
Playwright (step 10 of Slice 1). Until then they are clicked through by hand.
"""

import re
import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.accounts.roles import PERMISSIONS
from apps.accounts.tests.factories import MembershipFactory
from apps.jobs.models import ConcernStatus, JobCard, JobCardStatus, NumberCounter, StepKind
from apps.jobs.tests.cards import visit
from apps.jobs.tests.factories import ConcernFactory, JobCardFactory, JobLineFactory
from apps.jobs.tests.page_reader import what_the_page_sends
from apps.staff.tests.factories import StaffMemberFactory
from apps.vehicles.models import Colour
from apps.vehicles.tests.factories import CarFactory, CustomerFactory
from apps.workshops.tests.factories import BranchFactory, first_branch

pytestmark = pytest.mark.django_db

NEW = "/job-cards/new/"
HOME = "/"
VIN = "WBA8E9C50GK123456"


@pytest.fixture
def office(client):
    member = MembershipFactory(role=Role.OFFICE)
    client.force_login(member.user)
    return member


@pytest.fixture
def floor(client):
    member = MembershipFactory(role=Role.FLOOR)
    client.force_login(member.user)
    return member


def address(name, card):
    return reverse(name, kwargs={"key": card.pk})


def new_address(key=None):
    return reverse("jobs:create", kwargs={"key": key or uuid.uuid7()})


def card_of(member, **values):
    return JobCardFactory(workshop=member.workshop, **values)


def cards_of(member):
    return JobCard.objects.for_workshop(member.workshop)


def new_card_page(client):
    """The new card's page, and the address its form sends to."""
    html = client.get(NEW).text
    return html, re.search(r'<form id="job-form"[^>]* action="([^"]+)"', html)[1]


def send_new_card(client, **typed):
    html, action = new_card_page(client)
    boxes = {
        "plate": "KL10AA1000",
        "brand": "BMW",
        "car_model": "520d",
        **typed,
    }
    return client.post(action, what_the_page_sends(html, **boxes))


def send_card(client, card, **typed):
    address_of_card = address("jobs:edit", card)
    html = client.get(address_of_card).text
    return client.post(address_of_card, what_the_page_sends(html, **typed))


def notices_of(response):
    return [str(message) for message in response.wsgi_request._messages]


# The first live board.


def test_job_61_the_board_lists_the_open_cards(client, office):
    card_of(office, plate="KL10AA1000", car__plate="KL10AA1000", number="JC-0007")

    html = client.get(HOME).text

    assert "<h1>Live board</h1>" in html
    assert "KL10AA1000" in html
    assert "JC-0007" in html


def test_job_61_a_tap_opens_the_card(client, office):
    card = card_of(office)

    assert f'href="{address("jobs:edit", card)}"' in client.get(HOME).text


def test_job_61_an_empty_board_says_so_with_the_next_step(client, office):
    html = client.get(HOME).text

    assert "No cars in the workshop" in html
    assert f'class="btn btn--primary" href="{NEW}"' in html


def test_job_61_a_cancelled_card_is_not_on_the_board(client, office):
    card = card_of(
        office, status=JobCardStatus.CANCELLED, cancel_reason="Customer left", number="JC-0007"
    )

    assert card.number not in client.get(HOME).text


def test_job_62_owners_and_office_start_a_card_from_the_board(client, office):
    card_of(office)
    html = client.get(HOME).text

    assert f'class="btn btn--primary" href="{NEW}"' in html
    assert 'class="tab" href="/job-cards/new/"' not in html


def test_job_62_floor_starts_a_card_from_its_tab_bar(client, floor):
    card_of(floor)
    html = client.get(HOME).text

    assert 'class="tab" href="/job-cards/new/"' in html
    assert f'class="btn btn--primary" href="{NEW}"' not in html


# A new card.


def test_job_57_the_page_is_in_v1s_order(client, office):
    html = client.get(NEW).text

    words = ["Car Details", "Customer &amp; Notes", "Customer Concerns", "Job Performed"]
    assert [html.index(word) for word in words] == sorted(html.index(word) for word in words)
    assert html.index("Job Performed") < html.index("Labour Charge") < html.index("Save Job Card")


def test_job_59_the_plate_comes_first(client, office):
    html = client.get(NEW).text

    assert html.index('name="plate"') < html.index('name="brand"') < html.index('name="car_model"')


def test_job_58_a_new_cards_head_says_so(client, office):
    html = client.get(NEW).text

    assert "New Job Card" in html
    assert "Editing:" not in html


def test_job_24_the_date_starts_at_today(client, office):
    html = client.get(NEW).text

    assert f'value="{timezone.localdate().isoformat()}"' in html


def test_job_42_the_forms_address_holds_a_new_key_each_time(client, office):
    _html, first = new_card_page(client)
    _html, second = new_card_page(client)

    assert first != second
    assert uuid.UUID(first.rstrip("/").split("/")[-1]).version == 7


def test_job_45_a_saved_card_stays_open_with_its_notice(client, office):
    response = send_new_card(client)

    card = cards_of(office).get()
    assert response.status_code == 302
    assert response.url == address("jobs:edit", card)
    assert card.number == "JC-0001"
    assert f"Job card {card.number} saved for KL10AA1000." in notices_of(response)


def test_job_1_a_card_saves_what_the_page_typed(client, office):
    mechanic = StaffMemberFactory(workshop=office.workshop, name="Ajay")
    response = send_new_card(
        client,
        plate="kl-10 aa 1000",
        chassis_code="f 30",
        vin="wba 8e9c-50gk 123456",
        colour=Colour.RED,
        mileage="1,32,022",
        lead_mechanic=str(mechanic.pk),
        note="Noise only when cold",
        customer_name="arun k",
        contact_number="+91 90000 00001",
        labour="2950",
        **{
            "concerns-0-text": "Brake noise",
            "concerns-0-status": ConcernStatus.WORKING,
            "job_lines-0-text": "Brake disc skim",
        },
    )

    assert response.status_code == 302
    card = cards_of(office).get()
    car = card.car
    assert (car.plate, car.chassis_code, car.vin) == ("KL10AA1000", "F30", "WBA8E9C50GK123456")
    assert car.colour == Colour.RED
    assert card.mileage == 132022
    assert card.lead_mechanic == mechanic
    assert card.note == "Noise only when cold"
    assert (card.customer.name, card.customer.contact_number) == ("Arun K", "9000000001")
    assert card.labour == Decimal("2950.00")
    assert card.concerns.get().status == ConcernStatus.WORKING
    assert card.job_lines.get().text == "Brake disc skim"
    assert [step.by for step in card.steps.all()] == [office.user, office.user]


def test_job_42_a_repeat_opens_the_card_saved_first_with_the_same_notice(client, office):
    html, action = new_card_page(client)
    sent = what_the_page_sends(html, plate="KL10AA1000", brand="BMW", car_model="520d")

    client.post(action, sent)
    response = client.post(action, sent)

    card = cards_of(office).get()
    assert response.url == address("jobs:edit", card)
    assert notices_of(response)[-1] == f"Job card {card.number} saved for KL10AA1000."
    assert NumberCounter.objects.for_workshop(office.workshop).get().last_number == 1


def test_job_42_another_plate_with_a_used_key_is_not_saved_and_the_notice_says_so(client, office):
    html, action = new_card_page(client)
    sent = what_the_page_sends(html, plate="KL10AA1000", brand="BMW", car_model="520d")
    client.post(action, sent)

    response = client.post(action, {**sent, "plate": "KL10AB2000"})

    card = cards_of(office).get()
    assert card.plate == "KL10AA1000"
    assert response.url == address("jobs:edit", card)
    assert "so KL10AB2000 was not saved" in notices_of(response)[-1]


def test_a_get_on_a_used_key_opens_the_saved_card(client, office):
    html, action = new_card_page(client)
    client.post(action, what_the_page_sends(html, plate="KL10AA1", brand="BMW", car_model="520d"))

    assert client.get(action).url == address("jobs:edit", cards_of(office).get())


def test_sign_38_a_get_on_a_new_key_starts_a_new_form(client, office):
    assert client.get(new_address()).url == NEW


def test_a_send_with_no_key_starts_again(client, office):
    assert client.post(NEW, {"plate": "KL10AA1000"}).url == NEW
    assert not cards_of(office).exists()


# A refused save.


def test_job_44_a_refused_save_says_how_many_and_names_each(client, office):
    response = send_new_card(
        client,
        plate="",
        vin="WBA",
        **{"concerns-0-text": "x" * 256, "concerns-0-status": "pending"},
    )
    html = response.text

    assert response.status_code == 200
    assert 'data-sound-tag="error"' in html
    assert "Not saved: 3 things to fix. Nothing you typed was lost." in html
    assert "Plate Number: Type the plate." in html
    assert "VIN: A VIN has 17 characters, and this one has 3." in html
    assert f"Concern, {'x' * 256}:" in html
    assert not cards_of(office).exists()


def test_job_44_one_thing_to_fix_says_one(client, office):
    assert "Not saved: 1 thing to fix." in send_new_card(client, plate="").text


def test_job_44_what_was_typed_stays_and_the_error_sits_next_to_its_box(client, office):
    html = send_new_card(
        client,
        vin="WBA",
        note="Noise only when cold",
        customer_name="Arun",
        **{"concerns-0-text": "Oil leak", "concerns-0-status": "working"},
    ).text

    assert 'value="WBA"' in html
    assert "Noise only when cold</textarea>" in html
    assert 'value="Arun"' in html
    assert 'value="Oil leak"' in html
    assert '<option value="working" selected>' in html
    assert 'id="id_vin_error"' in html
    assert 'aria-invalid="true"' in html


def test_job_47_a_refused_page_is_unsaved_from_the_start(client, office):
    assert re.search(r'class="job-head [^"]*is-dirty', send_new_card(client, plate="").text)


def test_job_26_an_error_inside_the_customer_section_opens_it(client, office):
    html = send_new_card(client, contact_number="abc").text

    assert '<details class="job-card job-fold" open>' in html
    assert "Type a phone number, in digits." in html


def test_job_4_a_second_open_card_links_to_the_first_in_this_branch(client, office):
    first = card_of(office, plate="KL10AA1000", car__plate="KL10AA1000", number="JC-0007")

    html = send_new_card(client).text

    assert "This car already has an open job card, JC-0007." in html
    assert f'class="btn job-open-card" href="{address("jobs:edit", first)}"' in html


def test_job_4_a_card_in_another_branch_is_named_with_no_link(client, office):
    there = BranchFactory(workshop=office.workshop)
    first = card_of(
        office, branch=there, plate="KL10AA1000", car__plate="KL10AA1000", number="JC-0007"
    )

    html = send_new_card(client).text

    assert "This car already has an open job card, JC-0007." in html
    assert address("jobs:edit", first) not in html


# A saved card.


def test_job_58_the_head_names_the_car_the_plate_and_the_number(client, office):
    card = card_of(
        office,
        number="JC-0007",
        plate="KL10AA1000",
        car__plate="KL10AA1000",
        car__car_model__brand__name="BMW",
        car__car_model__name="520d",
    )

    html = client.get(address("jobs:edit", card)).text

    assert "Editing:" in html
    assert '<span class="job-head__car">BMW 520d</span>' in html
    assert '<span class="job-head__plate">KL10AA1000</span>' in html
    assert '<span class="job-head__number">JC-0007</span>' in html
    assert "Update Job Card" in html
    assert "Save Job Card" not in html


def test_job_45_an_update_stays_open_with_its_notice(client, office):
    card = card_of(office)

    response = send_card(client, card, note="Noise only when cold")

    card.refresh_from_db()
    assert card.note == "Noise only when cold"
    assert response.url == address("jobs:edit", card)
    assert notices_of(response) == [f"{card.plate} updated."]


def test_job_43_a_page_sent_as_it_came_changes_nothing(client, office):
    customer = CustomerFactory(workshop=office.workshop)
    mechanic = StaffMemberFactory(workshop=office.workshop)
    card = card_of(
        office,
        customer=customer,
        lead_mechanic=mechanic,
        mileage=132022,
        note="A note\nwith two lines",
        labour=Decimal("2950.00"),
        car__chassis_code="F30",
        car__colour=Colour.OTHER,
        car__colour_other="#7f1d1d",
    )
    concern = ConcernFactory(workshop=office.workshop, job_card=card, text="Oil leak")
    JobLineFactory(workshop=office.workshop, job_card=card, text="Oil changed")

    response = send_card(client, card)

    assert response.status_code == 302
    card.refresh_from_db()
    assert card.customer == customer
    assert card.note.split() == ["A", "note", "with", "two", "lines"]
    assert card.labour == Decimal("2950.00")
    assert card.car.colour_other == "#7f1d1d"
    concern.refresh_from_db()
    assert concern.status == ConcernStatus.PENDING
    assert not card.steps.exists()


def test_job_43_a_page_left_open_never_puts_back_someone_elses_save(client, office):
    card = card_of(office, note="Old", car__chassis_code="F30")
    concern = ConcernFactory(workshop=office.workshop, job_card=card, text="Oil leak")
    address_of_card = address("jobs:edit", card)
    left_open = client.get(address_of_card).text

    # Someone else fixes the note and the chassis code, and marks the concern Fixed.
    send_card(
        client,
        card,
        note="Office's fix",
        chassis_code="G20",
        **{f"concern-{concern.pk}-status": ConcernStatus.FIXED},
    )
    # The page left open saves one new thing.
    client.post(address_of_card, what_the_page_sends(left_open, mileage="5000"))

    card.refresh_from_db()
    assert card.mileage == 5000
    assert card.note == "Office's fix"
    assert card.car.chassis_code == "G20"
    concern.refresh_from_db()
    assert concern.status == ConcernStatus.FIXED
    assert [step.kind for step in card.steps.all()] == [StepKind.CONCERN_FIXED]


def test_job_43_a_row_someone_else_added_stays_and_one_they_removed_stays_removed(client, office):
    card = card_of(office)
    removed = ConcernFactory(workshop=office.workshop, job_card=card, text="Removed")
    address_of_card = address("jobs:edit", card)
    left_open = client.get(address_of_card).text
    removed.delete()
    ConcernFactory(workshop=office.workshop, job_card=card, text="Added")

    response = client.post(address_of_card, what_the_page_sends(left_open, note="Typed"))

    assert response.status_code == 302
    assert [row.text for row in card.concerns.all()] == ["Added"]


def test_job_37_a_double_tap_adds_a_new_row_once(client, office):
    card = card_of(office)
    address_of_card = address("jobs:edit", card)
    sent = what_the_page_sends(
        client.get(address_of_card).text,
        **{"concerns-0-text": "Oil leak", "concerns-0-status": "working"},
    )

    client.post(address_of_card, sent)
    client.post(address_of_card, sent)

    assert card.concerns.get().text == "Oil leak"
    assert card.steps.count() == 1


def test_job_37_a_refused_row_shows_its_error_next_to_it(client, office):
    card = card_of(office)
    ConcernFactory(workshop=office.workshop, job_card=card, text="Oil leak")
    second = ConcernFactory(workshop=office.workshop, job_card=card, text="AC not cooling")

    response = send_card(client, card, **{f"concern-{second.pk}-text": "OIL LEAK"})

    assert response.status_code == 200
    assert "This is already on the card." in response.text
    second.refresh_from_db()
    assert second.text == "AC not cooling"


def test_known_14_a_plate_of_another_car_shows_the_move_question_and_keeps_what_was_typed(
    client, office
):
    other = CarFactory(
        workshop=office.workshop,
        plate="KL10AB2000",
        car_model__brand__name="Audi",
        car_model__name="A4",
    )
    card = card_of(office)

    response = send_card(client, card, plate=other.plate, note="Typed before the question")

    html = response.text
    assert response.status_code == 200
    assert "Move this job card?" in html
    assert "KL10AB2000 is the plate of Audi A4" in html
    assert f'name="answers" value="move:move:{other.pk}"' in html
    assert "Typed before the question</textarea>" in html
    card.refresh_from_db()
    assert card.car != other


def test_known_14_the_answer_moves_the_card(client, office):
    other = CarFactory(workshop=office.workshop, plate="KL10AB2000")
    card = card_of(office)

    response = send_card(client, card, plate=other.plate, answers=f"move:move:{other.pk}")

    assert response.status_code == 302
    card.refresh_from_db()
    assert card.car == other


def test_known_13_an_answer_given_comes_back_with_the_next_question(client, office):
    toyota = CarFactory(
        workshop=office.workshop,
        plate="KL10AA1000",
        car_model__brand__name="Toyota",
        car_model__name="Innova",
    )
    bmw = CarFactory(
        workshop=office.workshop,
        plate="KA01AB1234",
        vin=VIN,
        car_model__brand__name="BMW",
        car_model__name="520d",
    )
    first = f"brand:another:{toyota.pk}"

    html = send_new_card(client, plate="KL10AA1000", vin=VIN, answers=first).text

    assert f'<input type="hidden" name="answers" value="{first}">' in html
    assert f'name="answers" value="vin:same:{bmw.pk}"' in html
    assert "Is it the same car, now with KL10AA1000?" in html
    assert not cards_of(office).exists()


def test_known_13_both_answers_make_the_card(client, office):
    toyota = CarFactory(
        workshop=office.workshop,
        plate="KL10AA1000",
        car_model__brand__name="Toyota",
        car_model__name="Innova",
    )
    bmw = CarFactory(
        workshop=office.workshop,
        plate="KA01AB1234",
        vin=VIN,
        car_model__brand__name="BMW",
        car_model__name="520d",
    )
    asked = send_new_card(client, plate="KL10AA1000", vin=VIN, answers=f"brand:another:{toyota.pk}")
    action = re.search(r'<form id="job-form"[^>]* action="([^"]+)"', asked.text)[1]

    sent = what_the_page_sends(asked.text)
    response = client.post(action, {**sent, "answers": [sent["answers"], f"vin:same:{bmw.pk}"]})

    assert response.status_code == 302
    assert cards_of(office).get().car == bmw


def test_known_12_a_vin_on_a_car_with_an_open_card_is_refused_next_to_the_vin(client, office):
    other = CarFactory(workshop=office.workshop, vin=VIN, car_model__brand__name="BMW")
    open_card = card_of(office, car=other)

    html = send_new_card(client, plate="KL10AA1000", vin=VIN).text

    assert f"which has an open job card, {open_card.number}." in html
    assert 'id="id_vin_error"' in html
    assert address("jobs:edit", open_card) in html


def test_known_4_a_new_cards_plate_box_asks_and_a_saved_cards_does_not(client, office):
    new = client.get(NEW).text
    saved = client.get(address("jobs:edit", card_of(office))).text

    assert 'hx-get="/job-cards/known-plate/"' in new
    assert 'hx-target="#known-plate"' in new
    assert 'hx-sync="this:replace"' in new
    assert '<div class="job-known" id="known-plate" aria-live="polite">' in new
    assert "/static/vendor/htmx/htmx.min.js" in new
    assert "hx-get" not in saved
    assert "htmx.min.js" not in saved


def test_known_19_an_error_never_goes_into_a_part_of_a_page_but_a_refused_form_does(client, office):
    # htmx reads this from the page: 40x and 5xx are not swapped, and a form's 422 is (ADR-0016).
    assert """<meta name="htmx-config" content='{"noSwap":[204,304,"40x","5xx"]}'>""" in (
        client.get(NEW).text
    )


def test_known_13_enter_saves_again_and_never_answers(client, office):
    # A browser's Enter presses the form's first submit button, so it must not be an answer.
    toyota = known_toyota(office)

    html = send_new_card(client, plate=toyota.plate).text

    form = html[html.index('<form id="job-form"') :]
    first_button = re.search(r"<button[^>]*>", form)[0]
    assert 'type="submit"' in first_button
    assert "name=" not in first_button
    assert 'tabindex="-1"' in first_button


def known_toyota(member):
    return CarFactory(
        workshop=member.workshop,
        plate="KL10AA1000",
        car_model__brand__name="Toyota",
        car_model__name="Innova",
    )


def a_bmw(member, plate, **values):
    return CarFactory(
        workshop=member.workshop,
        plate=plate,
        car_model__brand__name="BMW",
        car_model__name="520d",
        **values,
    )


def asks_about_another_brand(client, member):
    return send_new_card(client, plate=known_toyota(member).plate)


def asks_about_an_old_plate(client, member):
    car = a_bmw(member, "KL10AA2000")
    visit(member.workshop, car, plate="KA01AB1234")
    return send_new_card(client, plate="KA01AB1234")


def asks_about_a_saved_cards_brand(client, member):
    car = a_bmw(member, "KL10AA1000")
    visit(member.workshop, car)
    return send_card(client, card_of(member, car=car), brand="Toyota")


def asks_about_the_same_car_by_its_vin(client, member):
    a_bmw(member, "KA01AB1234", vin=VIN)
    return send_new_card(client, plate="KL10AA1000", vin=VIN)


def asks_to_check_the_vin(client, member):
    CarFactory(
        workshop=member.workshop,
        plate="KA01AB1234",
        vin=VIN,
        car_model__brand__name="Toyota",
        car_model__name="Innova",
    )
    return send_new_card(client, plate="KL10AA1000", vin=VIN)


def asks_to_move(client, member):
    other = a_bmw(member, "KL10AB2000")
    return send_card(client, card_of(member), plate=other.plate)


def asks_to_move_to_an_old_plate(client, member):
    other = a_bmw(member, "KL10AB2000")
    visit(member.workshop, other, plate="KA01AB1234")
    return send_card(client, card_of(member), plate="KA01AB1234")


def asks_about_a_new_plate(client, member):
    car = a_bmw(member, "KL10AA1000")
    visit(member.workshop, car)
    return send_card(client, card_of(member, car=car), plate="KL10AA1001")


@pytest.mark.parametrize(
    ("asks", "button"),
    [
        (asks_about_another_brand, 0),
        (asks_about_another_brand, 1),
        (asks_about_an_old_plate, 0),
        (asks_about_an_old_plate, 1),
        (asks_about_a_saved_cards_brand, 0),
        (asks_about_a_saved_cards_brand, 1),
        (asks_about_the_same_car_by_its_vin, 0),
        (asks_about_the_same_car_by_its_vin, 1),
        (asks_to_check_the_vin, 0),
        (asks_to_move, 0),
        (asks_to_move_to_an_old_plate, 0),
        (asks_to_move_to_an_old_plate, 1),
        (asks_about_a_new_plate, 0),
        (asks_about_a_new_plate, 1),
    ],
)
def test_known_13_every_button_answers_its_question(client, office, asks, button):
    asked = asks(client, office).text
    value = re.findall(r'<button[^>]*name="answers" value="([^"]+)"', asked)[button]
    action = re.search(r'<form id="job-form"[^>]* action="([^"]+)"', asked)[1]

    response = client.post(action, {**what_the_page_sends(asked), "answers": value})

    assert response.status_code == 302


ANSWERS = r'<button[^>]*name="answers" value="([^"]+)"'
ACTION = r'<form id="job-form"[^>]* action="([^"]+)"'


def test_known_13_a_refused_save_forgets_the_answers_so_each_can_be_changed(client, office):
    # An old plate's car has an open card: "same car" is refused, and "another car" is free.
    car = a_bmw(office, "KL10AA2000")
    visit(office.workshop, car, plate="KA01AB1234")
    card_of(office, car=car)
    asked = send_new_card(client, plate="KA01AB1234").text
    same, another = re.findall(ANSWERS, asked)
    action = re.search(ACTION, asked)[1]

    refused = client.post(action, {**what_the_page_sends(asked), "answers": same}).text
    assert "This car already has an open job card" in refused
    assert 'name="answers"' not in refused

    again = client.post(action, what_the_page_sends(refused)).text
    assert "Is this the same car?" in again

    made = client.post(action, {**what_the_page_sends(again), "answers": another})
    assert made.status_code == 302


def test_known_13_a_refused_move_can_still_be_answered_another_way(client, office):
    other = a_bmw(office, "KL10AB2000")
    visit(office.workshop, other, plate="KA01AB1234")
    card_of(office, car=other)
    asked = send_card(client, card_of(office), plate="KA01AB1234").text
    move, another = re.findall(ANSWERS, asked)
    action = re.search(ACTION, asked)[1]

    refused = client.post(action, {**what_the_page_sends(asked), "answers": move}).text
    assert "This car already has an open job card" in refused
    assert 'name="answers"' not in refused

    again = client.post(action, what_the_page_sends(refused)).text
    assert "Move this job card?" in again

    saved = client.post(action, {**what_the_page_sends(again), "answers": another})
    assert saved.status_code == 302


def test_known_10_a_saved_cards_brand_question_names_the_car_not_the_typed_plate(client, office):
    html = asks_about_a_saved_cards_brand(client, office).text

    assert "BMW 520d, KL10AA1000, has earlier visits." in html
    assert "is the plate of" not in html


def test_known_10_an_old_plate_says_the_cars_plate_today(client, office):
    html = asks_about_an_old_plate(client, office).text

    assert "KA01AB1234 was a plate of BMW 520d." in html
    assert "Its plate now is KL10AA2000." in html


def test_known_10_a_question_says_the_day_the_car_was_last_in_in_the_default_style(client, office):
    # docs/DESIGN.md: a date is 3 Mar 2026, unless a line there says otherwise.
    car = a_bmw(office, "KL10AA2000")
    day = date(2026, 3, 3)
    visit(office.workshop, car, plate="KA01AB1234", days_ago=(timezone.localdate() - day).days)

    html = send_new_card(client, plate="KA01AB1234").text

    assert "Last in on 3 Mar 2026." in html


def test_known_15_the_question_says_the_cars_plate_today(client, office):
    html = asks_about_a_new_plate(client, office).text

    assert "BMW 520d has the plate KL10AA1000, with earlier visits." in html
    assert "Did it get a new plate, KL10AA1001?" in html


def test_known_5_a_page_that_comes_back_has_the_plates_answer(client, office):
    car = a_bmw(office, "KL10AA1000", chassis_code="G30")
    customer = CustomerFactory(workshop=office.workshop, name="Arun K", contact_number="9000000001")
    visit(office.workshop, car, customer=customer)

    html = send_new_card(client, plate="KL10AA1000", mileage="50k").text

    assert "Not saved" in html
    holder = html[html.index('id="known-plate"') :]
    assert 'data-chassis_code="G30"' in holder
    assert 'data-customer_name="Arun K"' in holder


def test_known_8_the_page_that_comes_back_to_floor_has_no_customer(client, floor):
    car = a_bmw(floor, "KL10AA1000")
    customer = CustomerFactory(workshop=floor.workshop, name="Arun K", contact_number="9000000001")
    visit(floor.workshop, car, customer=customer)

    html = send_new_card(client, plate="KL10AA1000", mileage="50k").text

    assert "data-known" in html
    assert "Arun K" not in html
    assert "9000000001" not in html


def test_known_9_a_refused_plate_says_its_open_card_once(client, office):
    open_card = card_of(office, car=a_bmw(office, "KL10AA1000"))

    html = send_new_card(client, plate="KL10AA1000").text

    assert f"This car already has an open job card, {open_card.number}." in html
    assert "This car has an open job card" not in html
    assert html.count(address("jobs:edit", open_card)) == 1


def test_job_4_a_move_onto_a_car_with_an_open_card_is_refused_next_to_the_plate(client, office):
    other = a_bmw(office, "KL10AB2000")
    open_card = card_of(office, car=other)

    html = send_card(client, card_of(office), plate=other.plate).text

    assert f"This car already has an open job card, {open_card.number}." in html
    assert 'id="id_plate_error"' in html
    assert address("jobs:edit", open_card) in html


def test_known_7_use_last_visit_ships_hidden_for_office_and_owners(client, office):
    html = client.get(NEW).text

    assert '<button class="job-use-last" id="job-use-last" type="button" hidden>' in html


def test_known_8_floors_page_has_no_use_last_visit(client, floor):
    assert "job-use-last" not in client.get(NEW).text


def test_known_7_the_server_never_sends_words_inside_the_customer_boxes(client, office):
    html = client.get(NEW).text

    for name in ("customer_name", "contact_number"):
        box = re.search(rf'<input[^>]*name="{name}"[^>]*>', html)[0]
        assert "placeholder" not in box


def test_job_23_a_card_keeps_a_person_who_was_turned_off(client, office):
    gone = StaffMemberFactory(workshop=office.workshop, name="Gone", is_active=False)
    card = card_of(office, lead_mechanic=gone)

    html = client.get(address("jobs:edit", card)).text
    response = send_card(client, card, note="Typed")

    assert "Gone, Mechanic, not current" in html
    assert response.status_code == 302
    card.refresh_from_db()
    assert card.lead_mechanic == gone


def test_job_26_a_card_with_nothing_to_show_folds_its_customer_section(client, office):
    html = client.get(address("jobs:edit", card_of(office))).text

    assert '<details class="job-card job-fold">' in html
    assert 'name="customer_name"' in html


def test_job_26_it_opens_for_a_name_a_number_or_a_note(client, office):
    made = {"workshop": office.workshop}
    only_a_name = CustomerFactory(name="Arun", contact_number="", **made)
    only_a_number = CustomerFactory(name="", contact_number="9000000001", **made)
    for card in (
        card_of(office, customer=only_a_name),
        card_of(office, customer=only_a_number),
        card_of(office, note="A note"),
    ):
        assert (
            '<details class="job-card job-fold" open>'
            in client.get(address("jobs:edit", card)).text
        )


def test_job_21_the_rail_shows_the_colour_and_other_goes_to_the_script(client, office):
    red = card_of(office, car__colour=Colour.RED)
    other = card_of(office, car__colour=Colour.OTHER, car__colour_other="#7f1d1d")
    plain = card_of(office)

    assert 'class="job-head paint-red"' in client.get(address("jobs:edit", red)).text
    assert 'data-paint="#7f1d1d"' in client.get(address("jobs:edit", other)).text
    assert 'class="job-head paint-unset"' in client.get(address("jobs:edit", plain)).text


# Floor.


def test_job_54_floors_page_has_no_customer_and_no_labour_anywhere(client, floor):
    customer = CustomerFactory(
        workshop=floor.workshop, name="Secret Name", contact_number="9000000001"
    )
    card = card_of(floor, customer=customer, labour=Decimal("2950.00"))

    html = client.get(address("jobs:edit", card)).text

    for hidden in (
        "Secret Name",
        "9000000001",
        "2950",
        "customer_name",
        "contact_number",
        "labour",
    ):
        assert hidden not in html
    assert "Labour Charge" not in html
    assert "Customer Name" not in html


def test_job_54_a_floor_send_naming_them_changes_nothing(client, floor):
    customer = CustomerFactory(workshop=floor.workshop, name="Arun")
    card = card_of(floor, customer=customer, labour=Decimal("2950.00"))

    response = send_card(
        client,
        card,
        customer_name="Changed",
        contact_number="",
        labour="1",
        **{"initial-labour": "2950", "initial-customer_name": "Arun"},
    )

    assert response.status_code == 302
    card.refresh_from_db()
    assert card.customer == customer
    assert card.labour == Decimal("2950.00")


def test_job_54_a_new_card_from_floor_has_no_customer_and_no_labour(client, floor):
    send_new_card(client, customer_name="Invented", contact_number="9000000001", labour="1")

    card = cards_of(floor).get()
    assert card.customer is None
    assert card.labour == 0


def test_job_55_floors_section_is_called_workshop_note(client, floor):
    html = client.get(address("jobs:edit", card_of(floor))).text

    assert "Workshop Note" in html
    assert "Anything worth recording about this car" in html
    assert "Customer &amp; Notes" not in html


def test_job_55_floors_section_is_folded_until_it_holds_a_note(client, floor):
    empty = client.get(address("jobs:edit", card_of(floor))).text
    with_a_note = client.get(address("jobs:edit", card_of(floor, note="A note"))).text

    assert '<details class="job-card job-fold">' in empty
    assert '<details class="job-card job-fold" open>' in with_a_note


def test_job_25_floor_may_write_a_note(client, floor):
    card = card_of(floor)

    send_card(client, card, note="Noise only when cold")

    card.refresh_from_db()
    assert card.note == "Noise only when cold"


def test_job_18_floor_may_record_the_chassis_code_and_the_vin(client, floor):
    card = card_of(floor)

    send_card(client, card, chassis_code="f30", vin="WBA8E9C50GK123456")

    card.car.refresh_from_db()
    assert (card.car.chassis_code, card.car.vin) == ("F30", "WBA8E9C50GK123456")


def test_job_50_floor_has_no_cancel_button(client, floor):
    html = client.get(address("jobs:edit", card_of(floor))).text

    assert "Cancel job card" not in html
    assert "jobs/cancel" not in html


# Cancelling.


def test_job_50_office_has_the_button_and_its_card(client, office):
    card = card_of(office, number="JC-0007")

    html = client.get(address("jobs:edit", card)).text

    assert 'data-dialog-open="job-cancel-card"' in html
    assert "Cancel JC-0007?" in html
    assert "Keep job card" in html
    assert f'action="{address("jobs:cancel", card)}"' in html


def test_job_50_a_new_card_has_nothing_to_cancel(client, office):
    assert "Cancel job card" not in client.get(NEW).text


def test_job_50_a_reason_must_be_typed_and_the_card_opens_again(client, office):
    card = card_of(office)

    response = client.post(address("jobs:cancel", card), {"reason": "  "})

    assert response.status_code == 200
    assert "Type why this job card is cancelled." in response.text
    assert 'id="job-cancel-card" aria-labelledby="job-cancel-title" data-open-now' in response.text
    card.refresh_from_db()
    assert card.is_open


def test_job_49_cancelling_keeps_the_card_with_its_notice(client, office):
    card = card_of(office, number="JC-0007")

    response = client.post(address("jobs:cancel", card), {"reason": "Customer left"})

    card.refresh_from_db()
    assert card.status == JobCardStatus.CANCELLED
    assert response.url == address("jobs:edit", card)
    assert notices_of(response) == ["JC-0007 cancelled."]
    assert card.steps.get().by == office.user


def test_job_51_a_cancelled_cards_page_says_why_who_and_when_and_every_box_is_locked(
    client, office
):
    office.user.first_name = "Anil"
    office.user.save()
    card = card_of(office, number="JC-0007")
    client.post(address("jobs:cancel", card), {"reason": "Customer left"})

    html = client.get(address("jobs:edit", card)).text

    assert "Cancelled" in html
    assert "Customer left" in html
    assert "Anil," in html
    assert "The number JC-0007 stays with this card." in html
    assert '<fieldset class="job-form" disabled>' in html
    assert "Update Job Card" not in html
    assert "Cancel job card" not in html
    assert "data-row-template" not in html


def test_job_51_a_send_to_a_cancelled_card_is_refused(client, office):
    card = card_of(office)
    html = client.get(address("jobs:edit", card)).text
    client.post(address("jobs:cancel", card), {"reason": "Customer left"})

    response = client.post(address("jobs:edit", card), what_the_page_sends(html, note="Typed"))

    card.refresh_from_db()
    assert card.note == ""
    assert notices_of(response)[-1] == "This job card is cancelled, so nothing was saved."


def test_job_51_a_second_cancel_changes_nothing(client, office):
    card = card_of(office)
    client.post(address("jobs:cancel", card), {"reason": "First"})

    response = client.post(address("jobs:cancel", card), {"reason": "Second"})

    card.refresh_from_db()
    assert card.cancel_reason == "First"
    assert response.status_code == 302


def test_job_51_a_get_on_the_cancel_address_shows_the_card(client, office):
    card = card_of(office)

    response = client.get(address("jobs:cancel", card))

    assert response.status_code == 200
    assert card.is_open


# A role that may not save.


def test_job_56_a_read_only_role_sees_the_board_and_no_new_button(client, office, monkeypatch):
    # A planted role's list: it may look at the board and may not save.
    monkeypatch.setitem(PERMISSIONS, "jobs.save_job_card", frozenset({Role.OWNER, Role.FLOOR}))
    monkeypatch.setitem(PERMISSIONS, "jobs.cancel_job_card", frozenset({Role.OWNER}))
    card = card_of(office)

    html = client.get(HOME).text

    assert card.plate in html
    assert NEW not in html
    assert client.get(NEW).status_code == 403
    assert client.get(address("jobs:edit", card)).status_code == 403
    assert client.post(address("jobs:edit", card), {"note": "Typed"}).status_code == 403


def test_job_2_each_page_works_in_this_branch(client, office):
    send_new_card(client)

    assert cards_of(office).get().branch == first_branch(cards_of(office).get())


# The lit tab.


def bar_of(response):
    html = response.text
    return html[html.index('<nav class="tab-bar"') : html.index("</nav>")]


def test_job_63_a_job_cards_page_lights_the_home_tab(client, office):
    card = card_of(office)

    for page_address in (NEW, address("jobs:edit", card)):
        bar = bar_of(client.get(page_address))

        assert '<a class="tab" href="/" aria-current="page">' in bar
        assert bar.count('aria-current="page"') == 1
        assert "data-lit" not in bar


def test_job_63_floors_new_card_lights_its_new_tab_and_a_saved_card_its_home_tab(client, floor):
    card = card_of(floor)

    bar = bar_of(client.get(NEW))
    assert '<a class="tab" href="/job-cards/new/" aria-current="page">' in bar
    assert bar.count('aria-current="page"') == 1

    bar = bar_of(client.get(address("jobs:edit", card)))
    assert '<a class="tab" href="/" aria-current="page">' in bar
    assert bar.count('aria-current="page"') == 1

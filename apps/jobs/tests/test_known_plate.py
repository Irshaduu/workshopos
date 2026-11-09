"""What a typed plate names, and the lookup's answer (docs/rules/known-plate.md, KNOWN-1 to
KNOWN-9, KNOWN-18 and KNOWN-19; apps/jobs/selectors.py and views.py). Writing the answer into
the boxes (KNOWN-5, KNOWN-6) needs a browser: its plain functions are in
tests/js/job-card.test.js, and the rest is clicked through by hand until the browser tests
(step 10 of Slice 1)."""

import pytest
from django.urls import reverse

from apps.accounts.models import Role
from apps.accounts.tests.factories import MembershipFactory
from apps.jobs.selectors import car_for_plate, known_car, last_customer
from apps.jobs.tests.cards import visit
from apps.jobs.tests.factories import JobCardFactory
from apps.vehicles.models import Colour
from apps.vehicles.tests.factories import CarFactory, CustomerFactory
from apps.workshops.tests.factories import BranchFactory, WorkshopFactory

pytestmark = pytest.mark.django_db

VIN = "WBA8E9C50GK123456"
LOOKUP = "/job-cards/known-plate/"


def member_of(role, client):
    member = MembershipFactory(role=role)
    client.force_login(member.user)
    return member


def lookup(client, plate):
    return client.get(LOOKUP, {"plate": plate})


# What a plate names (KNOWN-1).


def test_known_1_a_plate_today_names_its_car():
    car = CarFactory(plate="KL10AA1000")

    assert car_for_plate(car.workshop, "KL10AA1000") == car


def test_known_1_an_old_plate_names_the_car_of_its_newest_card():
    workshop = WorkshopFactory()
    first, second = CarFactory(workshop=workshop), CarFactory(workshop=workshop)
    visit(workshop, first, plate="KA01AB1234", days_ago=90)
    visit(workshop, second, plate="KA01AB1234", days_ago=10)

    assert car_for_plate(workshop, "KA01AB1234") == second


def test_known_1_a_plate_no_card_came_with_names_no_car():
    car = CarFactory()

    assert car_for_plate(car.workshop, "KL99ZZ9999") is None
    assert car_for_plate(car.workshop, "") is None


def test_known_3_a_car_with_no_plate_is_never_named_by_an_empty_plate():
    car = CarFactory(plate="")

    assert car_for_plate(car.workshop, "") is None


def test_known_1_another_workshops_plate_names_nothing_here():
    theirs = CarFactory(plate="KL10AA1000")
    visit(theirs.workshop, theirs, plate="KA01AB1234")
    ours = WorkshopFactory()

    assert car_for_plate(ours, "KL10AA1000") is None
    assert car_for_plate(ours, "KA01AB1234") is None


# The last customer (JOB-29), and who may have them (KNOWN-7, KNOWN-8).


def test_job_29_a_cars_customer_is_on_its_newest_card_that_has_one():
    car = CarFactory()
    older = CustomerFactory(workshop=car.workshop, name="Arun K")
    newer = CustomerFactory(workshop=car.workshop, name="Ravi M")
    visit(car.workshop, car, customer=older, days_ago=90)
    visit(car.workshop, car, customer=newer, days_ago=40)
    visit(car.workshop, car, days_ago=5)

    assert last_customer(car.workshop, car) == newer


def test_known_8_with_no_customer_asked_for_none_is_read():
    car = CarFactory()
    visit(car.workshop, car, customer=CustomerFactory(workshop=car.workshop))

    assert known_car(car.workshop, car.plate, with_customer=False).customer is None
    assert known_car(car.workshop, car.plate, with_customer=True).customer is not None


def test_known_9_what_a_plate_found_says_an_old_plate_and_an_open_card():
    car = CarFactory(plate="KL10AA1000")
    visit(car.workshop, car, plate="KA01AB1234")
    open_card = JobCardFactory(workshop=car.workshop, car=car)

    today = known_car(car.workshop, "KL10AA1000", with_customer=False)
    old = known_car(car.workshop, "KA01AB1234", with_customer=False)

    assert (today.old, old.old) == (False, True)
    assert today.open_card == old.open_card == open_card


# The lookup's answer (KNOWN-4, KNOWN-9, KNOWN-19).


def test_known_4_a_known_plate_answers_its_cars_boxes_as_a_part_of_the_page(client):
    member = member_of(Role.FLOOR, client)
    CarFactory(
        workshop=member.workshop,
        plate="KL10AA1000",
        chassis_code="G30",
        vin=VIN,
        colour=Colour.OTHER,
        colour_other="#7f1d1d",
        car_model__brand__name="BMW",
        car_model__name="520d",
    )

    response = lookup(client, "kl-10 aa 1000")

    html = response.text
    assert response.status_code == 200
    assert html.lstrip().startswith('<div class="job-known__answer" data-known')
    for data in (
        'data-brand="BMW"',
        'data-car_model="520d"',
        'data-chassis_code="G30"',
        f'data-vin="{VIN}"',
        'data-colour="other"',
        'data-colour_other="#7f1d1d"',
    ):
        assert data in html
    assert "<html" not in html
    assert "job-known__line" not in html


@pytest.mark.parametrize("plate", ["KL99ZZ9999", "", "   ", "@@@", "\x00", "A" * 21])
def test_known_5_what_names_no_car_answers_nothing_so_the_fill_takes_back(client, plate):
    member = member_of(Role.FLOOR, client)
    CarFactory(workshop=member.workshop, plate="KL10AA1000")

    response = lookup(client, plate)

    assert response.status_code == 200
    assert response.text.strip() == ""


def test_known_9_an_old_plate_says_the_cars_plate_today(client):
    member = member_of(Role.OFFICE, client)
    car = CarFactory(workshop=member.workshop, plate="KL10AA1000")
    visit(member.workshop, car, plate="KA01AB1234")

    html = lookup(client, "KA01AB1234").text

    assert "An old plate of this car. Its plate now is KL10AA1000." in html


def test_known_9_a_car_with_an_open_card_says_so_with_a_link_in_this_branch(client):
    member = member_of(Role.OFFICE, client)
    open_card = JobCardFactory(workshop=member.workshop)

    html = lookup(client, open_card.car.plate).text

    assert f"This car has an open job card, {open_card.number}." in html
    assert reverse("jobs:edit", kwargs={"key": open_card.pk}) in html


def test_known_9_an_open_card_in_another_branch_has_no_link(client):
    member = member_of(Role.OFFICE, client)
    there = BranchFactory(workshop=member.workshop)
    open_card = JobCardFactory(workshop=member.workshop, branch=there)

    html = lookup(client, open_card.car.plate).text

    assert f"This car has an open job card, {open_card.number}." in html
    assert reverse("jobs:edit", kwargs={"key": open_card.pk}) not in html


@pytest.mark.parametrize("role", [Role.OWNER, Role.OFFICE])
def test_known_7_office_and_owners_get_the_last_customer(client, role):
    member = member_of(role, client)
    car = CarFactory(workshop=member.workshop)
    customer = CustomerFactory(workshop=member.workshop, name="Arun K", contact_number="9000000001")
    visit(member.workshop, car, customer=customer)

    html = lookup(client, car.plate).text

    assert 'data-customer_name="Arun K"' in html
    assert 'data-contact_number="9000000001"' in html


def test_known_8_floors_answer_has_nothing_about_the_customer(client):
    member = member_of(Role.FLOOR, client)
    car = CarFactory(workshop=member.workshop)
    customer = CustomerFactory(workshop=member.workshop, name="Arun K", contact_number="9000000001")
    visit(member.workshop, car, customer=customer)

    html = lookup(client, car.plate).text

    assert "data-known" in html
    assert "data-customer" not in html
    assert "data-contact" not in html
    assert "Arun K" not in html
    assert "9000000001" not in html


def test_known_18_the_lookup_only_shows(client):
    member_of(Role.OFFICE, client)

    assert client.post(LOOKUP, {"plate": "KL10AA1000"}).status_code == 405


def test_known_19_an_ended_session_sends_the_whole_page_to_sign_in(client):
    inside = {"HX-Request": "true", "HX-Current-URL": "http://testserver/job-cards/new/"}

    response = client.get(LOOKUP, {"plate": "KL10AA1000"}, headers=inside)

    assert response.status_code == 204
    assert response["HX-Redirect"] == "/sign-in/?next=/job-cards/new/"

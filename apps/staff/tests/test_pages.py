"""The wiring of the Staff list's pages (apps/staff/views.py). The rules themselves are
tested at their service and selector.

Who may open each page, and a record of another workshop: tests/test_permissions.py.
Opening the row buttons and the card needs a browser: that test comes with Playwright
(step 10 of Slice 1). Until then it is clicked through by hand.
"""

import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.accounts.models import Role
from apps.accounts.roles import PERMISSIONS
from apps.accounts.tests.factories import MembershipFactory
from apps.staff.forms import StaffMemberForm
from apps.staff.models import Designation, StaffMember
from apps.staff.tests.factories import StaffMemberFactory
from apps.workshops.tests.factories import BranchFactory

pytestmark = pytest.mark.django_db

LIST = "/staff/"


@pytest.fixture
def owner(client):
    member = MembershipFactory(owner=True)
    client.force_login(member.user)
    return member


def person(owner, **values):
    return StaffMemberFactory(workshop=owner.workshop, **values)


def people(owner):
    return StaffMember.objects.for_workshop(owner.workshop)


def add_address(key=None):
    return reverse("staff:new", kwargs={"key": key or uuid.uuid7()})


def address(name, member):
    return reverse(name, kwargs={"key": member.pk})


def typed(name="Anil Kumar", designation=Designation.MECHANIC, **more):
    return {"name": name, "designation": designation, **more}


# The list.


def test_staff_20_the_page_shows_each_person_under_their_card(client, owner):
    person(owner, name="Anil Kumar")
    person(owner, name="Suresh", designation=Designation.GENERAL_HELPER)

    html = client.get(LIST).text

    assert "<h1>Staff list</h1>" in html
    cards = html[html.index('<div class="staff-grid">') : html.index('<dialog class="menu"')]
    titles = [cards.index(word) for word in ("Mechanic", "Assistant Mechanic", "Office Staff")]
    assert titles == sorted(titles)
    assert cards.index("Mechanic") < cards.index("Anil Kumar") < cards.index("Assistant Mechanic")
    assert cards.index("General Helper") < cards.index(
        '<span class="staff-row__name">Suresh</span>'
    )


def test_staff_20_each_card_shows_its_count(client, owner):
    person(owner)
    person(owner)
    person(owner, is_active=False)

    html = client.get(LIST).text

    assert '<span class="staff-card__count num">3</span>' in html
    assert html.count('<span class="staff-card__count num">0</span>') == 3


def test_staff_21_a_card_with_no_one_says_so(client, owner):
    assert client.get(LIST).text.count("No one yet.") == 4


def test_staff_12_a_turned_off_person_shows_their_tag_and_turn_on(client, owner):
    member = person(owner, is_active=False)

    html = client.get(LIST).text

    assert "staff-row--off" in html
    assert '<span class="badge">Turned off</span>' in html
    assert address("staff:turn_on", member) in html
    assert address("staff:turn_off", member) not in html


def test_staff_12_a_person_turned_on_shows_turn_off(client, owner):
    member = person(owner)

    html = client.get(LIST).text

    assert "staff-row--off" not in html
    assert '<span class="badge">' not in html
    assert address("staff:turn_off", member) in html
    assert address("staff:turn_on", member) not in html


def test_staff_4_the_page_shows_only_its_own_branch(client, owner):
    person(owner, name="Here")
    person(owner, branch=BranchFactory(workshop=owner.workshop), name="Another Place")
    StaffMemberFactory(name="Another Workshop")

    html = client.get(LIST).text

    assert "Here" in html
    assert "Another Place" not in html
    assert "Another Workshop" not in html


def test_staff_9_each_opening_of_the_list_gives_a_new_key(client, owner):
    first = client.get(LIST).context["add_key"]
    second = client.get(LIST).context["add_key"]

    assert first != second
    assert first.version == 7
    assert add_address(first) in client.post(add_address(first), typed(name="")).text


def test_a_name_can_never_write_into_the_page(client, owner):
    # A name is typed by a person, and it comes back in text, in a box's value, in a
    # button's label and in a notice. A capital in it, so the tidy step leaves it alone.
    typed_name = '"><script>Alert(1)</script>'
    escaped = "&quot;&gt;&lt;script&gt;Alert(1)&lt;/script&gt;"

    response = client.post(add_address(), typed(name=typed_name), follow=True)

    assert people(owner).get().name == typed_name
    html = response.text
    assert "<script>Alert" not in html
    assert f'<span class="staff-row__name">{escaped}</span>' in html
    assert f'value="{escaped}"' in html
    assert f'aria-label="More for {escaped}"' in html
    assert f'<p class="notice__text">{escaped} added.</p>' in html


def test_staff_26_the_menu_lights_the_row(client, owner):
    html = client.get(LIST).text

    assert '<a class="menu-link" href="/staff/" aria-current="page">' in html


def test_staff_26_the_page_has_no_back_control(client, owner):
    assert 'class="back"' not in client.get(LIST).text


def test_the_page_loads_its_own_css_and_js_and_the_info_button(client, owner):
    html = client.get(LIST).text

    assert "/static/staff/staff-list.css" in html
    assert "/static/staff/staff-list.js" in html
    assert "/static/js/info.js" in html
    assert 'aria-controls="staff-note"' in html
    assert 'id="staff-note" hidden' in html


# Adding.


def test_staff_8_adding_saves_in_this_branch_and_goes_to_the_list(client, owner):
    key = uuid.uuid7()

    response = client.post(add_address(key), typed(name="anil kumar"), follow=True)

    member = people(owner).get()
    assert member.pk == key
    assert member.name == "Anil Kumar"
    assert response.redirect_chain == [(LIST, 302)]
    assert "Anil Kumar added." in response.text
    assert 'data-sound-tag="success"' in response.text


def test_staff_9_a_double_tap_adds_one_person_and_says_the_same_thing(client, owner):
    key = uuid.uuid7()
    client.post(add_address(key), typed(name="anil kumar"))

    repeat = client.post(add_address(key), typed(name="anil  kumar"), follow=True)

    assert people(owner).get().name == "Anil Kumar"
    assert repeat.redirect_chain == [(LIST, 302)]
    assert "Anil Kumar added." in repeat.text
    assert "already added" not in repeat.text


def test_staff_9_another_name_from_an_old_form_is_not_saved_and_the_page_says_so(client, owner):
    # A page brought back by Back still holds the key it already used.
    key = uuid.uuid7()
    client.post(add_address(key), typed(name="Anil Kumar"))
    client.get(LIST)

    repeat = client.post(add_address(key), typed(name="ravi menon"), follow=True)

    assert people(owner).get().name == "Anil Kumar"
    assert repeat.redirect_chain == [(LIST, 302)]
    assert "This form already added Anil Kumar, so Ravi Menon was not saved." in repeat.text
    assert 'data-sound-tag="warning"' in repeat.text
    assert "Anil Kumar added." not in repeat.text


def test_staff_9_a_repeat_that_fails_the_checks_still_gets_the_list(client, owner):
    # The first send was saved, its answer was lost, and the person then cleared a box.
    key = uuid.uuid7()
    client.post(add_address(key), typed())

    repeat = client.post(add_address(key), typed(name=""), follow=True)

    assert people(owner).count() == 1
    assert repeat.redirect_chain == [(LIST, 302)]
    assert "already added" not in repeat.text


def test_staff_9_a_key_that_is_not_a_uuid7_is_not_found(client, owner):
    response = client.post(add_address(uuid.uuid4()), typed())

    assert response.status_code == 404
    assert not people(owner).exists()


def test_staff_9_a_key_taken_in_another_workshop_is_not_found(client, owner):
    theirs = StaffMemberFactory(name="Theirs")

    response = client.post(add_address(theirs.pk), typed(name="Ours"))

    assert response.status_code == 404
    assert "Theirs" not in response.text
    assert not people(owner).exists()


def test_staff_24_a_taken_name_is_refused_beside_its_box_and_what_was_typed_stays(client, owner):
    person(owner, name="Anil Kumar")
    key = uuid.uuid7()

    response = client.post(add_address(key), typed(name="anil kumar"))

    assert response.status_code == 200
    assert people(owner).count() == 1
    html = response.text
    assert (
        '<p class="field__error" id="add-name-error" role="alert">'
        "This name is already on the staff list.</p>" in html
    )
    assert 'id="add-name"' in html
    assert (
        'value="anil kumar" aria-invalid="true" aria-describedby="add-name-error" autofocus' in html
    )
    # The same key, so the next send is still the same new record.
    assert f'action="{add_address(key)}"' in html


def test_staff_24_an_empty_name_is_refused_and_the_designation_stays(client, owner):
    html = client.post(add_address(), typed(name="")).text

    assert 'id="add-name-error" role="alert">Type a name.</p>' in html
    add_form = html[html.index('id="add-designation"') : html.index("</select>")]
    assert '<option value="mechanic" selected>Mechanic</option>' in add_form


def test_staff_8_a_form_with_no_designation_is_refused(client, owner):
    html = client.post(add_address(), typed(designation="")).text

    assert 'id="add-designation-error" role="alert">Choose a designation.</p>' in html
    assert not people(owner).exists()


def test_staff_8_the_add_form_chooses_no_designation_by_itself(client, owner):
    html = client.get(LIST).text

    add_form = html[html.index('id="add-designation"') : html.index("</select>")]
    assert '<option value="">Choose</option>' in add_form
    assert " selected" not in add_form


def test_staff_24_a_refused_designation_takes_the_keyboard(client, owner):
    html = client.post(add_address(), typed(designation="")).text

    assert 'aria-describedby="add-designation-error" autofocus>' in html


def test_staff_24_the_name_comes_first_when_both_are_refused(client, owner):
    html = client.post(add_address(), typed(name="", designation="")).text

    assert 'aria-describedby="add-name-error" autofocus' in html
    assert 'aria-describedby="add-designation-error" autofocus' not in html


def test_staff_24_an_error_that_belongs_to_no_box_is_shown_too(client, owner, monkeypatch):
    def refuse(form):
        raise ValidationError("This cannot be saved.")

    monkeypatch.setattr(StaffMemberForm, "clean", refuse)

    html = client.post(add_address(), typed()).text

    assert '<p class="field__error" role="alert">This cannot be saved.</p>' in html
    assert not people(owner).exists()


def test_staff_24_a_refused_send_opens_no_edit_card(client, owner):
    person(owner)

    assert "data-open-now" not in client.post(add_address(), typed(name="")).text


def test_a_longer_list_means_no_more_queries_on_a_refused_send_too(client, owner):
    # tests/test_query_counts.py opens the list. A refused send shows it too.
    def queries_with(count):
        for _ in range(count):
            person(owner)
        with CaptureQueriesContext(connection) as queries:
            client.post(add_address(), typed(name=""))
        return len(queries)

    assert queries_with(2) == queries_with(10)


def test_role_13_a_field_not_on_the_form_cannot_be_sent(client, owner):
    other = BranchFactory(workshop=owner.workshop)

    client.post(add_address(), typed(is_active="false", branch=other.pk, workshop=uuid.uuid7()))

    member = people(owner).get()
    assert member.is_active is True
    assert member.branch != other
    assert member.workshop == owner.workshop


# Changing.


def test_staff_10_edit_saves_and_goes_to_the_list(client, owner):
    member = person(owner, name="Old Name")

    response = client.post(
        address("staff:edit", member),
        typed(name="new name", designation=Designation.OFFICE_STAFF),
        follow=True,
    )

    member.refresh_from_db()
    assert member.name == "New Name"
    assert member.designation == Designation.OFFICE_STAFF
    assert response.redirect_chain == [(LIST, 302)]
    assert "New Name updated." in response.text


def test_staff_23_each_card_holds_its_persons_values(client, owner):
    member = person(owner, name="Faisal", designation=Designation.ASSISTANT_MECHANIC)

    html = client.get(LIST).text

    card = html[html.index(f'<dialog class="form-dialog" id="staff-edit-{member.pk}"') :]
    card = card[: card.index("</dialog>")]
    assert f'action="{address("staff:edit", member)}"' in card
    assert 'value="Faisal"' in card
    assert '<option value="assistant_mechanic" selected>Assistant Mechanic</option>' in card
    assert "Choose" not in card
    assert "data-open-now" not in card


def test_staff_23_and_24_a_refused_edit_opens_its_card_with_what_was_typed(client, owner):
    person(owner, name="Anil Kumar")
    member = person(owner, name="Bilal Rahman")

    response = client.post(
        address("staff:edit", member),
        typed(name="anil kumar", designation=Designation.OFFICE_STAFF),
    )

    assert response.status_code == 200
    member.refresh_from_db()
    assert member.name == "Bilal Rahman"
    html = response.text
    assert html.count("data-open-now") == 1
    card = html[html.index(f'id="staff-edit-{member.pk}"') :]
    card = card[: card.index("</dialog>")]
    assert "data-open-now" in card
    assert "This name is already on the staff list." in card
    assert 'value="anil kumar" aria-invalid="true"' in card
    assert '<option value="office_staff" selected>Office Staff</option>' in card
    # The row behind the card still says the name that is saved.
    assert '<span class="staff-row__name">Bilal Rahman</span>' in html
    # The add form stays empty, ready for its own new key.
    assert f'action="{add_address(response.context["add_key"])}"' in html


def test_staff_23_a_refused_edit_with_an_empty_box_opens_its_card_too(client, owner):
    member = person(owner)

    html = client.post(address("staff:edit", member), typed(name="")).text

    card = html[html.index(f'id="staff-edit-{member.pk}"') :]
    assert "Type a name." in card[: card.index("</dialog>")]


# Turning off and on.


def test_staff_11_and_14_turn_off_asks_no_question_keeps_the_person_and_says_so(client, owner):
    member = person(owner, name="Ravi Menon")

    response = client.post(address("staff:turn_off", member), follow=True)

    member.refresh_from_db()
    assert member.is_active is False
    assert response.redirect_chain == [(LIST, 302)]
    assert "Ravi Menon turned off." in response.text
    assert "Ravi Menon</span>" in response.text


def test_staff_13_a_double_tap_on_turn_off_ends_turned_off(client, owner):
    member = person(owner)

    client.post(address("staff:turn_off", member))
    client.post(address("staff:turn_off", member))

    member.refresh_from_db()
    assert member.is_active is False


def test_staff_13_turn_on_brings_them_back(client, owner):
    member = person(owner, name="Ravi Menon", is_active=False)

    response = client.post(address("staff:turn_on", member), follow=True)

    member.refresh_from_db()
    assert member.is_active is True
    assert "Ravi Menon turned on." in response.text


@pytest.mark.parametrize(
    ("name", "is_active"),
    [("staff:turn_off", True), ("staff:turn_on", False), ("staff:edit", True)],
)
def test_a_get_on_an_address_that_saves_changes_nothing(client, owner, name, is_active):
    # Each person is in the state a send to this address would change.
    member = person(owner, name="Ravi Menon", is_active=is_active)

    response = client.get(address(name, member))

    assert response.status_code == 302
    assert response.url == LIST
    member.refresh_from_db()
    assert member.is_active is is_active
    assert member.name == "Ravi Menon"


def test_sign_38_a_get_on_add_goes_to_the_list_and_adds_nothing(client, owner):
    assert client.get(add_address()).url == LIST
    assert not people(owner).exists()


# What each role is offered.


@pytest.mark.parametrize("role", [Role.OFFICE, Role.FLOOR])
@pytest.mark.parametrize("name", ["staff:edit", "staff:turn_off", "staff:turn_on"])
def test_staff_18_only_owners_change_anyone(client, role, name):
    member = MembershipFactory(role=role)
    client.force_login(member.user)
    someone = StaffMemberFactory(workshop=member.workshop, name="Someone")

    response = client.post(address(name, someone), typed(name="Changed"))

    assert response.status_code == 403
    someone.refresh_from_db()
    assert someone.name == "Someone"
    assert someone.is_active is True


@pytest.mark.parametrize("role", [Role.OFFICE, Role.FLOOR])
def test_staff_18_only_owners_add_anyone(client, role):
    member = MembershipFactory(role=role)
    client.force_login(member.user)

    response = client.post(add_address(), typed())

    assert response.status_code == 403
    assert not StaffMember.objects.for_workshop(member.workshop).exists()


@pytest.fixture
def read_only_office(client, monkeypatch):
    """Office, as a read-only role added later would be: it may see, and may not save."""
    monkeypatch.setitem(PERMISSIONS, "staff.see_staff_list", frozenset({Role.OWNER, Role.OFFICE}))
    member = MembershipFactory(role=Role.OFFICE)
    client.force_login(member.user)
    return member


def test_staff_19_a_read_only_role_sees_the_list_with_no_form_and_no_button(
    client, read_only_office
):
    member = StaffMemberFactory(workshop=read_only_office.workshop, name="Anil Kumar")

    html = client.get(LIST).text

    assert '<span class="staff-row__name">Anil Kumar</span>' in html
    assert "<form" not in html[html.index("</nav>") : html.index('<dialog class="menu"')]
    assert "data-row-more" not in html
    assert address("staff:edit", member) not in html
    assert address("staff:turn_off", member) not in html


def test_staff_19_a_read_only_role_is_refused_if_it_sends_one_by_hand(client, read_only_office):
    member = StaffMemberFactory(workshop=read_only_office.workshop, name="Anil Kumar")

    assert client.post(add_address(), typed(name="By Hand")).status_code == 403
    assert client.post(address("staff:edit", member), typed(name="By Hand")).status_code == 403
    assert client.post(address("staff:turn_off", member)).status_code == 403

    member.refresh_from_db()
    assert member.name == "Anil Kumar"
    assert member.is_active is True
    assert StaffMember.objects.for_workshop(read_only_office.workshop).count() == 1

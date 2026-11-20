"""The change history: what is kept when money is changed after it was recorded
(docs/rules/change-history.md, CHANGE-1 to CHANGE-8), at keep_change() and the Change model."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.http import Http404

from apps.accounts.tests.factories import MembershipFactory
from apps.audit.models import Change, ChangedRecord
from apps.audit.services import keep_change
from apps.audit.tests.factories import ChangeFactory
from apps.workshops.models import Branch

pytestmark = pytest.mark.django_db

BEFORE = {
    "date": date(2026, 11, 17),
    "cash": Decimal("40000.00"),
    "upi": None,
    "discount": Decimal("3000.00"),
}


@pytest.fixture
def member():
    return MembershipFactory(owner=True)


def keep(member, after, reason="UPI was part of it", before=BEFORE, **more):
    """Keeps a change to one bill of the member's first branch, under a new key, inside a
    transaction of its own, as a service would."""
    with transaction.atomic():
        return keep_change(
            member.workshop,
            more.pop("branch", Branch.objects.for_workshop(member.workshop).first()),
            member.user,
            key=more.pop("key", uuid.uuid7()),
            what=ChangedRecord.BILL,
            record_key=more.pop("record_key", uuid.uuid7()),
            label="INV-26-27-0045, KL07AB1234",
            before=before,
            after=after,
            reason=reason,
        )


def test_change_1_4_a_change_keeps_each_figure_that_moved_before_and_after(member):
    after = {**BEFORE, "cash": Decimal("38000.00"), "upi": Decimal("2000.00")}

    change = keep(member, after)

    change.refresh_from_db()
    assert change.figures == [
        {"figure": "cash", "kind": "money", "before": "40000.00", "after": "38000.00"},
        {"figure": "upi", "kind": "money", "before": None, "after": "2000.00"},
    ]
    assert (change.by, change.reason, change.what) == (member.user, "UPI was part of it", "bill")
    assert change.at is not None


def test_change_4_each_figure_is_kept_as_it_was_saved(member):
    after = {**BEFORE, "date": date(2026, 11, 16), "discount": Decimal("3000.5")}

    change = keep(member, after)

    assert change.figures == [
        {"figure": "date", "kind": "date", "before": "2026-11-17", "after": "2026-11-16"},
        {"figure": "discount", "kind": "money", "before": "3000.00", "after": "3000.50"},
    ]


def test_change_4_a_save_that_moves_nothing_keeps_nothing(member):
    # 40000 and 40000.00 are one amount.
    assert keep(member, {**BEFORE, "cash": Decimal("40000")}) is None
    assert not Change.objects.exists()


def test_change_4_a_figure_that_goes_is_kept_with_nothing_after(member):
    change = keep(member, {**BEFORE, "cash": None, "upi": Decimal("40000.00")})

    assert change.figures[0] == {
        "figure": "cash",
        "kind": "money",
        "before": "40000.00",
        "after": None,
    }


@pytest.mark.parametrize(
    "after",
    [
        pytest.param({"cash": 40000.5}, id="a float"),
        pytest.param({"cash": date(2026, 11, 17)}, id="a day for an amount"),
        pytest.param({"cash": "38000"}, id="text"),
    ],
)
def test_change_4_a_figure_is_an_amount_or_a_day_on_both_sides(member, after):
    with pytest.raises(TypeError):
        keep(member, {**BEFORE, **after})


def test_change_2_a_change_names_its_record_in_frozen_words_and_has_no_link_to_it(member):
    key = uuid.uuid7()

    change = keep(member, {**BEFORE, "cash": Decimal("1.00")}, record_key=key)

    assert change.record_key == key
    assert change.label == "INV-26-27-0045, KL07AB1234"
    assert not Change._meta.get_field("record_key").is_relation
    links = {field.name for field in Change._meta.get_fields() if field.is_relation}
    assert links == {"workshop", "branch", "by"}


def test_change_2_a_change_keeps_its_records_branch(member):
    branch = Branch.objects.for_workshop(member.workshop).first()

    change = keep(member, {**BEFORE, "cash": Decimal("1.00")}, branch=branch)

    assert change.branch == branch


def test_change_3_a_change_is_kept_under_the_key_its_box_was_opened_with(member):
    key = uuid.uuid7()

    assert keep(member, {**BEFORE, "cash": Decimal("1.00")}, key=key).pk == key


def test_change_3_a_key_another_change_has_is_not_found_and_keeps_nothing(member):
    key = uuid.uuid7()
    keep(member, {**BEFORE, "cash": Decimal("1.00")}, key=key)

    with pytest.raises(Http404):
        keep(member, {**BEFORE, "cash": Decimal("2.00")}, key=key)
    assert Change.objects.count() == 1


def test_change_3_only_a_uuid7_becomes_a_changes_key(member):
    with pytest.raises(Http404):
        keep(member, {**BEFORE, "cash": Decimal("1.00")}, key=uuid.uuid4())


@pytest.mark.django_db(transaction=True)
def test_change_3_a_change_is_kept_only_inside_the_transaction_of_what_it_changed():
    # A real commit for each save, so no test transaction is around this one.
    member = MembershipFactory(owner=True)

    with pytest.raises(RuntimeError):
        keep_change(
            member.workshop,
            Branch.objects.for_workshop(member.workshop).first(),
            member.user,
            key=uuid.uuid7(),
            what=ChangedRecord.BILL,
            record_key=uuid.uuid7(),
            label="INV-26-27-0045",
            before=BEFORE,
            after={**BEFORE, "cash": Decimal("1.00")},
            reason="Wrong amount",
        )


def test_change_3_a_save_that_fails_keeps_nothing(member):
    with pytest.raises(ValueError), transaction.atomic():
        keep(member, {**BEFORE, "cash": Decimal("1.00")})
        raise ValueError("The change itself failed.")

    assert not Change.objects.exists()


@pytest.mark.parametrize("reason", ["", "   "])
def test_change_5_every_change_says_why(member, reason):
    with pytest.raises(ValidationError) as refused:
        keep(member, {**BEFORE, "cash": Decimal("1.00")}, reason=reason)

    assert "reason" in refused.value.message_dict
    assert not Change.objects.exists()


def test_change_5_why_is_kept_tidy_and_up_to_255_characters(member):
    assert keep(member, {**BEFORE, "cash": Decimal("1.00")}, reason="  Wrong   amount ").reason == (
        "Wrong amount"
    )
    with pytest.raises(ValidationError):
        keep(member, {**BEFORE, "cash": Decimal("2.00")}, reason="x" * 256)


def test_change_5_postgresql_refuses_a_change_with_no_reason_or_no_figure():
    with pytest.raises(IntegrityError), transaction.atomic():
        ChangeFactory(reason="")
    with pytest.raises(IntegrityError), transaction.atomic():
        ChangeFactory(figures=[])


def test_change_6_a_kept_change_is_never_changed_or_removed():
    change = ChangeFactory()

    change.reason = "Something else"
    with pytest.raises(TypeError):
        change.save()
    with pytest.raises(TypeError):
        change.delete()
    with pytest.raises(TypeError):
        Change.objects.filter(pk=change.pk).update(reason="Something else")
    with pytest.raises(TypeError):
        Change.objects.filter(pk=change.pk).delete()
    # A new copy of a kept change, forced onto its key, is refused too.
    copy = ChangeFactory.build(id=change.pk, workshop=change.workshop, by=change.by)
    with pytest.raises(TypeError):
        copy.save(force_update=True)
    with pytest.raises(TypeError):
        copy.save(update_fields=["reason"])

    change.refresh_from_db()
    assert change.reason == "Typed the wrong amount"


def test_change_6_the_change_history_is_never_in_the_admin():
    assert Change not in admin.site._registry


def test_change_8_a_change_is_about_one_kind_of_money_record():
    # Each later money record adds its own kind with its module.
    assert ChangedRecord.values == ["bill"]
    with pytest.raises(IntegrityError), transaction.atomic():
        ChangeFactory(what="cashbook")


def test_change_1_the_figures_are_frozen_text_never_money_columns():
    money_columns = [
        field.name for field in Change._meta.get_fields() if isinstance(field, models.DecimalField)
    ]

    assert money_columns == []

"""A link stays inside its workshop (apps/workshops/constraints.py, ADR-0023).

These tests run on a throwaway table, made inside the test's own transaction, so
it is gone when the test ends. tests/test_tenancy.py walks every real link.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, models, transaction
from django.db.migrations.writer import MigrationWriter
from django.test.utils import isolate_apps

from apps.workshops.constraints import SameWorkshop
from apps.workshops.models import Branch, WorkshopModel
from apps.workshops.tests.factories import BranchFactory, WorkshopFactory


@pytest.fixture
def linked(db):
    """A workshop record with an optional link to a branch."""
    with isolate_apps("apps.workshops"):

        class Planted(WorkshopModel):
            branch = models.ForeignKey(
                Branch, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
            )

            class Meta(WorkshopModel.Meta):
                app_label = "workshops"
                constraints = [
                    *WorkshopModel.Meta.constraints,
                    SameWorkshop("branch", name="%(app_label)s_%(class)s_branch_same_workshop"),
                ]

        with connection.schema_editor() as editor:
            editor.create_model(Planted)
        yield Planted


def the_constraint(model):
    (constraint,) = [c for c in model._meta.constraints if isinstance(c, SameWorkshop)]
    return constraint


def constraints_in_postgresql(model):
    with connection.cursor() as cursor:
        return connection.introspection.get_constraints(cursor, model._meta.db_table)


def assert_postgresql_refuses(record):
    # PostgreSQL checks at the end of the transaction, so the check is asked for here.
    with pytest.raises(IntegrityError, match="same_workshop"), transaction.atomic():
        record.save()
        connection.check_constraints()


def test_postgresql_refuses_a_link_to_another_workshops_record(linked):
    ours, theirs = WorkshopFactory(), WorkshopFactory()

    assert_postgresql_refuses(linked(workshop=ours, branch=BranchFactory(workshop=theirs)))


def test_postgresql_takes_a_link_inside_the_workshop(linked):
    ours = WorkshopFactory()

    linked(workshop=ours, branch=BranchFactory(workshop=ours)).save()

    connection.check_constraints()


def test_postgresql_takes_an_empty_link(linked):
    linked(workshop=WorkshopFactory(), branch=None).save()

    connection.check_constraints()


def test_full_clean_refuses_it_first_in_plain_words(linked):
    ours, theirs = WorkshopFactory(), WorkshopFactory()
    record = linked(workshop=ours, branch=BranchFactory(workshop=theirs))

    with pytest.raises(ValidationError) as refused:
        record.full_clean()

    assert refused.value.message_dict == {"branch": ["This belongs to another workshop."]}


def test_full_clean_takes_a_link_inside_the_workshop(linked):
    ours = WorkshopFactory()

    linked(workshop=ours, branch=BranchFactory(workshop=ours)).full_clean()


def test_full_clean_takes_an_empty_link(linked):
    linked(workshop=WorkshopFactory(), branch=None).full_clean()


@pytest.mark.parametrize("left_out", ["workshop", "branch"])
def test_a_form_that_leaves_out_either_side_skips_the_check(linked, left_out):
    ours, theirs = WorkshopFactory(), WorkshopFactory()
    record = linked(workshop=ours, branch=BranchFactory(workshop=theirs))

    the_constraint(linked).validate(linked, record, exclude={left_out})


def test_migration_steps_remove_it_and_add_it_again(linked):
    constraint = the_constraint(linked)
    assert constraint.name in constraints_in_postgresql(linked)

    with connection.schema_editor() as editor:
        editor.remove_constraint(linked, constraint)
    assert constraint.name not in constraints_in_postgresql(linked)

    with connection.schema_editor() as editor:
        editor.add_constraint(linked, constraint)
    assert constraint.name in constraints_in_postgresql(linked)

    ours, theirs = WorkshopFactory(), WorkshopFactory()
    assert_postgresql_refuses(linked(workshop=ours, branch=BranchFactory(workshop=theirs)))


def test_migrations_can_write_it_down():
    written, imports = MigrationWriter.serialize(SameWorkshop("branch", name="a_name"))

    assert written == "apps.workshops.constraints.SameWorkshop(link='branch', name='a_name')"
    assert imports == {"import apps.workshops.constraints"}


def test_a_copy_equals_the_first_so_migrations_see_no_change():
    constraint = SameWorkshop("branch", name="a_name")

    assert constraint.clone() == constraint


@pytest.mark.parametrize(
    "other",
    [SameWorkshop("car", name="a_name"), SameWorkshop("branch", name="another_name"), "a_name"],
)
def test_another_link_or_name_is_a_change(other):
    assert SameWorkshop("branch", name="a_name") != other

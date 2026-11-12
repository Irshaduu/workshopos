"""A link stays inside its branch (apps/workshops/constraints.py, ADR-0032).

Like test_same_workshop.py, these run on throwaway tables made inside the test's own
transaction. The real link, a bill's to its job card, is tested in apps/billing/tests.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, models, transaction
from django.db.migrations.writer import MigrationWriter
from django.test.utils import isolate_apps

from apps.workshops.constraints import SameBranch, SameWorkshop
from apps.workshops.models import Branch, BranchModel
from apps.workshops.tests.factories import BranchFactory, WorkshopFactory


@pytest.fixture
def linked(db):
    """A branch record with an optional link to another branch record, kept in its branch."""
    with isolate_apps("apps.workshops"):

        class Target(BranchModel):
            class Meta(BranchModel.Meta):
                app_label = "workshops"
                constraints = [
                    *BranchModel.Meta.constraints,
                    models.UniqueConstraint(fields=["branch", "id"], name="target_branch_id"),
                ]

        class Planted(BranchModel):
            target = models.ForeignKey(
                Target, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
            )

            class Meta(BranchModel.Meta):
                app_label = "workshops"
                constraints = [
                    *BranchModel.Meta.constraints,
                    SameWorkshop("target", name="planted_target_same_workshop"),
                    SameBranch("target", name="planted_target_same_branch"),
                ]

        with connection.schema_editor() as editor:
            editor.create_model(Target)
            editor.create_model(Planted)
        yield Target, Planted


def two_branches():
    """A workshop, its first branch, and a second one."""
    workshop = WorkshopFactory()
    return workshop, Branch.objects.for_workshop(workshop).get(), BranchFactory(workshop=workshop)


def test_postgresql_refuses_a_link_to_another_branchs_record(linked):
    target_model, planted = linked
    workshop, here, there = two_branches()
    target = target_model.objects.create(workshop=workshop, branch=there)

    with pytest.raises(IntegrityError, match="same_branch"), transaction.atomic():
        planted(workshop=workshop, branch=here, target=target).save()
        connection.check_constraints()


def test_postgresql_takes_a_link_inside_the_branch(linked):
    target_model, planted = linked
    workshop, here, _there = two_branches()
    target = target_model.objects.create(workshop=workshop, branch=here)

    planted(workshop=workshop, branch=here, target=target).save()

    connection.check_constraints()


def test_full_clean_refuses_it_first_in_plain_words(linked):
    target_model, planted = linked
    workshop, here, there = two_branches()
    target = target_model.objects.create(workshop=workshop, branch=there)
    record = planted(workshop=workshop, branch=here, target=target)

    with pytest.raises(ValidationError) as refused:
        record.full_clean()

    assert refused.value.message_dict == {"target": ["This belongs to another branch."]}


def test_migrations_can_write_it_down():
    written, imports = MigrationWriter.serialize(SameBranch("job_card", name="a_name"))

    assert written == "apps.workshops.constraints.SameBranch(link='job_card', name='a_name')"
    assert imports == {"import apps.workshops.constraints"}


def test_it_is_never_taken_for_a_same_workshop_check_and_back():
    assert SameBranch("job_card", name="a_name") != SameWorkshop("job_card", name="a_name")
    assert SameWorkshop("job_card", name="a_name") != SameBranch("job_card", name="a_name")
    assert SameBranch("job_card", name="a_name").clone() == SameBranch("job_card", name="a_name")

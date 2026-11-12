"""Shared by the tests of workshops."""

import pytest
from django.db import connection, models
from django.test.utils import isolate_apps

from apps.workshops.models import BranchModel


@pytest.fixture
def planted(db):
    """A record with a branch, on a throwaway table.

    The table is made inside the test's own transaction, so it is gone when the
    test ends. tests/test_tenancy.py covers every real one by itself.
    """
    with isolate_apps("apps.workshops"):

        class Planted(BranchModel):
            class Meta(BranchModel.Meta):
                app_label = "workshops"

        with connection.schema_editor() as editor:
            editor.create_model(Planted)
        yield Planted


@pytest.fixture
def planted_under(db):
    """A parent and a record under it, like a job card and its bill, on throwaway tables."""
    with isolate_apps("apps.workshops"):

        class Parent(BranchModel):
            class Meta(BranchModel.Meta):
                app_label = "workshops"

        class Child(BranchModel):
            parent = models.ForeignKey(Parent, on_delete=models.PROTECT, related_name="+")

            class Meta(BranchModel.Meta):
                app_label = "workshops"

        with connection.schema_editor() as editor:
            editor.create_model(Parent)
            editor.create_model(Child)
        yield Parent, Child

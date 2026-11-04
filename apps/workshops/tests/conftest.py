"""Shared by the tests of workshops."""

import pytest
from django.db import connection
from django.test.utils import isolate_apps

from apps.workshops.models import BranchModel


@pytest.fixture
def planted(db):
    """A record with a branch, on a throwaway table.

    The table is made inside the test's own transaction, so it is gone when the
    test ends. The first real one comes with the Staff list; tests/test_tenancy.py
    then covers every real one by itself.
    """
    with isolate_apps("apps.workshops"):

        class Planted(BranchModel):
            class Meta(BranchModel.Meta):
                app_label = "workshops"

        with connection.schema_editor() as editor:
            editor.create_model(Planted)
        yield Planted

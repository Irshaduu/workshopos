"""Shared by the project-wide tests."""

import pytest
from django.apps import apps


@pytest.fixture
def our_models():
    """Every model in our apps, without the link tables Django makes itself."""
    found = [
        model
        for model in apps.get_models()
        if model.__module__.startswith("apps.") and not model._meta.auto_created
    ]
    assert found, "No model found in apps/."
    return found

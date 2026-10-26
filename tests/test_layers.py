"""Apps use only the floors below their own (ADR-0005, ADR-0021).

import-linter checks the imports. A model link written as text, like
ForeignKey("billing.FleetAccount"), needs no import, so the tests here check
the model links, with the same floors from pyproject.toml.
"""

import tomllib
from pathlib import Path

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.db import models
from importlinter.cli import lint_imports

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def floors():
    """Each app's floor, from the import-linter settings. 0 is the top floor."""
    settings = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["tool"]["importlinter"]
    (contract,) = [c for c in settings["contracts"] if c["type"] == "layers"]
    floor_of = {}
    for number, row in enumerate(contract["layers"]):
        for app in row.replace(":", "|").split("|"):
            floor_of[app.strip().strip("()")] = number
    return floor_of


def model_links(models_to_check):
    """Every link a model makes: (its app, the app it points to, where)."""
    return [
        (
            model._meta.app_label,
            field.related_model._meta.app_label,
            f"{model._meta.label}.{field.name}",
        )
        for model in models_to_check
        for field in model._meta.get_fields()
        if field.is_relation and not field.auto_created and field.related_model is not None
    ]


def upward_links(links, floor_of):
    """Where a link points to the same row or higher. Django's own apps sit below everything."""
    return [
        where
        for source, target, where in links
        if source != target and target in floor_of and floor_of[target] <= floor_of[source]
    ]


def generic_links(models_to_check):
    """Where a model uses a generic link, which PostgreSQL cannot guard (ADR-0019)."""
    return [
        f"{model._meta.label}.{field.name}"
        for model in models_to_check
        for field in model._meta.get_fields()
        if isinstance(field, GenericForeignKey | GenericRelation)
    ]


def test_imports_go_only_to_lower_floors(capsys):
    passed = lint_imports(no_cache=True, no_logo=True) == 0

    assert passed, capsys.readouterr().out


def test_every_app_with_models_has_a_floor(our_models):
    assert {model._meta.app_label for model in our_models} - floors().keys() == set()


def test_every_model_link_points_to_a_lower_floor(our_models):
    assert upward_links(model_links(our_models), floors()) == []


def test_no_model_uses_a_generic_link(our_models):
    assert generic_links(our_models) == []


def test_a_link_to_a_higher_floor_is_caught():
    floor_of = {"accounts": 6, "workshops": 7}
    link = ("workshops", "accounts", "workshops.Workshop.created_by")

    assert upward_links([link], floor_of) == ["workshops.Workshop.created_by"]


def test_a_link_inside_one_row_is_caught():
    floor_of = {"billing": 1, "finance": 1}
    link = ("billing", "finance", "billing.Invoice.cashbook_entry")

    assert upward_links([link], floor_of) == ["billing.Invoice.cashbook_entry"]


def test_links_to_a_lower_floor_or_to_django_are_allowed():
    floor_of = {"jobs": 2, "vehicles": 4}
    links = [
        ("jobs", "vehicles", "jobs.JobCard.vehicle"),
        ("jobs", "auth", "jobs.JobCard.created_by_group"),
        ("jobs", "jobs", "jobs.JobCardLine.job_card"),
    ]

    assert upward_links(links, floor_of) == []


def test_a_generic_link_is_caught():
    class Planted(models.Model):
        content_type = models.ForeignKey("contenttypes.ContentType", on_delete=models.CASCADE)
        object_id = models.UUIDField()
        subject = GenericForeignKey("content_type", "object_id")

        class Meta:
            abstract = True
            app_label = "core"

    assert generic_links([Planted]) == ["core.Planted.subject"]

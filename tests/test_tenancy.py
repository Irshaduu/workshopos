"""Each workshop's data stays its own (ADR-0023).

Every business model builds on WorkshopModel, and one leak test covers every
workshop model by itself. Page leak tests come with the permission matrix.
"""

from importlib import import_module

import pytest
from django.contrib.auth.models import Group
from django.db import models

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory
from apps.workshops.models import WorkshopModel
from apps.workshops.tests.factories import WorkshopFactory

#: Models in our apps that do not belong to one workshop, and why.
NOT_WORKSHOP_MODELS = {
    "accounts.User": "one person can belong to several workshops",
    "accounts.SignInCode": "it belongs to an account, not to a workshop (ADR-0025)",
    "workshops.Workshop": "it is the workshop itself",
}


def workshop_problem(model):
    """What is wrong with a model's workshop link, or None when it is right."""
    if not issubclass(model, WorkshopModel):
        return "it does not build on WorkshopModel"
    pairs = [
        constraint
        for constraint in model._meta.constraints
        if isinstance(constraint, models.UniqueConstraint)
        and tuple(constraint.fields) == ("workshop", "id")
        and constraint.condition is None
    ]
    if not pairs:
        return "it lost the unique (workshop, id) pair: keep WorkshopModel.Meta.constraints"
    return None


def factory_for(model):
    """The model's factory: <Model>Factory in its app's tests/factories.py, or None."""
    module_name = f"{model._meta.app_config.name}.tests.factories"
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as error:
        # Only a missing factories file (or its tests folder) means "no factory";
        # a bad import inside the file must still fail loudly.
        if not f"{module_name}.".startswith(f"{error.name}."):
            raise
        return None
    return getattr(module, f"{model.__name__}Factory", None)


def workshop_models(our_models):
    return [model for model in our_models if model._meta.label not in NOT_WORKSHOP_MODELS]


def test_every_business_model_belongs_to_a_workshop(our_models):
    problems = {model._meta.label: workshop_problem(model) for model in workshop_models(our_models)}

    assert {label: problem for label, problem in problems.items() if problem} == {}


def test_every_model_left_out_still_exists(our_models):
    assert NOT_WORKSHOP_MODELS.keys() - {model._meta.label for model in our_models} == set()


def test_a_model_without_a_workshop_is_caught():
    assert workshop_problem(User) == "it does not build on WorkshopModel"


def test_a_model_that_lost_the_unique_pair_is_caught():
    class Planted(WorkshopModel):
        class Meta:
            abstract = True
            app_label = "workshops"
            constraints = []

    assert workshop_problem(Planted).startswith("it lost the unique (workshop, id) pair")


def test_a_factory_is_found_by_its_name():
    assert factory_for(User) is UserFactory
    assert factory_for(Group) is None


@pytest.mark.django_db
def test_a_workshop_sees_only_its_own_records(our_models):
    ours, theirs = WorkshopFactory(), WorkshopFactory()
    leaks = {}

    for model in workshop_models(our_models):
        make = factory_for(model)
        if make is None:
            leaks[model._meta.label] = f"no {model.__name__}Factory in its app's tests/factories.py"
            continue
        own, other = make(workshop=ours), make(workshop=theirs)
        seen = set(model.objects.for_workshop(ours))
        if own not in seen or other in seen:
            leaks[model._meta.label] = "for_workshop() did not return only its own records"

    assert leaks == {}

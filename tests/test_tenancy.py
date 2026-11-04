"""Each workshop's data stays its own (ADR-0023).

Every business model builds on WorkshopModel, and one leak test covers every
workshop model by itself. Page leak tests come with the permission matrix.
"""

from importlib import import_module

import pytest
from django.contrib.auth.models import Group
from django.db import connection, models
from django.test.utils import isolate_apps

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory
from apps.workshops.constraints import SameWorkshop
from apps.workshops.models import Branch, BranchModel, WorkshopModel
from apps.workshops.tests.factories import BranchFactory, WorkshopFactory

#: Models in our apps that do not belong to one workshop, and why.
NOT_WORKSHOP_MODELS = {
    "accounts.User": "one person can belong to several workshops",
    "accounts.SignInCode": "it belongs to an account, not to a workshop (ADR-0025)",
    "workshops.Workshop": "it is the workshop itself",
}

#: Workshop models with no branch link, and why. A short list: each record of
#: any other model knows its branch, so a second place changes no real record
#: (ADR-0028).
WORKSHOP_WIDE_MODELS = {
    "accounts.Membership": "a person belongs to the workshop; Branch screens limit what they see",
    "workshops.Branch": "it is the branch itself",
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


def branch_link_problem(model):
    """What is wrong with a workshop model's branch link, or None when it is right."""
    if issubclass(model, BranchModel) or model._meta.label in WORKSHOP_WIDE_MODELS:
        return None
    return "it does not build on BranchModel, and it is not on the workshop-wide list"


def unguarded_links(model):
    """Each link to a workshop record that PostgreSQL does not keep inside its workshop."""
    guarded = {
        constraint.link
        for constraint in model._meta.constraints
        if isinstance(constraint, SameWorkshop)
    }
    return [
        field.name
        for field in model._meta.get_fields()
        if field.is_relation
        and not field.auto_created
        and field.related_model is not None
        and issubclass(field.related_model, WorkshopModel)
        and field.name not in guarded
    ]


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


def test_every_business_model_has_a_branch_link_or_a_reason(our_models):
    problems = {
        model._meta.label: branch_link_problem(model) for model in workshop_models(our_models)
    }

    assert {label: problem for label, problem in problems.items() if problem} == {}


def test_every_workshop_wide_model_exists_and_has_no_branch_link(our_models):
    workshop_wide = [model for model in our_models if model._meta.label in WORKSHOP_WIDE_MODELS]

    assert {model._meta.label for model in workshop_wide} == WORKSHOP_WIDE_MODELS.keys()
    assert [model for model in workshop_wide if issubclass(model, BranchModel)] == []


def test_a_model_with_no_branch_link_and_no_reason_is_caught():
    class Planted(WorkshopModel):
        class Meta:
            abstract = True
            app_label = "workshops"

    assert "workshop-wide list" in branch_link_problem(Planted)


def test_every_link_to_a_workshop_record_stays_inside_its_workshop(our_models):
    links = {model._meta.label: unguarded_links(model) for model in workshop_models(our_models)}

    assert {label: names for label, names in links.items() if names} == {}


@isolate_apps("apps.workshops")
def test_a_link_with_no_same_workshop_is_caught_and_one_with_it_passes():
    class Planted(WorkshopModel):
        unguarded = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="+")
        guarded = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="+")
        also_unguarded = models.OneToOneField(Branch, on_delete=models.PROTECT, related_name="+")
        many = models.ManyToManyField(Branch, related_name="+")

        class Meta(WorkshopModel.Meta):
            app_label = "workshops"
            constraints = [SameWorkshop("guarded", name="guarded_same_workshop")]

    assert sorted(unguarded_links(Planted)) == ["also_unguarded", "many", "unguarded"]


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
    # A factory gives its linked records the same workshop, or PostgreSQL refuses here.
    connection.check_constraints()


@pytest.mark.django_db
def test_a_branch_sees_only_its_own_records(our_models):
    ours = WorkshopFactory(first_branch=None)
    here, there = BranchFactory(workshop=ours), BranchFactory(workshop=ours)
    leaks = {}

    for model in our_models:
        if not issubclass(model, BranchModel):
            continue
        make = factory_for(model)
        own, other = make(workshop=ours, branch=here), make(workshop=ours, branch=there)
        seen = set(model.objects.for_workshop(ours).for_branch(here))
        if own not in seen or other in seen:
            leaks[model._meta.label] = "for_branch() did not return only its own records"

    assert leaks == {}

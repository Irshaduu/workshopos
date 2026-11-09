"""Every query asks for its workshop, and for its branch (ADR-0023, ADR-0028).

A forgotten for_workshop() shows one workshop's records to another, and until
row-level security comes, PostgreSQL would not stop it. So this test reads every
query in apps/. It reads the code with Python's own parser, not as lines of text,
so a call written on two lines cannot get past it, and a word in a docstring
cannot set it off.

A query that truly cannot start there says why, on its own lines or in a comment on
the line above:

    # not for_workshop: this is how a request finds its workshop.

A record with a branch that truly spans branches says # not for_branch: and why.

A form's link field queries by itself too, with no code of ours to read, so the
forms are checked as well: each link field starts empty.
"""

import ast
import re
from importlib import import_module
from pathlib import Path

import pytest
from django import forms
from django.apps import apps
from django.conf import settings
from django.db import models
from django.test.utils import isolate_apps
from django.utils.module_loading import module_has_submodule
from test_tenancy import NOT_WORKSHOP_MODELS, WORKSHOP_WIDE_MODELS

from apps.workshops.models import Branch, WorkshopModel

APPS = Path(settings.BASE_DIR) / "apps"

SHORTCUTS = {"get_object_or_404", "get_list_or_404", "aget_object_or_404", "aget_list_or_404"}


def scanned_files():
    """Every Python file in apps/, except tests and migrations, which never run on a
    page, and admin.py, because the Django admin is not scoped (ADR-0023)."""
    return [
        path
        for path in APPS.rglob("*.py")
        if path.name != "admin.py"
        and not {"tests", "migrations"} & set(path.relative_to(APPS).parts)
    ]


def goes_on_to(node, method, parents):
    """Whether this code goes straight on to a call of this method."""
    attribute = parents.get(node)
    return (
        isinstance(attribute, ast.Attribute)
        and attribute.attr == method
        and isinstance(parents.get(attribute), ast.Call)
    )


def objects_problem(node, parents, no_workshop, workshop_wide):
    """What is wrong with one Model.objects, or None when it starts as it must."""
    match node.value:
        case ast.Name(id=model) | ast.Attribute(attr=model):
            pass
        case _:
            model = None
    if model in no_workshop:
        return None
    # No rows at all: a form's link field starts like this.
    if goes_on_to(node, "none", parents):
        return None
    if not goes_on_to(node, "for_workshop", parents):
        return "workshop", "it does not start with for_workshop()"
    # Anything not known to be workshop-wide must ask, so an alias or
    # type(record).objects cannot get past.
    if model not in workshop_wide and not goes_on_to(parents[parents[node]], "for_branch", parents):
        return "branch", "it may have a branch, but for_branch() does not come right after"
    return None


def call_problem(node):
    """What is wrong with one call that can query by itself, or None."""
    match node.func:
        case ast.Name(id=name) | ast.Attribute(attr=name):
            pass
        case _:
            return None
    if name in SHORTCUTS:
        klass = (kw.value for kw in node.keywords if kw.arg == "klass")
        first = node.args[0] if node.args else next(klass, None)
        # A call here is a query, which the check on .objects reads by itself.
        if not isinstance(first, ast.Call):
            return "workshop", f"{name}(Model, ...) queries by itself; give it a for_workshop()"
    if name == "modelformset_factory":
        return "workshop", "a model form set shows every workshop's rows by default"
    if name == "as_view" and any(kw.arg == "model" for kw in node.keywords):
        return "workshop", "as_view(model=...) queries by itself"
    if name in {"raw", "cursor"}:
        return "workshop", "raw SQL never asks for a workshop"
    return None


def problem_of(node, parents, no_workshop, workshop_wide):
    """The word its reason must use, and what is wrong; or None when nothing is."""
    match node:
        case ast.Attribute(attr="objects"):
            return objects_problem(node, parents, no_workshop, workshop_wide)
        case ast.Attribute(
            attr="_default_manager" | "_base_manager" | "default_manager" | "base_manager" as name
        ):
            return "workshop", f"{name} goes around for_workshop()"
        case ast.Call():
            return call_problem(node)
        case (
            ast.Assign(targets=[ast.Name(id="model")]) | ast.AnnAssign(target=ast.Name(id="model"))
        ):
            owner = parents[node]
            if isinstance(owner, ast.ClassDef) and owner.name != "Meta":
                return "workshop", "a class-based view's model = queries by itself"
    return None


def says_why(node, word, parents, lines):
    """Whether a comment gives the reason, on the statement's lines or the line above."""
    statement = node
    while not isinstance(statement, ast.stmt):
        statement = parents[statement]
    first = statement.lineno - 1
    own = lines[first : node.end_lineno]
    # The line above counts only as a comment of its own: the end of the last
    # statement is that statement's reason.
    above = [line for line in lines[max(first - 1, 0) : first] if line.lstrip().startswith("#")]
    reason = re.compile(rf"# not for_{word}: \S")
    return any(reason.search(line) for line in [*above, *own])


def query_problems(source, no_workshop=frozenset(), workshop_wide=frozenset()):
    """What breaks the rule in this code: a list of (line number, what is wrong)."""
    tree = ast.parse(source)
    lines = source.splitlines()
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}

    found = []
    for node in ast.walk(tree):
        problem = problem_of(node, parents, no_workshop, workshop_wide)
        if problem is not None and not says_why(node, problem[0], parents, lines):
            found.append((node.lineno, problem[1]))
    return sorted(found)


def model_names(labels):
    return {label.split(".")[1] for label in labels}


def locks_and_joins(source):
    """The lines of the queries that lock their rows and join others too. A save that waited for
    the lock would get the row as it is now beside the linked row as it was, or no row at all
    when the link changed, because PostgreSQL checks the join again with the old linked row."""
    lock_or_join = {"select_for_update", "select_related"}
    lines = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Attribute) and node.attr in lock_or_join:
            below = node.value
            while isinstance(below, ast.Call | ast.Attribute):
                if isinstance(below, ast.Attribute) and below.attr in lock_or_join - {node.attr}:
                    lines.append(node.lineno)
                below = below.func if isinstance(below, ast.Call) else below.value
    return lines


def test_a_locking_query_joins_nothing():
    found = {str(path): locks_and_joins(path.read_text()) for path in scanned_files()}

    assert {name: lines for name, lines in found.items() if lines} == {}


@pytest.mark.parametrize(
    "source",
    [
        'Car.objects.select_for_update().select_related("car_model")',
        'Car.objects.select_related("car_model").select_for_update(of=("self",))',
        'Car.objects.select_related("car_model").filter(pk=1).select_for_update()',
    ],
)
def test_a_query_that_locks_and_joins_is_caught(source):
    assert locks_and_joins(source) == [1]


def test_a_lock_alone_and_a_join_alone_pass():
    assert locks_and_joins("Car.objects.select_for_update().get(pk=1)") == []
    assert locks_and_joins('Car.objects.select_related("car_model").get(pk=1)') == []


def test_every_query_in_the_apps_asks_for_its_workshop_and_its_branch():
    files = scanned_files()
    # A floor, so a scan that read nothing cannot pass for being clean.
    assert len(files) >= 20, files
    no_workshop = model_names(NOT_WORKSHOP_MODELS)
    workshop_wide = model_names(WORKSHOP_WIDE_MODELS)

    found = [
        f"{path.relative_to(settings.BASE_DIR)}:{number}: {what}"
        for path in files
        for number, what in query_problems(
            path.read_text(encoding="utf-8"), no_workshop, workshop_wide
        )
    ]

    assert not found, "Start with for_workshop(), or say why on the line above:\n" + "\n".join(
        found
    )


def test_the_scan_reads_the_files_with_queries_and_leaves_out_the_rest():
    names = {str(path.relative_to(APPS).as_posix()) for path in scanned_files()}

    assert {"accounts/selectors.py", "accounts/services.py", "accounts/views.py"} <= names
    assert "accounts/admin.py" not in names
    assert not [name for name in names if "/tests/" in name or "/migrations/" in name]


# Planted code: Bill is workshop-wide, User has no workshop, and any other model, like
# Visit, has a branch.
def planted_problems(source):
    return query_problems(source, no_workshop={"User"}, workshop_wide={"Bill"})


@pytest.mark.parametrize(
    "source",
    [
        "Bill.objects.all()",
        "Bill.objects.get(pk=1)",
        "Bill.objects.create(a=1)",
        "Bill.objects.filter(a=1).for_workshop(w)",
        "models.Bill.objects.all()",
        "bills = Bill.objects",
        "Bill.objects.for_workshop",
        "self.model.objects.all()",
        "type(record).objects.all()",
        "Prefetch('bills', queryset=Bill.objects.all())",
        "Bill._default_manager.all()",
        "Bill._base_manager.all()",
        "Bill._default_manager.for_workshop(w)",
        "Bill._meta.default_manager.all()",
        "Bill._meta.base_manager.all()",
        "get_object_or_404(Bill, pk=1)",
        "get_object_or_404(\n    Bill,\n    pk=1,\n)",
        "get_object_or_404(models.Bill, pk=1)",
        "get_object_or_404(klass=Bill, pk=1)",
        "shortcuts.get_object_or_404(Bill, pk=1)",
        "get_list_or_404(Bill, a=1)",
        "aget_object_or_404(Bill, pk=1)",
        "aget_list_or_404(Bill, a=1)",
        "modelformset_factory(Bill)",
        "class BillList(ListView):\n    model = Bill\n",
        "class BillList(ListView):\n    model: type = Bill\n",
        "ListView.as_view(model=Bill)",
        "Bill.objects.for_workshop(w).raw('select 1')",
        "connection.cursor()",
        "connections['default'].cursor()",
        "django.db.connection.cursor()",
        "Bill.objects.for_workshop(w)\nBill.objects.all()",
    ],
)
def test_a_query_with_no_workshop_is_caught(source):
    assert planted_problems(source)


@pytest.mark.parametrize(
    "source",
    [
        "Visit.objects.for_workshop(w)",
        "Visit.objects.for_workshop(w).filter(a=1)",
        "Visit.objects.for_workshop(w).filter(a=1).for_branch(b)",
        "get_object_or_404(Visit.objects.for_workshop(w), pk=1)",
        "models.Visit.objects.for_workshop(w)",
        "self.model.objects.for_workshop(w)",
        "type(record).objects.for_workshop(w)",
    ],
)
def test_a_record_that_may_have_a_branch_and_does_not_ask_for_it_is_caught(source):
    assert "for_branch" in planted_problems(source)[0][1]


def test_a_problem_names_its_line():
    assert planted_problems("x = 1\n\nBill.objects.all()")[0][0] == 3


@pytest.mark.parametrize(
    "source",
    [
        "Bill.objects.for_workshop(w)",
        "Bill.objects.for_workshop(w).filter(a=1).first()",
        "models.Bill.objects.for_workshop(w)",
        "bills = (\n    Bill.objects.for_workshop(w)\n    .filter(a=1)\n    .first()\n)",
        "get_object_or_404(Bill.objects.for_workshop(w), pk=1)",
        "get_object_or_404(klass=Bill.objects.for_workshop(w), pk=1)",
        "Visit.objects.for_workshop(w).for_branch(b).filter(a=1)",
        "models.Visit.objects.for_workshop(w).for_branch(b)",
        "get_object_or_404(Visit.objects.for_workshop(w).for_branch(b), pk=1)",
        "Visit.objects.none()",
        "User.objects.filter(a=1)",
        "models.User.objects.filter(a=1)",
        "class BillForm(ModelForm):\n    class Meta:\n        model = Bill\n",
        "model = Bill",
        "def view():\n    model = Bill\n",
        "HomePage.as_view()",
        "objects = BillQuerySet.as_manager()",
        "text = 'Bill.objects.all()'",
        '"""Bill.objects.all() in a docstring."""',
        "# Bill.objects.all() in a comment",
    ],
)
def test_good_code_passes(source):
    assert planted_problems(source) == []


@pytest.mark.parametrize(
    "source",
    [
        "# not for_workshop: a good reason\nBill.objects.all()",
        "Bill.objects.all()  # not for_workshop: a good reason",
        "# not for_workshop: a good reason\nbills = (\n    Bill.objects.all()\n)",
        "bills = (\n    # not for_workshop: a good reason\n    Bill.objects.all()\n)",
        "# not for_workshop: a good reason\nBill._base_manager.all()",
        "# not for_branch: owners see every branch\nVisit.objects.for_workshop(w)",
    ],
)
def test_a_line_that_says_why_passes(source):
    assert planted_problems(source) == []


@pytest.mark.parametrize(
    "source",
    [
        # The wrong word, no reason at all, a reason too far above, and another
        # statement's reason.
        "# not for_branch: the wrong word\nBill.objects.all()",
        "# not for_workshop:\nBill.objects.all()",
        "# not for_workshop: a good reason\nx = 1\nBill.objects.all()",
        "# not for_workshop: this query only\nBill.objects.all()\nBill.objects.all()",
        "Bill.objects.all()  # not for_workshop: this query only\nBill.objects.all()",
    ],
)
def test_a_line_that_does_not_really_say_why_is_caught(source):
    assert planted_problems(source)


# Forms: a link field Django makes by itself lists every workshop's records.


def form_classes():
    """Every form in the forms.py of our apps."""
    found = []
    for config in apps.get_app_configs():
        if config.name.startswith("apps.") and module_has_submodule(config.module, "forms"):
            module = import_module(f"{config.name}.forms")
            found += [
                value
                for value in vars(module).values()
                if isinstance(value, type)
                and issubclass(value, forms.BaseForm)
                and value.__module__ == module.__name__
            ]
    return found


def choices_that_start_full(form_class):
    """Each link field to a workshop record that does not start empty."""
    return [
        name
        for name, field in form_class.base_fields.items()
        if isinstance(field, forms.ModelChoiceField)
        and issubclass(field.queryset.model, WorkshopModel)
        and not field.queryset.query.is_empty()
    ]


def test_every_link_field_on_a_form_starts_empty():
    found_forms = form_classes()
    # A floor, so a search that found nothing cannot pass for being clean.
    assert found_forms

    found = {form: names for form in found_forms if (names := choices_that_start_full(form))}

    assert found == {}, "Use queryset=Model.objects.none(), and fill it in __init__."


@isolate_apps("apps.workshops")
def test_a_link_field_django_makes_by_itself_is_caught():
    class Planted(WorkshopModel):
        branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="+")

        class Meta(WorkshopModel.Meta):
            app_label = "workshops"

    class PlantedForm(forms.ModelForm):
        class Meta:
            model = Planted
            fields = ["branch"]

    assert choices_that_start_full(PlantedForm) == ["branch"]


def test_a_link_field_with_every_row_is_caught_and_an_empty_one_passes():
    class PlantedForm(forms.Form):
        full = forms.ModelChoiceField(queryset=Branch.objects.all())
        empty = forms.ModelChoiceField(queryset=Branch.objects.none())
        many = forms.ModelMultipleChoiceField(queryset=Branch.objects.all())

    assert choices_that_start_full(PlantedForm) == ["full", "many"]

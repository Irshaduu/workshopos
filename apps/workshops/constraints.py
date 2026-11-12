"""A link from one workshop record to another stays inside its workshop (ADR-0023), and a
link that must stay inside its branch, like a bill's to its job card, stays there too
(ADR-0032)."""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.utils import DEFAULT_DB_ALIAS
from django.utils.translation import gettext_lazy as _


class SameWorkshop(models.BaseConstraint):
    """A two-column foreign key: this record's (workshop, link) to the target's (workshop, id).

    So PostgreSQL refuses a job card of workshop A that points at a car of
    workshop B. Django cannot write one from models.py: its ForeignObject makes
    no database constraint (ADR-0023). The target's unique (workshop, id) pair
    comes from WorkshopModel.

    PostgreSQL checks it at the end of the transaction, like Django's own foreign
    keys. full_clean() checks first and says it in plain words; a form that leaves
    out the workshop never reaches this check, so its choices come from
    for_workshop(). An empty link passes: PostgreSQL skips a key with an empty side.
    """

    default_violation_error_message = _("This belongs to another workshop.")
    #: The column the two records share.
    shared = "workshop"

    def __init__(self, link, *, name):
        self.link = link
        super().__init__(name=name)

    def constraint_sql(self, model, schema_editor):
        quote = schema_editor.quote_name

        def shared_and(field):
            return (
                f"{quote(field.model._meta.get_field(self.shared).column)}, {quote(field.column)}"
            )

        link = model._meta.get_field(self.link)
        target = link.related_model
        return (
            f"CONSTRAINT {quote(self.name)} FOREIGN KEY ({shared_and(link)}) "
            f"REFERENCES {quote(target._meta.db_table)} ({shared_and(target._meta.pk)}) "
            "DEFERRABLE INITIALLY DEFERRED"
        )

    def create_sql(self, model, schema_editor):
        table = schema_editor.quote_name(model._meta.db_table)
        return f"ALTER TABLE {table} ADD {self.constraint_sql(model, schema_editor)}"

    def remove_sql(self, model, schema_editor):
        table = schema_editor.quote_name(model._meta.db_table)
        return f"ALTER TABLE {table} DROP CONSTRAINT {schema_editor.quote_name(self.name)}"

    def validate(self, model, instance, exclude=None, using=DEFAULT_DB_ALIAS):
        if exclude and {self.shared, self.link} & set(exclude):
            return
        if getattr(instance, model._meta.get_field(self.link).attname) is None:
            return
        shared_id = f"{self.shared}_id"
        if getattr(getattr(instance, self.link), shared_id) != getattr(instance, shared_id):
            raise ValidationError({self.link: self.get_violation_error_message()})

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        kwargs["link"] = self.link
        return path, args, kwargs

    def __eq__(self, other):
        return type(other) is type(self) and self.deconstruct() == other.deconstruct()


class SameBranch(SameWorkshop):
    """A two-column foreign key: this record's (branch, link) to the target's (branch, id).

    For a record whose branch is one fact with its link's, like a bill and its job card, so
    the two can never disagree (ADR-0032). The target needs a unique (branch, id) pair of its
    own: BranchModel does not give one, because few links need it.
    """

    default_violation_error_message = _("This belongs to another branch.")
    shared = "branch"

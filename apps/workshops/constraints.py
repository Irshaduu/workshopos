"""A link from one workshop record to another stays inside its workshop (ADR-0023)."""

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

    def __init__(self, link, *, name):
        self.link = link
        super().__init__(name=name)

    def constraint_sql(self, model, schema_editor):
        quote = schema_editor.quote_name

        def workshop_and(field):
            return f"{quote(field.model._meta.get_field('workshop').column)}, {quote(field.column)}"

        link = model._meta.get_field(self.link)
        target = link.related_model
        return (
            f"CONSTRAINT {quote(self.name)} FOREIGN KEY ({workshop_and(link)}) "
            f"REFERENCES {quote(target._meta.db_table)} ({workshop_and(target._meta.pk)}) "
            "DEFERRABLE INITIALLY DEFERRED"
        )

    def create_sql(self, model, schema_editor):
        table = schema_editor.quote_name(model._meta.db_table)
        return f"ALTER TABLE {table} ADD {self.constraint_sql(model, schema_editor)}"

    def remove_sql(self, model, schema_editor):
        table = schema_editor.quote_name(model._meta.db_table)
        return f"ALTER TABLE {table} DROP CONSTRAINT {schema_editor.quote_name(self.name)}"

    def validate(self, model, instance, exclude=None, using=DEFAULT_DB_ALIAS):
        if exclude and {"workshop", self.link} & set(exclude):
            return
        if getattr(instance, model._meta.get_field(self.link).attname) is None:
            return
        if getattr(instance, self.link).workshop_id != instance.workshop_id:
            raise ValidationError({self.link: self.get_violation_error_message()})

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        kwargs["link"] = self.link
        return path, args, kwargs

    def __eq__(self, other):
        return isinstance(other, SameWorkshop) and self.deconstruct() == other.deconstruct()

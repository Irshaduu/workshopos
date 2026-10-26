"""Who signs in (ADR-0007)."""

from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class User(BaseModel, AbstractUser):
    """A person who signs in.

    Made before any other app's first migration, so it can grow later without
    rebuilding the database. What a person may do in a workshop comes from
    their membership (ADR-0007), added with the workshops.
    """

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

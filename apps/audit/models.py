"""Each workshop's own limits on money typed after the fact (docs/rules/change-history.md,
ADR-0024)."""

from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.workshops.models import WorkshopModel

#: How many days back Office may date money, when a workshop never chose its own: v1's
#: BACKDATE_DAYS, the owners' decision of 2026-09-22 (CHANGE-15).
BACK_DATE_DAYS = 3
#: The most a workshop may choose: a month, so a slip of a year is never a setting.
BACK_DATE_DAYS_MOST = 31


class AuditSettings(WorkshopModel):
    """A workshop's own limits (CHANGE-18). A workshop with no saved row uses the values
    above, and reading never writes one (ADR-0024). Only an owner changes one; until a
    settings screen exists, the developer does it for them."""

    back_date_days = models.PositiveSmallIntegerField(
        _("back-date limit"),
        default=BACK_DATE_DAYS,
        db_default=BACK_DATE_DAYS,
        validators=[MaxValueValidator(BACK_DATE_DAYS_MOST)],
        help_text=_("How many days back Office may date money."),
    )

    class Meta(WorkshopModel.Meta):
        verbose_name = _("change history settings")
        verbose_name_plural = _("change history settings")
        constraints = [
            *WorkshopModel.Meta.constraints,
            models.UniqueConstraint(fields=["workshop"], name="audit_auditsettings_one_each"),
            models.CheckConstraint(
                condition=Q(back_date_days__lte=BACK_DATE_DAYS_MOST),
                name="audit_auditsettings_back_date_days_most",
            ),
        ]

    def __str__(self):
        return str(self.workshop)

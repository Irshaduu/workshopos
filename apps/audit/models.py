"""Money after it was recorded (docs/rules/change-history.md): each workshop's own limits on
it (ADR-0024), and the change history, which keeps every change to it for good (ADR-0032)."""

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.workshops.models import BranchModel, BranchQuerySet, WorkshopModel

#: How many days back Office may date money, when a workshop never chose its own: v1's
#: BACKDATE_DAYS, the owners' decision of 2026-09-22 (CHANGE-15).
BACK_DATE_DAYS = 3
#: The most a workshop may choose: a month, so a slip of a year is never a setting.
BACK_DATE_DAYS_MOST = 31
#: How many hours after money was recorded Office may still change it, when a workshop never
#: chose its own: v1's OFFICE_WINDOW_HOURS, the owners' decision of 2026-09-22 (CHANGE-9).
EDIT_WINDOW_HOURS = 24
#: The least and the most a workshop may choose: an hour, and a week, which Paid bills
#: shows Office whole, so Office always finds a bill it may still change (SETTLE-53).
EDIT_WINDOW_HOURS_LEAST = 1
EDIT_WINDOW_HOURS_MOST = 168


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
    edit_window_hours = models.PositiveSmallIntegerField(
        _("edit window"),
        default=EDIT_WINDOW_HOURS,
        db_default=EDIT_WINDOW_HOURS,
        validators=[
            MinValueValidator(EDIT_WINDOW_HOURS_LEAST),
            MaxValueValidator(EDIT_WINDOW_HOURS_MOST),
        ],
        help_text=_("How many hours after money was recorded Office may still change it."),
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
            models.CheckConstraint(
                condition=Q(
                    edit_window_hours__gte=EDIT_WINDOW_HOURS_LEAST,
                    edit_window_hours__lte=EDIT_WINDOW_HOURS_MOST,
                ),
                name="audit_auditsettings_edit_window_hours_range",
            ),
        ]

    def __str__(self):
        return str(self.workshop)


class ChangedRecord(models.TextChoices):
    """What kind of money record a change is about. Each later money record adds its own
    with its module (CHANGE-8)."""

    BILL = "bill", _("Bill")


class ChangeQuerySet(BranchQuerySet):
    """A change is never changed or removed, not even many at once (CHANGE-6)."""

    def update(self, **kwargs):
        raise TypeError("A change is kept for good, so it is never changed (CHANGE-6).")

    def delete(self):
        raise TypeError("A change is kept for good, so it is never removed (CHANGE-6).")


class Change(BranchModel):
    """One change to money after it was recorded, kept for good: what it was about, each
    figure that moved before and after, who, when and why (CHANGE-1 to CHANGE-6).

    It keeps its record's key with no link to it, and names it in words frozen when it was
    kept, so it outlives the record (CHANGE-2). It belongs to its record's branch, like the
    bill it is about, so every branch rule guards it; a change about a workshop-wide record,
    like a setting (CHANGE-18), decides its branch when that is built. Its figures are frozen
    text, never money columns: an amount with its paise, a day as a date (CHANGE-4). Only
    keep_change() makes one, in the same transaction as the change itself (CHANGE-3), under
    the key its change box was opened with; nothing changes or removes one, and it is never
    in the admin.
    """

    what = models.CharField(_("what"), max_length=20, choices=ChangedRecord)
    #: The changed record's own key. No link to it, deliberately (CHANGE-2).
    record_key = models.UUIDField(_("record key"))
    #: The record in words, as it was when the change was kept, like "INV-26-27-0045,
    #: KL07AB1234" (CHANGE-2).
    label = models.CharField(_("record"), max_length=255)
    #: Each figure that moved: its name, its kind (money or date), and its value before and
    #: after, as saved (CHANGE-4).
    figures = models.JSONField(_("figures"), encoder=DjangoJSONEncoder)
    reason = models.CharField(_("reason"), max_length=255)
    by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        editable=False,
        verbose_name=_("by"),
    )
    at = models.DateTimeField(_("at"), default=timezone.now, editable=False)

    objects = ChangeQuerySet.as_manager()

    class Meta(BranchModel.Meta):
        verbose_name = _("change")
        verbose_name_plural = _("changes")
        constraints = [
            *BranchModel.Meta.constraints,
            models.CheckConstraint(
                condition=Q(what__in=ChangedRecord.values), name="audit_change_what_known"
            ),
            # Every change says why (CHANGE-5), and keeps at least one figure that moved: a
            # save that moved nothing keeps nothing (CHANGE-4).
            models.CheckConstraint(condition=~Q(reason=""), name="audit_change_reason_given"),
            models.CheckConstraint(condition=~Q(figures=[]), name="audit_change_figures_given"),
        ]

    def __str__(self):
        return self.label

    def save(self, *args, **kwargs):
        # Only a first insert: a saved change, or an update forced onto a kept key, is refused.
        if not self._state.adding or kwargs.get("force_update") or kwargs.get("update_fields"):
            raise TypeError("A change is kept for good, so it is never changed (CHANGE-6).")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("A change is kept for good, so it is never removed (CHANGE-6).")

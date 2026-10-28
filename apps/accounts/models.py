"""Who signs in, and their place in a workshop (ADR-0007)."""

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel
from apps.workshops.models import WorkshopModel


class User(BaseModel, AbstractUser):
    """A person who signs in.

    Made before any other app's first migration, so it can grow later without
    rebuilding the database. What a person may do in a workshop comes from
    their membership (ADR-0007).
    """

    # The lockout for a password (SIGN-29 to SIGN-34): the wrong passwords in
    # a row, and when the last one came. Kept on the account, never per
    # internet address: the whole workshop uses one connection, so one
    # person's wrong tries never lock anyone else (SIGN-31). PostgreSQL gives
    # a row added outside Django its 0 too.
    wrong_passwords = models.PositiveSmallIntegerField(
        _("wrong passwords in a row"), default=0, db_default=0
    )
    last_wrong_password_at = models.DateTimeField(
        _("last wrong password at"), null=True, blank=True
    )

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        # Capitals never make a second account: AB.Floor is ab.floor, and an
        # email in any capitals is the same email (SIGN-9). Office and Floor
        # have no email, so an empty one is left out.
        constraints = [
            models.UniqueConstraint(
                Lower("username"),
                name="accounts_user_username_once",
                violation_error_message=_("Another account already has this username."),
            ),
            models.UniqueConstraint(
                Lower("email"),
                condition=~models.Q(email=""),
                name="accounts_user_email_once",
                violation_error_message=_("Another account already has this email."),
            ),
        ]

    @property
    def is_platform_staff(self):
        """Runs the system: staff and superusers. Never a workshop member (ADR-0007)."""
        return self.is_staff or self.is_superuser


class Role(models.TextChoices):
    OWNER = "owner", _("Owner")
    OFFICE = "office", _("Office")
    FLOOR = "floor", _("Floor")


class Membership(WorkshopModel):
    """An account's place in a workshop, with its role (ADR-0007).

    One per account for now: an account belongs to one workshop. A shared
    login, like one Floor login on the workshop tablet, is still one account.
    Several workshops per account come with a workshop picker (SaaS).
    """

    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="+", verbose_name=_("user")
    )
    role = models.CharField(_("role"), max_length=20, choices=Role)

    class Meta(WorkshopModel.Meta):
        verbose_name = _("membership")
        verbose_name_plural = _("memberships")
        constraints = [
            *WorkshopModel.Meta.constraints,
            models.UniqueConstraint(
                fields=["user"],
                name="accounts_membership_one_per_account",
                violation_error_message=_("This account already belongs to a workshop."),
            ),
            models.CheckConstraint(
                condition=models.Q(role__in=Role.values),
                name="accounts_membership_role_known",
            ),
        ]

    def __str__(self):
        return f"{self.user} ({self.get_role_display()})"

    def clean(self):
        super().clean()
        if self.user_id and self.user.is_platform_staff:
            raise ValidationError(
                {"user": _("Staff and superusers run the system; they are never members.")}
            )


class SignInCode(BaseModel):
    """A 6-digit code emailed to an owner, who types it to sign in (ADR-0025).

    Only a hash of the code is kept, made with the server's secret key
    (SIGN-24). A code belongs to an account, not to a workshop. Rows stay
    after use, because the limits are counted from them (SIGN-20); a
    scheduled clean-up deletes old ones (the background jobs ADR, Phase 6).
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="+", verbose_name=_("account")
    )
    code_hash = models.CharField(_("code hash"), max_length=64)
    created_at = models.DateTimeField(_("made at"))
    # Ten minutes after it was made, or earlier: a new code, the right code
    # or the fifth wrong try ends it at once.
    ends_at = models.DateTimeField(_("ends at"))
    wrong_tries = models.PositiveSmallIntegerField(_("wrong tries"), default=0, db_default=0)
    used_at = models.DateTimeField(_("used at"), null=True, blank=True)

    class Meta:
        verbose_name = _("sign-in code")
        verbose_name_plural = _("sign-in codes")
        # The limits count an account's codes of the last hour (SIGN-20).
        indexes = [models.Index(fields=["user", "-created_at"], name="accounts_code_user_recent")]

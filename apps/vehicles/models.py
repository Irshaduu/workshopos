"""Cars and customers, each one record in a workshop, shared by its branches (ADR-0030).

The rules: docs/rules/job-card.md. What is true of the car lives here. What is true of a
visit lives on its job card.
"""

import re

from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from apps.core.text import tidy_name, tidy_spaces
from apps.workshops.constraints import SameWorkshop
from apps.workshops.models import WorkshopModel

PLATE_MAX_LENGTH = 20
CHASSIS_CODE_MAX_LENGTH = 20
VIN_LENGTH = 17
#: Other's own colour is what the browser's colour box sends: #rrggbb.
OWN_COLOUR = re.compile(r"#[0-9a-f]{6}")

PLATE_FORM = _("A plate is letters and digits, up to 20.")
VIN_FORM = _("A VIN is 17 letters and digits, with no I, O or Q.")
CONTACT_NUMBER_FORM = _("Type a phone number, in digits.")


def tidy_plate(typed):
    """One spelling for one plate, so "kl-10 aa 1000" is KL10AA1000 (JOB-16)."""
    return re.sub(r"[\s\-./]+", "", typed).upper()


def plate_problem(plate):
    """What is wrong with a tidied plate, in words; or nothing. Its shape is never judged
    further, because temporary, new and other countries' plates are real (JOB-16)."""
    if not re.fullmatch(rf"[A-Z0-9]{{1,{PLATE_MAX_LENGTH}}}", plate):
        return PLATE_FORM
    return ""


def tidy_chassis_code(typed):
    """Capitals, with spaces gone, and never refused for its shape: 991.2 is real (JOB-18)."""
    return "".join(typed.split()).upper()


def tidy_vin(typed):
    """A VIN may be typed in groups, so spaces and dashes go (JOB-19)."""
    return re.sub(r"[\s\-]+", "", typed).upper()


def vin_problem(vin):
    """What is wrong with a tidied VIN, in words; or nothing (JOB-19).

    It is refused with its rule, never corrected. There is no check-digit test, because
    European makers fill that place freely.
    """
    if not vin:
        return ""
    if not re.fullmatch(r"[A-Z0-9]+", vin):
        return _("A VIN is letters and digits only.")
    if len(vin) != VIN_LENGTH:
        return _("A VIN has 17 characters, and this one has %(count)d.") % {"count": len(vin)}
    if set(vin) & set("IOQ"):
        return _("A VIN never uses the letters I, O or Q. Check for a 1 or a 0.")
    return ""


def tidy_contact_number(typed):
    """One spelling for one number (JOB-30): +91 or 91 before a 10-digit mobile goes. A leading
    0 stays, because 080 40000001 is a landline and could not be told from a mobile."""
    plain = re.sub(r"[\s\-.()]+", "", typed)
    mobile = re.fullmatch(r"(?:\+?91)?([6-9][0-9]{9})", plain)
    return mobile[1] if mobile else plain


def contact_number_problem(number):
    """What is wrong with a tidied number, in words; or nothing. A landline and a Gulf
    number are fine (JOB-30)."""
    if number and not re.fullmatch(r"\+?[0-9]{7,15}", number):
        return CONTACT_NUMBER_FORM
    return ""


class CarBrand(WorkshopModel):
    """A maker, on the workshop's list of brands. A new word joins by itself (JOB-17)."""

    name = models.CharField(_("car brand"), max_length=100)

    class Meta(WorkshopModel.Meta):
        verbose_name = _("car brand")
        verbose_name_plural = _("car brands")
        constraints = [
            *WorkshopModel.Meta.constraints,
            models.UniqueConstraint(
                Lower("name"),
                "workshop",
                name="vehicles_carbrand_name_once",
                violation_error_message=_("This brand is already on the list."),
            ),
            models.CheckConstraint(
                condition=Q(name__regex=r"\S"),
                name="vehicles_carbrand_name_given",
                violation_error_message=_("Type a brand."),
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        self.name = tidy_name(self.name)


class CarModel(WorkshopModel):
    """A model of one brand, on that brand's list. A new word joins by itself (JOB-17)."""

    brand = models.ForeignKey(
        CarBrand, on_delete=models.PROTECT, related_name="car_models", verbose_name=_("car brand")
    )
    name = models.CharField(_("car model"), max_length=100)

    class Meta(WorkshopModel.Meta):
        verbose_name = _("car model")
        verbose_name_plural = _("car models")
        constraints = [
            *WorkshopModel.Meta.constraints,
            SameWorkshop("brand", name="vehicles_carmodel_brand_same_workshop"),
            models.UniqueConstraint(
                Lower("name"),
                "brand",
                name="vehicles_carmodel_name_once",
                violation_error_message=_("This model is already on the list."),
            ),
            models.CheckConstraint(
                condition=Q(name__regex=r"\S"),
                name="vehicles_carmodel_name_given",
                violation_error_message=_("Type a model."),
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        # Only its spaces: i20 and CR-V must stay as they are (JOB-17).
        self.name = tidy_spaces(self.name)


class Colour(models.TextChoices):
    """v1's colours, in its order. Each has its paint class in components.css (JOB-21)."""

    BLACK = "black", _("Black")
    WHITE = "white", _("White")
    SILVER = "silver", _("Silver")
    GREY = "grey", _("Grey")
    RED = "red", _("Red")
    LIGHT_BLUE = "light-blue", _("Light Blue")
    BLUE = "blue", _("Blue")
    DARK_BLUE = "dark-blue", _("Dark Blue")
    YELLOW = "yellow", _("Yellow")
    LIGHT_GREEN = "light-green", _("Light Green")
    GREEN = "green", _("Green")
    DARK_GREEN = "dark-green", _("Dark Green")
    BROWN = "brown", _("Brown")
    DARK_BROWN = "dark-brown", _("Dark Brown")
    OTHER = "other", _("Other")


class Car(WorkshopModel):
    """One car in a workshop, with its whole history (JOB-11).

    It keeps its plate today. Each job card keeps the plate it came with, so a new plate
    changes the car from that day on (JOB-13). It can be left with no plate for a while,
    when the car in front of you takes it, and its VIN finds it again (KNOWN-3). It has no
    owner: a car's customer is the one on its newest job card that has one, so a sale is
    only the next card (JOB-29).
    """

    plate = models.CharField(_("plate number"), max_length=PLATE_MAX_LENGTH, blank=True)
    car_model = models.ForeignKey(
        CarModel, on_delete=models.PROTECT, related_name="cars", verbose_name=_("car model")
    )
    chassis_code = models.CharField(
        _("chassis code"), max_length=CHASSIS_CODE_MAX_LENGTH, blank=True
    )
    vin = models.CharField(_("VIN"), max_length=VIN_LENGTH, blank=True)
    colour = models.CharField(_("colour"), max_length=20, choices=Colour, blank=True)
    colour_other = models.CharField(_("other colour"), max_length=7, blank=True)

    class Meta(WorkshopModel.Meta):
        verbose_name = _("car")
        verbose_name_plural = _("cars")
        constraints = [
            *WorkshopModel.Meta.constraints,
            SameWorkshop("car_model", name="vehicles_car_car_model_same_workshop"),
            models.UniqueConstraint(
                fields=["workshop", "plate"],
                condition=~Q(plate=""),
                name="vehicles_car_plate_once",
                violation_error_message=_("This plate is on another car."),
            ),
            models.UniqueConstraint(
                fields=["workshop", "vin"],
                condition=~Q(vin=""),
                name="vehicles_car_vin_once",
                violation_error_message=_("This VIN is on another car."),
            ),
            # Empty only when another car took the plate (KNOWN-3).
            models.CheckConstraint(
                condition=Q(plate__regex=r"^[A-Z0-9]*$"),
                name="vehicles_car_plate_form",
                violation_error_message=PLATE_FORM,
            ),
            models.CheckConstraint(
                condition=Q(vin="") | Q(vin__regex=r"^[A-HJ-NPR-Z0-9]{17}$"),
                name="vehicles_car_vin_form",
                violation_error_message=VIN_FORM,
            ),
            models.CheckConstraint(
                condition=Q(chassis_code__regex=r"^[^\sa-z]*$"),
                name="vehicles_car_chassis_code_form",
            ),
            models.CheckConstraint(
                condition=Q(colour="") | Q(colour__in=Colour.values),
                name="vehicles_car_colour_known",
            ),
            models.CheckConstraint(
                condition=(
                    Q(colour=Colour.OTHER, colour_other__regex=r"^#[0-9a-f]{6}$")
                    | (~Q(colour=Colour.OTHER) & Q(colour_other=""))
                ),
                name="vehicles_car_colour_other_only_with_other",
            ),
        ]

    def __str__(self):
        return self.plate or self.name

    def clean(self):
        # Here, so every service that checks a car before saving tidies it.
        self.plate = tidy_plate(self.plate)
        self.chassis_code = tidy_chassis_code(self.chassis_code)
        self.vin = tidy_vin(self.vin)

    @property
    def name(self):
        """What people call it, like BMW 520d."""
        return f"{self.car_model.brand.name} {self.car_model.name}"

    @property
    def paint(self):
        """Its paint class's last word. No colour has its own, never grey (JOB-21)."""
        return self.colour or "unset"


class Customer(WorkshopModel):
    """A name and a number together, as one record in a workshop (JOB-27).

    The same two boxes find the same record. Another name with the same number is another
    record: one phone can serve a family or a company, and a card's name never changes
    because of another person's visit. Nothing merges by itself.
    """

    name = models.CharField(_("customer name"), max_length=150, blank=True)
    contact_number = models.CharField(_("contact number"), max_length=16, blank=True)

    class Meta(WorkshopModel.Meta):
        verbose_name = _("customer")
        verbose_name_plural = _("customers")
        constraints = [
            *WorkshopModel.Meta.constraints,
            models.UniqueConstraint(
                Lower("name"),
                "contact_number",
                "workshop",
                name="vehicles_customer_once",
                violation_error_message=_("This customer is already saved."),
            ),
            models.CheckConstraint(
                condition=Q(name__regex=r"\S") | Q(contact_number__regex=r"\S"),
                name="vehicles_customer_name_or_number",
                violation_error_message=_("A customer needs a name or a number."),
            ),
            models.CheckConstraint(
                condition=Q(contact_number="") | Q(contact_number__regex=r"^\+?[0-9]{7,15}$"),
                name="vehicles_customer_contact_number_form",
                violation_error_message=CONTACT_NUMBER_FORM,
            ),
        ]

    def __str__(self):
        return self.name or self.contact_number

    def clean(self):
        self.name = tidy_name(self.name)
        self.contact_number = tidy_contact_number(self.contact_number)

"""Models module."""
from enum import Enum, auto

from homeassistant.backports.enum import StrEnum

from custom_components.bodymiscale.const import (
    ATTR_AGE,
    ATTR_BMI,
    ATTR_BMR,
    ATTR_BODY,
    ATTR_BONES,
    ATTR_LBM,
    ATTR_METABOLIC,
    ATTR_MUSCLE,
    ATTR_VISCERAL,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_WEIGHT,
)


class Gender(str, Enum):
    """Gender enum."""

    MALE = "male"
    FEMALE = "female"


class Metric(StrEnum):
    """Metric enum."""

    STATUS = "status"
    AGE = ATTR_AGE
    WEIGHT = CONF_SENSOR_WEIGHT
    IMPEDANCE = CONF_SENSOR_IMPEDANCE
    BMI = ATTR_BMI
    BMR = ATTR_BMR
    VISCERAL_FAT = ATTR_VISCERAL
    LBM = ATTR_LBM
    FAT_PERCENTAGE = "fat_percentage"
    WATER_PERCENTAGE = "water_percentage"
    BONE_MASS = ATTR_BONES
    MUSCLE_MASS = ATTR_MUSCLE
    METABOLIC_AGE = ATTR_METABOLIC
    PROTEIN_PERCENTAGE = "protein_percentage"
    FAT_MASS_2_IDEAL_WEIGHT = "fat_mass_2_ideal_weight"
    BODY_TYPE = ATTR_BODY

"""Models module."""

from enum import Enum

from .const import (
    ATTR_AGE,
    ATTR_BMI,
    ATTR_BMR,
    ATTR_BODY,
    ATTR_BODY_SCORE,
    ATTR_BONES,
    ATTR_FAT,
    ATTR_LBM,
    ATTR_METABOLIC,
    ATTR_MUSCLE,
    ATTR_PROTEIN,
    ATTR_VISCERAL,
    ATTR_WATER,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_WEIGHT,
)


class Gender(str, Enum):
    """Gender enum."""

    MALE = "male"
    FEMALE = "female"


class Metric(str, Enum):
    """Metric enum."""

    STATUS = "status"
    AGE = ATTR_AGE
    WEIGHT = CONF_SENSOR_WEIGHT
    IMPEDANCE = CONF_SENSOR_IMPEDANCE
    BMI = ATTR_BMI
    BMR = ATTR_BMR
    VISCERAL_FAT = ATTR_VISCERAL
    LBM = ATTR_LBM
    FAT_PERCENTAGE = ATTR_FAT
    WATER_PERCENTAGE = ATTR_WATER
    BONE_MASS = ATTR_BONES
    MUSCLE_MASS = ATTR_MUSCLE
    METABOLIC_AGE = ATTR_METABOLIC
    PROTEIN_PERCENTAGE = ATTR_PROTEIN
    FAT_MASS_2_IDEAL_WEIGHT = "fat_mass_2_ideal_weight"
    BODY_TYPE = ATTR_BODY
    BODY_SCORE = ATTR_BODY_SCORE

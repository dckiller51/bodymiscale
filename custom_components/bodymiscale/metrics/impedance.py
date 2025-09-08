"""Metrics module, which require impedance and other metrics."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from homeassistant.helpers.typing import StateType

from ..const import CONF_GENDER, CONF_HEIGHT, CONF_SCALE
from ..models import Gender, Metric
from ..util import check_value_constraints, to_float


def get_lbm(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Get LBM coefficient (with impedance)."""
    height = to_float(config.get(CONF_HEIGHT))
    weight = to_float(metrics.get(Metric.WEIGHT))
    impedance = to_float(metrics.get(Metric.IMPEDANCE))
    age = to_float(metrics.get(Metric.AGE))

    lbm = 0.0

    if (
        height is not None
        and weight is not None
        and impedance is not None
        and age is not None
    ):
        lbm = (height * 9.058 / 100) * (height / 100)
        lbm += weight * 0.32 + 12.226
        lbm -= impedance * 0.0068
        lbm -= age * 0.0542

    return float(lbm)


def get_fat_percentage(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate fat percentage."""
    weight = to_float(metrics.get(Metric.WEIGHT))
    lbm = to_float(metrics.get(Metric.LBM))
    age = to_float(metrics.get(Metric.AGE))
    height = to_float(config.get(CONF_HEIGHT))
    gender = config.get(CONF_GENDER)

    # Return 0 if any required metric is missing
    if weight is None or lbm is None or age is None or height is None or gender is None:
        return 0.0

    coefficient = 1.0

    if gender == Gender.FEMALE:
        const = 9.25 if age <= 49 else 7.25
        if weight > 60:
            coefficient = 0.96
        elif weight < 50:
            coefficient = 1.02
        if height > 160 and (weight < 50 or weight > 60):
            coefficient *= 1.03
    else:
        const = 0.8
        if weight < 61:
            coefficient = 0.98

    fat_percentage = (1.0 - ((lbm - const) * coefficient / weight)) * 100

    # Cap fat_percentage at 75
    if fat_percentage > 63:
        fat_percentage = 75

    return check_value_constraints(fat_percentage, 5, 75)


def get_water_percentage(
    _: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Get water percentage."""
    fat_percentage = to_float(metrics.get(Metric.FAT_PERCENTAGE)) or 0.0
    water_percentage = (100 - fat_percentage) * 0.7
    coefficient = 1.02 if water_percentage <= 50 else 0.98

    water_percentage *= coefficient
    if water_percentage >= 65:
        water_percentage = 75

    return check_value_constraints(water_percentage, 35, 75)


def get_bone_mass(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Get bone mass."""
    lbm = to_float(metrics.get(Metric.LBM)) or 0.0
    base = 0.245691014 if config[CONF_GENDER] == Gender.FEMALE else 0.18016894

    bone_mass = (base - (lbm * 0.05158)) * -1

    if bone_mass > 2.2:
        bone_mass += 0.1
    else:
        bone_mass -= 0.1

    if config[CONF_GENDER] == Gender.FEMALE and bone_mass > 5.1:
        bone_mass = 8
    elif config[CONF_GENDER] == Gender.MALE and bone_mass > 5.2:
        bone_mass = 8

    return check_value_constraints(bone_mass, 0.5, 8)


def get_muscle_mass(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Get muscle mass."""
    weight = to_float(metrics.get(Metric.WEIGHT)) or 0.0
    fat_percentage = to_float(metrics.get(Metric.FAT_PERCENTAGE)) or 0.0
    bone_mass = to_float(metrics.get(Metric.BONE_MASS)) or 0.0

    muscle_mass = weight - ((fat_percentage * 0.01) * weight) - bone_mass

    if config[CONF_GENDER] == Gender.FEMALE and muscle_mass >= 84:
        muscle_mass = 120
    elif config[CONF_GENDER] == Gender.MALE and muscle_mass >= 93.5:
        muscle_mass = 120

    return check_value_constraints(muscle_mass, 10, 120)


def get_metabolic_age(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Get metabolic age."""
    height = to_float(config.get(CONF_HEIGHT))
    weight = to_float(metrics.get(Metric.WEIGHT))
    age = to_float(metrics.get(Metric.AGE))
    impedance = to_float(metrics.get(Metric.IMPEDANCE))

    metabolic_age = 15.0

    if (
        height is not None
        and weight is not None
        and age is not None
        and impedance is not None
    ):
        if config[CONF_GENDER] == Gender.FEMALE:
            metabolic_age = (
                (height * -1.1165)
                + (weight * 1.5784)
                + (age * 0.4615)
                + (impedance * 0.0415)
                + 83.2548
            )
        else:
            metabolic_age = (
                (height * -0.7471)
                + (weight * 0.9161)
                + (age * 0.4184)
                + (impedance * 0.0517)
                + 54.2267
            )

    return check_value_constraints(metabolic_age, 15, 80)


def get_protein_percentage(
    _: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Get protein percentage."""
    muscle_mass = to_float(metrics.get(Metric.MUSCLE_MASS)) or 0.0
    weight = to_float(metrics.get(Metric.WEIGHT)) or 0.0
    water_percentage = to_float(metrics.get(Metric.WATER_PERCENTAGE)) or 0.0

    if weight == 0:
        return 0.0

    protein_percentage = (muscle_mass / weight) * 100 - water_percentage
    return check_value_constraints(protein_percentage, 5, 32)


def get_fat_mass_to_ideal_weight(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Get missing mass to ideal weight."""
    weight = to_float(metrics.get(Metric.WEIGHT)) or 0.0
    age = to_float(metrics.get(Metric.AGE)) or 0.0
    fat_percentage = to_float(metrics.get(Metric.FAT_PERCENTAGE)) or 0.0

    target_fat_pct = config[CONF_SCALE].get_fat_percentage(age)[2]
    fat_mass_to_ideal = weight * (target_fat_pct / 100) - weight * (
        fat_percentage / 100
    )

    return float(fat_mass_to_ideal)


def get_body_type(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> str:
    """Get body type."""
    fat = to_float(metrics.get(Metric.FAT_PERCENTAGE)) or 0.0
    muscle = to_float(metrics.get(Metric.MUSCLE_MASS)) or 0.0
    age = to_float(metrics.get(Metric.AGE)) or 0.0
    scale = config[CONF_SCALE]

    if fat > scale.get_fat_percentage(age)[2]:
        factor = 0
    elif fat < scale.get_fat_percentage(age)[1]:
        factor = 2
    else:
        factor = 1

    body_type = 1 + (factor * 3)
    if muscle > scale.muscle_mass[1]:
        body_type = 2 + (factor * 3)
    elif muscle < scale.muscle_mass[0]:
        body_type = factor * 3

    return [
        "obese",
        "overweight",
        "thick_set",
        "lack_exercise",
        "balanced",
        "balanced_muscular",
        "skinny",
        "balanced_skinny",
        "skinny_muscular",
    ][body_type]

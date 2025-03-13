"""Metrics module, which require impedance."""

from collections.abc import Mapping
from typing import Any

from homeassistant.helpers.typing import StateType

from ..const import CONF_GENDER, CONF_HEIGHT, CONF_SCALE
from ..models import Gender, Metric
from ..util import check_value_constraints


def get_lbm(config: Mapping[str, Any], metrics: Mapping[Metric, StateType]) -> float:
    """Get LBM coefficient (with impedance)."""
    height = config[CONF_HEIGHT]
    lbm = (height * 9.058 / 100) * (height / 100)
    lbm += metrics[Metric.WEIGHT] * 0.32 + 12.226
    lbm -= metrics[Metric.IMPEDANCE] * 0.0068
    lbm -= metrics[Metric.AGE] * 0.0542

    return float(lbm)


def get_fat_percentage(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType]
) -> float:
    """Get fat percentage."""
    # Set a const to remove from LBM
    weight = metrics[Metric.WEIGHT]
    coefficient = 1.0
    if config[CONF_GENDER] == Gender.FEMALE:
        const = 9.25 if metrics[Metric.AGE] <= 49 else 7.25
        if weight > 60:
            coefficient = 0.96
        elif weight < 50:
            coefficient = 1.02

        if config[CONF_HEIGHT] > 160 and (weight < 50 or weight > 60):
            coefficient *= 1.03
    else:
        const = 0.8
        if weight < 61:
            coefficient = 0.98

    fat_percentage = (
        1.0 - (((metrics[Metric.LBM] - const) * coefficient) / weight)
    ) * 100

    # Capping body fat percentage
    if fat_percentage > 63:
        fat_percentage = 75
    return check_value_constraints(fat_percentage, 5, 75)


def get_water_percentage(
    _: Mapping[str, Any], metrics: Mapping[Metric, StateType]
) -> float:
    """Get water percentage."""
    water_percentage = (100 - metrics[Metric.FAT_PERCENTAGE]) * 0.7
    coefficient = 1.02 if water_percentage <= 50 else 0.98

    # Capping water percentage
    if water_percentage * coefficient >= 65:
        water_percentage = 75
    return check_value_constraints(water_percentage * coefficient, 35, 75)


def get_bone_mass(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType]
) -> float:
    """Get bone mass."""
    if config[CONF_GENDER] == Gender.FEMALE:
        base = 0.245691014
    else:
        base = 0.18016894

    bone_mass = (base - (metrics[Metric.LBM] * 0.05158)) * -1

    if bone_mass > 2.2:
        bone_mass += 0.1
    else:
        bone_mass -= 0.1

    # Capping bone mass
    if config[CONF_GENDER] == Gender.FEMALE and bone_mass > 5.1:
        bone_mass = 8
    elif config[CONF_GENDER] == Gender.MALE and bone_mass > 5.2:
        bone_mass = 8

    return check_value_constraints(bone_mass, 0.5, 8)


def get_muscle_mass(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType]
) -> float:
    """Get muscle mass."""
    weight = metrics[Metric.WEIGHT]
    muscle_mass = (
        weight
        - ((metrics[Metric.FAT_PERCENTAGE] * 0.01) * weight)
        - metrics[Metric.BONE_MASS]
    )

    # Capping muscle mass
    if config[CONF_GENDER] == Gender.FEMALE and muscle_mass >= 84:
        muscle_mass = 120
    elif config[CONF_GENDER] == Gender.MALE and muscle_mass >= 93.5:
        muscle_mass = 120

    return check_value_constraints(muscle_mass, 10, 120)


def get_metabolic_age(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType]
) -> float:
    """Get metabolic age."""
    height = config[CONF_HEIGHT]
    weight = metrics[Metric.WEIGHT]
    age = metrics[Metric.AGE]
    impedance = metrics[Metric.IMPEDANCE]

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
    _: Mapping[str, Any], metrics: Mapping[Metric, StateType]
) -> float:
    """Get protetin percentage (warn: guessed formula)."""
    # Use original algorithm from mi fit (or legacy guess one)
    protein_percentage = (metrics[Metric.MUSCLE_MASS] / metrics[Metric.WEIGHT]) * 100
    protein_percentage -= metrics[Metric.WATER_PERCENTAGE]
    return check_value_constraints(protein_percentage, 5, 32)


def get_fat_mass_to_ideal_weight(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType]
) -> float:
    """Get missig mass to ideal weight."""
    weight = metrics[Metric.WEIGHT]
    return float(
        weight * (config[CONF_SCALE].get_fat_percentage(metrics[Metric.AGE])[2] / 100)
        - (weight * (metrics[Metric.FAT_PERCENTAGE] / 100))
    )


def get_body_type(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType]
) -> str:
    """Get body type (out of nine possible)."""
    fat = metrics[Metric.FAT_PERCENTAGE]
    muscle = metrics[Metric.MUSCLE_MASS]
    scale = config[CONF_SCALE]

    if fat > scale.get_fat_percentage(metrics[Metric.AGE])[2]:
        factor = 0
    elif fat < scale.get_fat_percentage(metrics[Metric.AGE])[1]:
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

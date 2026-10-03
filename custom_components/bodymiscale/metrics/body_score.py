"""Body score module."""

from collections import namedtuple
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from homeassistant.helpers.typing import StateType

from ..const import (
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_IMPEDANCE_MODE,
    CONF_SCALE,
    IMPEDANCE_MODE_DUAL,
)
from ..models import Gender, Metric
from ..util import check_value_constraints, to_float


def _get_malus(
    value: float,
    value1: float,
    value2: float,
    malus1: int | float,
    malus2: int | float,
) -> float:
    """Calculate malus based on value and predefined ranges."""
    if value1 == value2:
        return 0.0
    if value2 < value1:
        value1, value2, malus1, malus2 = value2, value1, malus2, malus1

    if value <= value1:
        return malus1
    if value >= value2:
        return malus2

    interpolated = (malus2 - malus1) / (value2 - value1) * (value - value1) + malus1
    return max(0.0, interpolated)


def _calculate_bmi_deduct_score(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate BMI deduct score."""
    bmi_very_low = 14.0
    bmi_low = 15.0
    bmi_normal = 18.5
    bmi_overweight = 28.0
    bmi_obese = 32.0

    if to_float(config.get(CONF_HEIGHT)) < 90:
        return 0.0

    bmi = to_float(metrics.get(Metric.BMI))
    age = int(to_float(metrics.get(Metric.AGE)))
    fat_percentage = to_float(metrics.get(Metric.FAT_PERCENTAGE))
    fat_scale = config[CONF_SCALE].get_fat_percentage(age)

    if bmi < bmi_low:
        return _get_malus(bmi, bmi_very_low, bmi_low, 30, 15)
    if bmi < bmi_normal:
        if fat_percentage < fat_scale[2] and age < 18:
            return 0.0
        return _get_malus(bmi, bmi_low, bmi_normal, 15, 5)
    if bmi < bmi_overweight:
        return 0.0
    if fat_percentage >= fat_scale[2]:
        return _get_malus(bmi, bmi_overweight, bmi_obese, 5, 10)

    return 0.0


def _calculate_body_fat_deduct_score(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate body fat deduct score."""
    fat_percentage = to_float(metrics.get(Metric.FAT_PERCENTAGE))
    age = int(to_float(metrics.get(Metric.AGE)))
    gender = config[CONF_GENDER]
    scale = config[CONF_SCALE].get_fat_percentage(age)

    best_fat_level = scale[2] - 3.0 if gender == Gender.MALE else scale[2] - 2.0

    if fat_percentage < scale[0]:
        return _get_malus(fat_percentage, 1.0, scale[0], 10, 3)
    if fat_percentage < best_fat_level:
        return 0.0
    if fat_percentage < scale[2]:
        return _get_malus(fat_percentage, best_fat_level, scale[2], 3, 9)

    return _get_malus(fat_percentage, scale[2], scale[3], 10, 20)


def _calculate_common_deduct_score(
    value: float, min_value: float, max_value: float
) -> float:
    """Calculate common deduct score (Universal logic)."""
    if value >= max_value:
        return 0.0

    penalty_max = 10.0

    return _get_malus(value, min_value, max_value, penalty_max, 5)


def _calculate_muscle_deduct_score(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate muscle mass deduct score with S400 adaptation."""
    scale = config[CONF_SCALE].muscle_mass
    is_s400 = config.get(CONF_IMPEDANCE_MODE) == IMPEDANCE_MODE_DUAL

    if is_s400:
        # In S400, we use the SMM (Skeletal Muscle Mass)
        muscle_mass = to_float(metrics.get(Metric.SKELETAL_MUSCLE_MASS))

        # Guard: if SMM calculation failed or is 0, we don't apply penalty
        if muscle_mass <= 0:
            return 0.0

        # We adjust the standard thresholds (Total Muscle Mass) to the SMM format
        # The 0.77 ratio is a physiological estimate of skeletal muscle vs total muscle.
        target_min = (scale[0] - 5.0) * 0.77
        target_max = scale[0] * 0.77
    else:
        # Classical modes: Total muscle mass
        muscle_mass = to_float(metrics.get(Metric.MUSCLE_MASS))
        if muscle_mass <= 0:
            return 0.0
        target_min = scale[0] - 5.0
        target_max = scale[0]

    return _calculate_common_deduct_score(muscle_mass, target_min, target_max)


def _calculate_water_deduct_score(
    config: Mapping[str, Any], water_percentage: float
) -> float:
    """Calculate water percentage deduct score."""
    water_percentage_normal = 55.0 if config[CONF_GENDER] == Gender.MALE else 45.0
    return _calculate_common_deduct_score(
        water_percentage,
        water_percentage_normal - 5.0,
        water_percentage_normal,
    )


def _calculate_bone_deduct_score(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate bone mass deduct score."""
    BoneMassEntry = namedtuple("BoneMassEntry", ["min_weight", "bone_mass"])

    if config[CONF_GENDER] == Gender.MALE:
        entries = [
            BoneMassEntry(75, 2.0),
            BoneMassEntry(60, 1.9),
            BoneMassEntry(0, 1.6),
        ]
    else:
        entries = [
            BoneMassEntry(60, 1.8),
            BoneMassEntry(45, 1.5),
            BoneMassEntry(0, 1.3),
        ]

    weight = to_float(metrics.get(Metric.WEIGHT))
    bone_mass = to_float(metrics.get(Metric.BONE_MASS))
    expected_bone_mass = entries[-1].bone_mass
    for entry in entries:
        if weight >= entry.min_weight:
            expected_bone_mass = entry.bone_mass
            break

    return _calculate_common_deduct_score(
        bone_mass, expected_bone_mass - 0.3, expected_bone_mass
    )


def _calculate_body_visceral_deduct_score(visceral_fat: float) -> float:
    """Calculate visceral fat deduct score."""
    max_data = 15.0
    min_data = 10.0

    if visceral_fat < min_data:
        return 0.0

    return _get_malus(visceral_fat, min_data, max_data, min_data, max_data)


def _calculate_basal_metabolism_deduct_score(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate basal metabolism deduct score."""
    gender = config[CONF_GENDER]
    age = int(to_float(metrics.get(Metric.AGE)))
    weight = to_float(metrics.get(Metric.WEIGHT))
    bmr = to_float(metrics.get(Metric.BMR))

    coefficients = {
        Gender.MALE: {30: 21.6, 50: 20.07, 100: 19.35},
        Gender.FEMALE: {30: 21.24, 50: 19.53, 100: 18.63},
    }

    normal_bmr = 20.0
    for c_age, coefficient in coefficients[gender].items():
        if age < c_age:
            normal_bmr = weight * coefficient
            break

    if bmr >= normal_bmr:
        return 0.0

    return _get_malus(bmr, normal_bmr - 300, normal_bmr, 6, 3)


def _calculate_protein_deduct_score(protein_percentage: float) -> float:
    """Calculate protein deduct score."""
    if protein_percentage <= 16.0:
        return _get_malus(protein_percentage, 10.0, 16.0, 10, 5)
    if protein_percentage <= 17.0:
        return _get_malus(protein_percentage, 16.0, 17.0, 5, 3)

    return 0.0


def get_body_score(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate the body score (range: 10–100).

    Starts at 100 and deducts penalty points for each metric that falls
    outside its optimal physiological range. The final score is clamped
    to a minimum of 10 (not 0) to distinguish a low-but-measurable result
    from an unavailable or uncalculated metric.

    Penalties are applied for:
      - BMI outside healthy range
      - Body fat percentage above/below target
      - Muscle mass below threshold (SMM in S400 mode, total mass otherwise)
      - Water percentage below target
      - Visceral fat above threshold
      - Bone mass below expected value for body weight
      - Basal metabolic rate below expected value for age/weight
      - Protein percentage below target
    """
    score = 100.0

    score -= _calculate_bmi_deduct_score(config, metrics)
    score -= _calculate_body_fat_deduct_score(config, metrics)
    score -= _calculate_muscle_deduct_score(config, metrics)
    score -= _calculate_water_deduct_score(
        config, to_float(metrics.get(Metric.WATER_PERCENTAGE))
    )
    score -= _calculate_body_visceral_deduct_score(
        to_float(metrics.get(Metric.VISCERAL_FAT))
    )
    score -= _calculate_bone_deduct_score(config, metrics)
    score -= _calculate_basal_metabolism_deduct_score(config, metrics)
    score -= _calculate_protein_deduct_score(
        to_float(metrics.get(Metric.PROTEIN_PERCENTAGE))
    )

    return check_value_constraints(score, 10, 100)

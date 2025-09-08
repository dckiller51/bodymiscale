"""Body score module."""

from collections import namedtuple
from collections.abc import Mapping
from datetime import datetime
from typing import Any, cast

from homeassistant.helpers.typing import StateType

from ..const import CONF_GENDER, CONF_HEIGHT, CONF_SCALE
from ..models import Gender, Metric


def _get_malus(
    data: float,
    min_data: float,
    max_data: float,
    max_malus: int | float,
    min_malus: int | float,
) -> float:
    """Calculate malus based on data and predefined ranges (original logic)."""
    result = ((data - max_data) / (min_data - max_data)) * float(max_malus - min_malus)
    if result >= 0.0:
        return result
    return 0.0


def _calculate_bmi_deduct_score(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate BMI deduct score."""
    bmi_very_low = 14.0
    bmi_low = 15.0
    bmi_normal = 18.5
    bmi_overweight = 28.0
    bmi_obese = 32.0

    if config[CONF_HEIGHT] < 90:
        return 0.0

    bmi = cast(float, metrics[Metric.BMI])
    age = cast(int, metrics[Metric.AGE])
    fat_percentage = cast(float, metrics[Metric.FAT_PERCENTAGE])
    fat_scale = config[CONF_SCALE].get_fat_percentage(age)

    if bmi <= bmi_very_low:
        return 30.0

    if (fat_percentage < fat_scale[2]) and (
        (bmi >= bmi_normal and age >= 18) or (bmi >= bmi_low and age < 18)
    ):
        return 0.0

    if bmi < bmi_low:
        return _get_malus(bmi, bmi_very_low, bmi_low, 30, 15) + 15.0
    if bmi < bmi_normal and age >= 18:
        return _get_malus(bmi, 15.0, 18.5, 15, 5) + 5.0

    if fat_percentage >= fat_scale[2]:
        if bmi >= bmi_obese:
            return 10.0
        if bmi > bmi_overweight:
            return _get_malus(bmi, 28.0, 25.0, 5, 10) + 5.0

    return 0.0


def _calculate_body_fat_deduct_score(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate body fat deduct score."""
    fat_percentage = cast(float, metrics[Metric.FAT_PERCENTAGE])
    age = cast(int, metrics[Metric.AGE])
    gender = config[CONF_GENDER]
    scale = config[CONF_SCALE].get_fat_percentage(age)

    best_fat_level = scale[2] - 3.0 if gender == Gender.MALE else scale[2] - 2.0

    if scale[0] <= fat_percentage < best_fat_level:
        return 0.0
    if fat_percentage >= scale[3]:
        return 20.0

    if fat_percentage < scale[3]:
        return _get_malus(fat_percentage, scale[3], scale[2], 20, 10) + 10.0

    if fat_percentage <= scale[2]:
        return _get_malus(fat_percentage, scale[2], best_fat_level, 3, 9) + 3.0

    if fat_percentage < scale[0]:
        return _get_malus(fat_percentage, 1.0, scale[0], 3, 10) + 3.0

    return 0.0


def _calculate_common_deduct_score(
    min_value: float, max_value: float, value: float
) -> float:
    """Calculate common deduct score based on min/max values."""
    if value >= max_value:
        return 0.0
    if value < min_value:
        return 10.0
    return _get_malus(value, min_value, max_value, 10, 5) + 5.0


def _calculate_muscle_deduct_score(
    config: Mapping[str, Any], muscle_mass: float
) -> float:
    """Calculate muscle mass deduct score."""
    scale = config[CONF_SCALE].muscle_mass
    return _calculate_common_deduct_score(scale[0] - 5.0, scale[0], muscle_mass)


def _calculate_water_deduct_score(
    config: Mapping[str, Any], water_percentage: float
) -> float:
    """Calculate water percentage deduct score."""
    water_percentage_normal = 55.0 if config[CONF_GENDER] == Gender.MALE else 45.0
    return _calculate_common_deduct_score(
        water_percentage_normal - 5.0, water_percentage_normal, water_percentage
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

    weight = cast(float, metrics[Metric.WEIGHT])
    bone_mass = cast(float, metrics[Metric.BONE_MASS])
    expected_bone_mass = entries[-1].bone_mass
    for entry in entries:
        if weight >= entry.min_weight:
            expected_bone_mass = entry.bone_mass
            break

    return _calculate_common_deduct_score(
        expected_bone_mass - 0.3, expected_bone_mass, bone_mass
    )


def _calculate_body_visceral_deduct_score(visceral_fat: float) -> float:
    """Calculate visceral fat deduct score."""
    max_data = 15.0
    min_data = 10.0

    if visceral_fat < min_data:
        return 0.0
    if visceral_fat >= max_data:
        return 15.0
    return _get_malus(visceral_fat, max_data, min_data, max_data, min_data) + 10.0


def _calculate_basal_metabolism_deduct_score(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate basal metabolism deduct score."""
    gender = config[CONF_GENDER]
    age = cast(int, metrics[Metric.AGE])
    weight = cast(float, metrics[Metric.WEIGHT])
    bmr = cast(float, metrics[Metric.BMR])

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
    if bmr <= normal_bmr - 300:
        return 6.0
    return _get_malus(bmr, normal_bmr - 300, normal_bmr, 6, 3) + 5.0


def _calculate_protein_deduct_score(protein_percentage: float) -> float:
    """Calculate protein deduct score."""
    if protein_percentage > 17.0:
        return 0.0
    if protein_percentage < 10.0:
        return 10.0
    if protein_percentage <= 16.0:
        return _get_malus(protein_percentage, 10.0, 16.0, 10, 5) + 5.0
    if protein_percentage <= 17.0:
        return _get_malus(protein_percentage, 16.0, 17.0, 5, 3) + 3.0
    return 0.0


def get_body_score(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate the body score."""
    score = 100.0
    score -= _calculate_bmi_deduct_score(config, metrics)
    score -= _calculate_body_fat_deduct_score(config, metrics)
    score -= _calculate_muscle_deduct_score(
        config, cast(float, metrics[Metric.MUSCLE_MASS])
    )
    score -= _calculate_water_deduct_score(
        config, cast(float, metrics[Metric.WATER_PERCENTAGE])
    )
    score -= _calculate_body_visceral_deduct_score(
        cast(float, metrics[Metric.VISCERAL_FAT])
    )
    score -= _calculate_bone_deduct_score(config, metrics)
    score -= _calculate_basal_metabolism_deduct_score(config, metrics)
    score -= _calculate_protein_deduct_score(
        cast(float, metrics[Metric.PROTEIN_PERCENTAGE])
    )

    return max(0.0, score)

"""Body score module."""

from collections import namedtuple
from collections.abc import Mapping
from typing import Any

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
    result = ((data - max_data) / (min_data - max_data)) * float(max_malus - min_malus)
    if result >= 0.0:
        return result
    return 0.0


def _calculate_bmi_deduct_score(  # pylint: disable=too-many-return-statements
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType]
) -> float:
    bmi_low = 15.0
    bmi_very_low = 14.0
    bmi_normal = 18.5
    bmi_overweight = 28.0
    bmi_obese = 32.0

    if config[CONF_HEIGHT] < 90:
        # "BMI is not reasonable
        return 0.0
    if metrics[Metric.BMI] <= bmi_very_low:
        # Extremely skinny (bmi < 14)
        return 30.0

    fat_scale = config[CONF_SCALE].get_fat_percentage(metrics[Metric.AGE])

    # Perfect range (bmi >= 18.5 and fat_percentage not high for adults, bmi >= 15.0 for kids
    if metrics[Metric.FAT_PERCENTAGE] < fat_scale[2] and (
        (metrics[Metric.BMI] >= bmi_normal and metrics[Metric.AGE] >= 18)
        or metrics[Metric.BMI] >= bmi_very_low
        and metrics[Metric.AGE] < 18
    ):
        return 0.0

    # Too skinny (bmi between 14 and 15)
    if metrics[Metric.BMI] < bmi_low:
        return _get_malus(metrics[Metric.BMI], bmi_very_low, bmi_low, 30, 15) + 15.0
    # Skinny (for adults, between 15 and 18.5)
    if metrics[Metric.BMI] < bmi_normal and metrics[Metric.AGE] >= 18:
        return _get_malus(metrics[Metric.BMI], 15.0, 18.5, 15, 5) + 5.0

    # Normal or high bmi but too much bodyfat
    if (
        metrics[Metric.FAT_PERCENTAGE] >= fat_scale[2]
        and (metrics[Metric.BMI] >= bmi_low and metrics[Metric.AGE] < 18)
        or (metrics[Metric.BMI] >= bmi_normal and metrics[Metric.AGE] >= 18)
    ):
        # Obese
        if metrics[Metric.BMI] >= bmi_obese:
            return 10.0
        # Overweight
        if metrics[Metric.BMI] > bmi_overweight:
            return _get_malus(metrics[Metric.BMI], 28.0, 25.0, 5, 10) + 5.0

    return 0.0


def _calculate_body_fat_deduct_score(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType]
) -> float:
    scale = config[CONF_SCALE].get_fat_percentage(metrics[Metric.AGE])

    if config[CONF_GENDER] == Gender.MALE:
        best = scale[2] - 3.0
    else:
        best = scale[2] - 2.0

    # Slightly low in fat or low part or normal fat
    if scale[0] <= metrics[Metric.FAT_PERCENTAGE] < best:
        return 0.0
    if metrics[Metric.FAT_PERCENTAGE] >= scale[3]:
        return 20.0

    # Slightly high body fat
    if metrics[Metric.FAT_PERCENTAGE] < scale[3]:
        return (
            _get_malus(metrics[Metric.FAT_PERCENTAGE], scale[3], scale[2], 20, 10)
            + 10.0
        )

    # High part of normal fat
    if metrics[Metric.FAT_PERCENTAGE] <= scale[2]:
        return _get_malus(metrics[Metric.FAT_PERCENTAGE], scale[2], best, 3, 9) + 3.0

    # Very low in fat
    if metrics[Metric.FAT_PERCENTAGE] < scale[0]:
        return _get_malus(metrics[Metric.FAT_PERCENTAGE], 1.0, scale[0], 3, 10) + 3.0

    return 0.0


def _calculate_common_deduct_score(
    min_value: float, max_value: float, value: float
) -> float:
    if value >= max_value:
        return 0.0
    if value < min_value:
        return 10.0
    return _get_malus(value, min_value, max_value, 10, 5) + 5.0


def _calculate_muscle_deduct_score(
    config: Mapping[str, Any], muscle_mass: float
) -> float:
    scale = config[CONF_SCALE].muscle_mass
    return _calculate_common_deduct_score(scale[0] - 5.0, scale[0], muscle_mass)


def _calculate_water_deduct_score(
    config: Mapping[str, Any], water_percentage: float
) -> float:
    # No malus = normal or good; maximum malus (10.0) = less than normal-5.0;
    # malus = between 5 and 10, on your water being between normal-5.0 and normal
    water_percentage_normal = 45
    if config[CONF_GENDER] == Gender.MALE:
        water_percentage_normal = 55

    return _calculate_common_deduct_score(
        water_percentage_normal - 5.0, water_percentage_normal, water_percentage
    )


def _calculate_bone_deduct_score(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType]
) -> float:
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

    bone_mass = entries[-1].bone_mass
    for entry in entries:
        if metrics[Metric.WEIGHT] >= entry.min_weight:
            bone_mass = entry.bone_mass

    return _calculate_common_deduct_score(
        bone_mass - 0.3, bone_mass, metrics[Metric.BONE_MASS]
    )


def _calculate_body_visceral_deduct_score(visceral_fat: float) -> float:
    # No malus = normal; maximum malus (15.0) = very high; malus = between 10 and 15
    # with your visceral fat in your high range
    max_data = 15.0
    min_data = 10.0

    if visceral_fat < min_data:
        # For some reason, the original app would try to
        # return 3.0 if vfat == 8 and 5.0 if vfat == 9
        # but i's overwritten with 0.0 anyway before return
        return 0.0
    if visceral_fat >= max_data:
        return 15.0
    return _get_malus(visceral_fat, max_data, min_data, max_data, min_data) + 10.0


def _calculate_basal_metabolism_deduct_score(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType]
) -> float:
    # Get normal BMR
    normal_bmr = 20.0
    coefficients = {
        Gender.MALE: {30: 21.6, 50: 20.07, 100: 19.35},
        Gender.FEMALE: {30: 21.24, 50: 19.53, 100: 18.63},
    }

    for c_age, coefficient in coefficients[config[CONF_GENDER]].items():
        if metrics[Metric.AGE] < c_age:
            normal_bmr = metrics[Metric.WEIGHT] * coefficient

    if metrics[Metric.BMR] >= normal_bmr:
        return 0.0
    if metrics[Metric.BMR] <= (normal_bmr - 300):
        return 6.0
    # It's really + 5.0 in the app, but it's probably a mistake, should be 3.0
    return _get_malus(metrics[Metric.BMR], normal_bmr - 300, normal_bmr, 6, 3) + 5.0


def _calculate_protein_deduct_score(protein_percentage: float) -> float:
    # low: 10,16; normal: 16,17
    # Check limits
    if protein_percentage > 17.0:
        return 0.0
    if protein_percentage < 10.0:
        return 10.0

    # Return values for low proteins or normal proteins
    if protein_percentage <= 16.0:
        return _get_malus(protein_percentage, 10.0, 16.0, 10, 5) + 5.0
    if protein_percentage <= 17.0:
        return _get_malus(protein_percentage, 16.0, 17.0, 5, 3) + 3.0

    return 0.0


def get_body_score(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType]
) -> float:
    """Calculate the body score."""
    score = 100.0
    score -= _calculate_bmi_deduct_score(config, metrics)
    score -= _calculate_body_fat_deduct_score(config, metrics)
    score -= _calculate_muscle_deduct_score(config, metrics[Metric.MUSCLE_MASS])
    score -= _calculate_water_deduct_score(config, metrics[Metric.WATER_PERCENTAGE])
    score -= _calculate_body_visceral_deduct_score(metrics[Metric.VISCERAL_FAT])
    score -= _calculate_bone_deduct_score(config, metrics)
    score -= _calculate_basal_metabolism_deduct_score(config, metrics)
    score -= _calculate_protein_deduct_score(metrics[Metric.PROTEIN_PERCENTAGE])

    return score

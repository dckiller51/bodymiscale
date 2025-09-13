"""Metrics module, which requires only weight."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from homeassistant.helpers.typing import StateType

from custom_components.bodymiscale.const import CONF_GENDER, CONF_HEIGHT

from ..models import Gender, Metric
from ..util import check_value_constraints, to_float


def get_bmi(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate BMI."""
    height_val = to_float(config.get(CONF_HEIGHT))
    weight = to_float(metrics.get(Metric.WEIGHT))

    bmi = 0.0

    if height_val is not None and weight is not None:
        height_c = height_val / 100
        bmi = weight / (height_c * height_c)

    return check_value_constraints(bmi, 10, 90)


def get_bmr(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate Basal Metabolic Rate (BMR)."""
    weight = to_float(metrics.get(Metric.WEIGHT))
    age = to_float(metrics.get(Metric.AGE))
    height = to_float(config.get(CONF_HEIGHT))
    gender = config.get(CONF_GENDER)

    if weight is None or age is None or height is None or gender is None:
        return 0.0

    if gender == Gender.FEMALE:
        bmr = 864.6 + weight * 10.2036
        bmr -= height * 0.39336
        bmr -= age * 6.204
    else:
        bmr = 877.8 + weight * 14.916
        bmr -= height * 0.726
        bmr -= age * 8.976

    bmr = min(bmr, 5000)
    return check_value_constraints(bmr, 500, 5000)


def get_visceral_fat(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate Visceral Fat."""
    height = to_float(config.get(CONF_HEIGHT))
    weight = to_float(metrics.get(Metric.WEIGHT))
    age = to_float(metrics.get(Metric.AGE))
    gender = config.get(CONF_GENDER)

    if height is None or weight is None or age is None or gender is None:
        return 1.0

    if gender == Gender.MALE:
        if height < weight * 1.6 + 63.0:
            vfal = age * 0.15 + (
                (weight * 305.0) / ((height * 0.0826 * height - height * 0.4) + 48.0)
                - 2.9
            )
        else:
            vfal = (
                age * 0.15
                + (weight * (height * -0.0015 + 0.765) - height * 0.143)
                - 5.0
            )
    else:
        if weight <= height * 0.5 - 13.0:
            vfal = (
                age * 0.07
                + (weight * (height * -0.0024 + 0.691) - height * 0.027)
                - 10.5
            )
        else:
            vfal = age * 0.07 + (
                (weight * 500.0) / ((height * 1.45 + height * 0.1158 * height) - 120.0)
                - 6.0
            )

    return check_value_constraints(vfal, 1, 50)

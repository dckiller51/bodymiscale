"""Metrics module, which require only weight."""

from collections.abc import Mapping
from typing import Any

from homeassistant.helpers.typing import StateType

from custom_components.bodymiscale.const import CONF_GENDER, CONF_HEIGHT

from ..models import Gender, Metric
from ..util import check_value_constraints


def get_bmi(config: Mapping[str, Any], metrics: Mapping[Metric, StateType]) -> float:
    """Get MBI."""
    heiht_c = config[CONF_HEIGHT] / 100
    bmi = metrics[Metric.WEIGHT] / (heiht_c * heiht_c)
    return check_value_constraints(bmi, 10, 90)


def get_bmr(config: Mapping[str, Any], metrics: Mapping[Metric, StateType]) -> float:
    """Get BMR."""
    if config[CONF_GENDER] == Gender.FEMALE:
        bmr = 864.6 + metrics[Metric.WEIGHT] * 10.2036
        bmr -= config[CONF_HEIGHT] * 0.39336
        bmr -= metrics[Metric.AGE] * 6.204

        if bmr > 2996:
            bmr = 5000
    else:
        bmr = 877.8 + metrics[Metric.WEIGHT] * 14.916
        bmr -= config[CONF_HEIGHT] * 0.726
        bmr -= metrics[Metric.AGE] * 8.976

        if bmr > 2322:
            bmr = 5000

    return check_value_constraints(bmr, 500, 5000)


def get_visceral_fat(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType]
) -> float:
    """Get Visceral Fat."""
    height = config[CONF_HEIGHT]
    weight = metrics[Metric.WEIGHT]
    age = metrics[Metric.AGE]

    if config[CONF_GENDER] == Gender.MALE:
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

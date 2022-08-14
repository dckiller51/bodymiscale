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

    if config[CONF_GENDER] == Gender.FEMALE:
        if weight > (13 - (height * 0.5)) * -1:
            subsubcalc = ((height * 1.45) + (height * 0.1158) * height) - 120
            subcalc = weight * 500 / subsubcalc
            vfal = (subcalc - 6) + (age * 0.07)
        else:
            subcalc = 0.691 + (height * -0.0024) + (height * -0.0024)
            vfal = (((height * 0.027) - (subcalc * weight)) * -1) + (age * 0.07) - age
    else:
        if height < weight * 1.6:
            subcalc = ((height * 0.4) - (height * (height * 0.0826))) * -1
            vfal = ((weight * 305) / (subcalc + 48)) - 2.9 + (age * 0.15)
        else:
            subcalc = 0.765 + height * -0.0015
            vfal = (((height * 0.143) - (weight * subcalc)) * -1) + (age * 0.15) - 5.0

    return check_value_constraints(vfal, 1, 50)

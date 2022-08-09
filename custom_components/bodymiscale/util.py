"""Util module."""


from collections.abc import Mapping
from typing import Any

from .const import CONF_GENDER, CONF_HEIGHT
from .models import Gender


def check_value_constraints(value: float, minimum: float, maximum: float) -> float:
    """Set the value to a boundary if it overflows."""
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def get_ideal_weight(config: Mapping[str, Any]) -> float:
    """Get ideal weight (just doing a reverse BMI, should be something better)."""
    if config[CONF_GENDER] == Gender.FEMALE:
        ideal = float(config[CONF_HEIGHT] - 70) * 0.6
    else:
        ideal = float(config[CONF_HEIGHT] - 80) * 0.7

    return round(ideal, 0)


def get_bmi_label(bmi: float) -> str:  # pylint: disable=too-many-return-statements
    """Get BMI label."""
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal or Healthy Weight"
    if bmi < 27:
        return "Slight overweight"
    if bmi < 30:
        return "Overweight"
    if bmi < 35:
        return "Moderate obesity"
    if bmi < 40:
        return "Severe obesity"
    return "Massive obesity"

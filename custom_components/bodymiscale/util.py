"""Util module."""

from collections.abc import Mapping
from datetime import datetime
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
        return "underweight"
    if bmi < 25:
        return "normal_or_healthy_weight"
    if bmi < 27:
        return "slight_overweight"
    if bmi < 30:
        return "overweight"
    if bmi < 35:
        return "moderate_obesity"
    if bmi < 40:
        return "severe_obesity"
    return "massive_obesity"


def get_age(date: str) -> int:
    """Get current age from birthdate."""
    born = datetime.strptime(date, "%Y-%m-%d")
    today = datetime.today()
    age = today.year - born.year
    if (today.month, today.day) < (born.month, born.day):
        age -= 1
    return age

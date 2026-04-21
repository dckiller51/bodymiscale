"""Metrics module — weight-based calculations (no impedance required).

Three distinct modes:

  XIAOMI :
    BMR      : exact Zepp Life formula.
    Visceral : exact Zepp Life formula.

  SCIENCE :
    BMR      : Mifflin–St Jeor 1990 (recommended by AND/WHO/ACSM).
    Visceral : Zepp Life formula (no validated WHO alternative for BIA).

  S400 :
    BMR      : revised Harris-Benedict (Roza & Shizgal 1984), more accurate for adults >50 years.
    Visceral : Zepp Life formula with ×2 divisor (S400 manufacturer calibration).
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from homeassistant.helpers.typing import StateType

from ..const import (
    ALGO_SCIENCE,
    ALGO_XIAOMI,
    CONF_CALCULATION_MODE,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_IMPEDANCE_MODE,
    IMPEDANCE_MODE_DUAL,
)
from ..models import Gender, Metric
from ..util import check_value_constraints, to_float


def _is_dual(config: Mapping[str, Any]) -> bool:
    return config.get(CONF_IMPEDANCE_MODE) == IMPEDANCE_MODE_DUAL


def get_bmi(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate BMI — identical in all 3 modes."""
    h = to_float(config.get(CONF_HEIGHT))
    w = to_float(metrics.get(Metric.WEIGHT))

    if h <= 0 or w <= 0:
        return 0.0

    bmi = w / (h / 100.0) ** 2
    return check_value_constraints(bmi, 10, 90)


def get_bmr(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate Basal Metabolic Rate (BMR).

    XIAOMI :
        Exact Zepp Life formula.
        Male   : BMR = 877.8 + W×14.916 − H×0.726 − A×8.976
        Female : BMR = 864.6 + W×10.2036 − H×0.39336 − A×6.204

    SCIENCE :
        Mifflin–St Jeor 1990 (recommended by AND, ADA, ACSM, WHO).
        Male   : BMR = 10×W + 6.25×H − 5×A + 5
        Female : BMR = 10×W + 6.25×H − 5×A − 161

    S400 :
        Revised Harris-Benedict — Roza & Shizgal 1984.
        Better accuracy for adults >50 years and overweight subjects.
        Male   : BMR = 88.362 + 13.397×W + 4.799×H − 5.677×A
        Female : BMR = 447.593 + 9.247×W + 3.098×H − 4.330×A
    """
    w = to_float(metrics.get(Metric.WEIGHT))
    a = to_float(metrics.get(Metric.AGE))
    h = to_float(config.get(CONF_HEIGHT))
    gender = config.get(CONF_GENDER)
    mode = config.get(CONF_CALCULATION_MODE, ALGO_XIAOMI)

    if w <= 0 or a <= 0 or h <= 0 or gender is None:
        return 0.0

    if _is_dual(config):
        # S400 — Revised Harris-Benedict
        if gender == Gender.MALE:
            bmr = 88.362 + 13.397 * w + 4.799 * h - 5.677 * a
        else:
            bmr = 447.593 + 9.247 * w + 3.098 * h - 4.330 * a

    elif mode == ALGO_SCIENCE:
        # Mifflin–St Jeor
        if gender == Gender.MALE:
            bmr = 10.0 * w + 6.25 * h - 5.0 * a + 5.0
        else:
            bmr = 10.0 * w + 6.25 * h - 5.0 * a - 161.0

    else:
        # XIAOMI — Zepp Life exact
        if gender == Gender.MALE:
            bmr = 877.8 + w * 14.916 - h * 0.726 - a * 8.976
        else:
            bmr = 864.6 + w * 10.2036 - h * 0.39336 - a * 6.204

    return check_value_constraints(bmr, 500, 5000)


def get_visceral_fat(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate Visceral Fat Rating.

    XIAOMI / SCIENCE :
        Exact Zepp Life formula.

    S400 :
        Same Zepp Life base but divided by 2 — empirical calibration
        on manufacturer data (S400 manufacturer: 8, Xiaomi: 16.3).
        Ratio ≈ 0.5 confirmed on calibration point.
    """
    h = to_float(config.get(CONF_HEIGHT))
    w = to_float(metrics.get(Metric.WEIGHT))
    a = to_float(metrics.get(Metric.AGE))
    gender = config.get(CONF_GENDER)

    if h <= 0 or w <= 0 or a <= 0 or gender is None:
        return 1.0

    # Common Zepp Life formula (base for all modes)
    if gender == Gender.MALE:
        if h < w * 1.6 + 63.0:
            vfal = a * 0.15 + ((w * 305.0) / ((h * 0.0826 * h - h * 0.4) + 48.0) - 2.9)
        else:
            vfal = a * 0.15 + (w * (h * -0.0015 + 0.765) - h * 0.143) - 5.0
    else:
        if w <= h * 0.5 - 13.0:
            vfal = a * 0.07 + (w * (h * -0.0024 + 0.691) - h * 0.027) - 10.5
        else:
            vfal = a * 0.07 + (
                (w * 500.0) / ((h * 1.45 + h * 0.1158 * h) - 120.0) - 6.0
            )

    if _is_dual(config):
        # S400 : manufacturer calibration → divisor ×2
        vfal = vfal / 2.0

    return check_value_constraints(vfal, 1, 50)

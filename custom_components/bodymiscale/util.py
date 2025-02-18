"""Util module."""  # Utility functions module

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .const import CONF_GENDER, CONF_HEIGHT
from .models import Gender


def check_value_constraints(value: float, minimum: float, maximum: float) -> float:
    """Set the value to a boundary if it overflows."""  # Constrain a value within a range
    if value < minimum:
        return minimum  # Return minimum if value is below minimum
    if value > maximum:
        return maximum  # Return maximum if value is above maximum
    return value  # Return the value if it's within the range


def get_ideal_weight(config: Mapping[str, Any]) -> float:
    """Get ideal weight (just doing a reverse BMI, should be something better)."""  # Calculate ideal weight (using a simplified formula)
    if config[CONF_GENDER] == Gender.FEMALE:  # If gender is female
        ideal = float(config[CONF_HEIGHT] - 70) * 0.6  # Calculate ideal weight for females
    else:  # If gender is male
        ideal = float(config[CONF_HEIGHT] - 80) * 0.7  # Calculate ideal weight for males

    return round(ideal, 0)  # Round the ideal weight to the nearest whole number


def get_bmi_label(bmi: float) -> str:  # pylint: disable=too-many-return-statements
    """Get BMI label."""  # Get the BMI category label
    if bmi < 18.5:
        return "underweight"  # Underweight
    if bmi < 25:
        return "normal_or_healthy_weight"  # Normal or healthy weight
    if bmi < 27:
        return "slight_overweight"  # Slightly overweight
    if bmi < 30:
        return "overweight"  # Overweight
    if bmi < 35:
        return "moderate_obesity"  # Moderately obese
    if bmi < 40:
        return "severe_obesity"  # Severely obese
    return "massive_obesity"  # Morbidly obese


def get_age(date: str) -> int:
    """Get current age from birthdate."""  # Calculate age from birthdate
    born = datetime.strptime(date, "%Y-%m-%d")  # Parse the birthdate string
    today = datetime.today()  # Get today's date
    age = today.year - born.year  # Calculate the age
    if (today.month, today.day) < (born.month, born.day):  # Adjust if birthday hasn't occurred yet this year
        age -= 1
    return age  # Return the calculated age

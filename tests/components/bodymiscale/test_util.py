"""Tests for bodymiscale utility functions."""

from __future__ import annotations

import pytest
from freezegun import freeze_time

from custom_components.bodymiscale.const import CONF_GENDER, CONF_HEIGHT
from custom_components.bodymiscale.models import Gender
from custom_components.bodymiscale.util import (
    check_value_constraints,
    clamp_water_percentage,
    get_age,
    get_bmi_label,
    get_bmr_schofield,
    get_ideal_weight,
    get_metabolic_age_clamped,
    to_float,
)

# ===========================================================================
# to_float
# ===========================================================================


def test_to_float_from_int() -> None:
    """Int must be converted to float."""
    assert to_float(42) == 42.0
    assert to_float(0) == 0.0


def test_to_float_from_float() -> None:
    """Float must pass through unchanged."""
    assert to_float(3.14) == pytest.approx(3.14)


def test_to_float_from_valid_string() -> None:
    """Numeric string must be converted to float."""
    assert to_float("3.14") == pytest.approx(3.14)
    assert to_float("0") == 0.0
    assert to_float("-5.5") == pytest.approx(-5.5)


def test_to_float_from_invalid_string_returns_default() -> None:
    """Non-numeric string must return default."""
    assert to_float("unavailable") == 0.0
    assert to_float("unknown") == 0.0
    assert to_float("") == 0.0


def test_to_float_custom_default_on_invalid_string() -> None:
    """Non-numeric string must use the provided default."""
    assert to_float("bad", default=99.9) == pytest.approx(99.9)


def test_to_float_unsupported_type_returns_default() -> None:
    """None, list, dict must return default."""
    assert to_float(None) == 0.0
    assert to_float([1, 2]) == 0.0
    assert to_float({"a": 1}) == 0.0


def test_to_float_unsupported_type_custom_default() -> None:
    """None with custom default must return that default."""
    assert to_float(None, default=-1.0) == pytest.approx(-1.0)


# ===========================================================================
# check_value_constraints
# ===========================================================================


def test_check_value_constraints_below_min() -> None:
    """Value below min must be clamped to min."""
    assert check_value_constraints(-1.0, 0.0, 10.0) == 0.0


def test_check_value_constraints_above_max() -> None:
    """Value above max must be clamped to max."""
    assert check_value_constraints(15.0, 0.0, 10.0) == 10.0


def test_check_value_constraints_within_bounds() -> None:
    """Value within bounds must be returned unchanged."""
    assert check_value_constraints(5.0, 0.0, 10.0) == 5.0


def test_check_value_constraints_at_boundaries() -> None:
    """Values exactly at boundaries must be returned unchanged."""
    assert check_value_constraints(0.0, 0.0, 10.0) == 0.0
    assert check_value_constraints(10.0, 0.0, 10.0) == 10.0


# ===========================================================================
# get_ideal_weight
# ===========================================================================


def test_get_ideal_weight_female() -> None:
    """Female ideal weight: (height - 70) * 0.6."""
    config = {CONF_HEIGHT: 165.0, CONF_GENDER: Gender.FEMALE}
    assert get_ideal_weight(config) == round((165.0 - 70.0) * 0.6, 1)


def test_get_ideal_weight_male() -> None:
    """Male ideal weight: (height - 80) * 0.7."""
    config = {CONF_HEIGHT: 180.0, CONF_GENDER: Gender.MALE}
    assert get_ideal_weight(config) == round((180.0 - 80.0) * 0.7, 1)


def test_get_ideal_weight_rounded() -> None:
    """Result must be rounded to 1 decimal place."""
    config = {CONF_HEIGHT: 172.0, CONF_GENDER: Gender.FEMALE}
    result = get_ideal_weight(config)
    assert result == round(result, 1)


# ===========================================================================
# get_bmr_schofield
# ===========================================================================


@pytest.mark.parametrize(
    "age, gender, weight",
    [
        (1, Gender.MALE, 10.0),
        (5, Gender.MALE, 20.0),
        (14, Gender.MALE, 50.0),
        (25, Gender.MALE, 75.0),
        (45, Gender.MALE, 80.0),
        (65, Gender.MALE, 78.0),
        (1, Gender.FEMALE, 10.0),
        (5, Gender.FEMALE, 20.0),
        (14, Gender.FEMALE, 50.0),
        (25, Gender.FEMALE, 60.0),
        (45, Gender.FEMALE, 65.0),
        (65, Gender.FEMALE, 63.0),
    ],
)
def test_get_bmr_schofield_all_age_brackets(
    age: int, gender: Gender, weight: float
) -> None:
    """get_bmr_schofield must return a positive float for every age/gender bracket."""
    result = get_bmr_schofield(weight=weight, age=age, gender=gender)
    assert result > 0


def test_get_bmr_schofield_male_0_3() -> None:
    """Male 0-3: slope=59.512, constant=-30.4."""
    result = get_bmr_schofield(weight=10.0, age=1, gender=Gender.MALE)
    assert result == pytest.approx(59.512 * 10.0 + (-30.4), abs=0.1)


def test_get_bmr_schofield_female_18_30() -> None:
    """Female 18-30: slope=14.818, constant=486.6."""
    result = get_bmr_schofield(weight=60.0, age=25, gender=Gender.FEMALE)
    assert result == pytest.approx(14.818 * 60.0 + 486.6, abs=0.1)


def test_get_bmr_schofield_heavier_higher_bmr() -> None:
    """Heavier person must have higher BMR, all else equal."""
    light = get_bmr_schofield(weight=60.0, age=35, gender=Gender.MALE)
    heavy = get_bmr_schofield(weight=90.0, age=35, gender=Gender.MALE)
    assert heavy > light


def test_get_bmr_schofield_age_boundary_3() -> None:
    """Age exactly 3 must use the 3-10 bracket."""
    result = get_bmr_schofield(weight=15.0, age=3, gender=Gender.MALE)
    assert result == pytest.approx(22.706 * 15.0 + 504.3, abs=0.1)


def test_get_bmr_schofield_age_boundary_60() -> None:
    """Age exactly 60 must use the 60+ bracket."""
    result = get_bmr_schofield(weight=70.0, age=60, gender=Gender.MALE)
    assert result == pytest.approx(11.711 * 70.0 + 587.7, abs=0.1)


# ===========================================================================
# get_metabolic_age_clamped
# ===========================================================================


def test_metabolic_age_clamped_within_range() -> None:
    """Metabolic age within [12, real_age+25] must be returned unchanged."""
    assert get_metabolic_age_clamped(30, 30) == 30


def test_metabolic_age_clamped_below_minimum() -> None:
    """Metabolic age below 12 must be clamped to 12."""
    assert get_metabolic_age_clamped(5, 30) == 12


def test_metabolic_age_clamped_above_ceiling() -> None:
    """Metabolic age above real_age+25 must be clamped."""
    assert get_metabolic_age_clamped(80, 30) == 55


def test_metabolic_age_clamped_max_cap_95() -> None:
    """Ceiling must never exceed 95."""
    assert get_metabolic_age_clamped(100, 80) == 95


# ===========================================================================
# clamp_water_percentage
# ===========================================================================


def test_clamp_water_within_range() -> None:
    """Water percentage within [35, 73] must be returned unchanged."""
    assert clamp_water_percentage(55.0) == 55.0


def test_clamp_water_below_min() -> None:
    """Water percentage below 35 must be clamped to 35."""
    assert clamp_water_percentage(10.0) == 35.0


def test_clamp_water_above_max() -> None:
    """Water percentage above 73 must be clamped to 73."""
    assert clamp_water_percentage(80.0) == 73.0


def test_clamp_water_at_boundaries() -> None:
    """Values at exact boundaries must be returned unchanged."""
    assert clamp_water_percentage(35.0) == 35.0
    assert clamp_water_percentage(73.0) == 73.0


# ===========================================================================
# get_bmi_label
# ===========================================================================


@pytest.mark.parametrize(
    "bmi, expected",
    [
        (15.0, "underweight"),
        (18.4, "underweight"),
        (18.5, "normal_or_healthy_weight"),
        (24.9, "normal_or_healthy_weight"),
        (25.0, "slight_overweight"),
        (26.9, "slight_overweight"),
        (27.0, "overweight"),
        (29.9, "overweight"),
        (30.0, "moderate_obesity"),
        (34.9, "moderate_obesity"),
        (35.0, "severe_obesity"),
        (39.9, "severe_obesity"),
        (40.0, "massive_obesity"),
        (50.0, "massive_obesity"),
    ],
)
def test_get_bmi_label(bmi: float, expected: str) -> None:
    """BMI label must match WHO classification at every threshold."""
    assert get_bmi_label(bmi) == expected


# ===========================================================================
# get_age
# ===========================================================================


def test_get_age_valid_date() -> None:
    """get_age must return a positive integer for a valid past date."""
    age = get_age("1990-01-15")
    assert isinstance(age, int)
    assert age > 0


@freeze_time("2026-05-15")
def test_get_age_birthday_already_passed() -> None:
    """When birthday has passed this year, age = current year - birth year."""
    assert get_age("1990-01-01") == 36


@freeze_time("2026-05-15")
def test_get_age_birthday_not_yet_this_year() -> None:
    """When birthday has not yet occurred this year, age = year diff - 1."""
    assert get_age("1990-12-31") == 35


def test_get_age_invalid_string_returns_zero() -> None:
    """Invalid date string must return 0."""
    assert get_age("not-a-date") == 0
    assert get_age("") == 0
    assert get_age("2099-13-45") == 0


def test_get_age_none_returns_zero() -> None:
    """None must return 0."""
    assert get_age(None) == 0  # type: ignore[arg-type]

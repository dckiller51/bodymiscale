"""Tests for metrics/scale.py."""

from __future__ import annotations

import pytest

from custom_components.bodymiscale.metrics.scale import Scale
from custom_components.bodymiscale.models import Gender

# ===========================================================================
# get_fat_percentage — all age ranges
# ===========================================================================


@pytest.mark.parametrize(
    "age, gender, expected_len",
    [
        (0, Gender.FEMALE, 4),
        (12, Gender.MALE, 4),
        (14, Gender.FEMALE, 4),
        (16, Gender.MALE, 4),
        (18, Gender.FEMALE, 4),
        (40, Gender.MALE, 4),
        (60, Gender.FEMALE, 4),
        (100, Gender.MALE, 4),
    ],
)
def test_get_fat_percentage_all_age_ranges(
    age: int, gender: Gender, expected_len: int
) -> None:
    """get_fat_percentage must return 4 thresholds for every standard age range."""
    scale = Scale(height=170, gender=gender)
    result = scale.get_fat_percentage(age)
    assert len(result) == expected_len
    assert all(isinstance(v, float) for v in result)


def test_get_fat_percentage_female_18_40() -> None:
    """Female 18-40 fat% thresholds must match the table values."""
    scale = Scale(height=165, gender=Gender.FEMALE)
    result = scale.get_fat_percentage(25)
    assert result == [21.0, 28.0, 35.0, 40.0]


def test_get_fat_percentage_male_40_60() -> None:
    """Male 40-60 fat% thresholds must match the table values."""
    scale = Scale(height=175, gender=Gender.MALE)
    result = scale.get_fat_percentage(50)
    assert result == [12.0, 18.0, 23.0, 28.0]


# ===========================================================================
# get_fat_percentage — fallback (age >= 101)
# ===========================================================================


def test_get_fat_percentage_fallback_above_100_female() -> None:
    """Age > 100 must fall back to the 60-101 entry for female."""
    scale = Scale(height=160, gender=Gender.FEMALE)
    result = scale.get_fat_percentage(101)
    assert result == [23.0, 30.0, 37.0, 42.0]


def test_get_fat_percentage_fallback_above_100_male() -> None:
    """Age > 100 must fall back to the 60-101 entry for male."""
    scale = Scale(height=175, gender=Gender.MALE)
    result = scale.get_fat_percentage(120)
    assert result == [14.0, 20.0, 25.0, 30.0]


def test_get_fat_percentage_fallback_age_200() -> None:
    """Extreme age must always return a valid 4-element list via fallback."""
    scale = Scale(height=170, gender=Gender.FEMALE)
    result = scale.get_fat_percentage(200)
    assert len(result) == 4


# ===========================================================================
# muscle_mass — normal ranges
# ===========================================================================


def test_muscle_mass_tall_male() -> None:
    """Male ≥ 170 cm must return the first muscle mass entry."""
    scale = Scale(height=180, gender=Gender.MALE)
    result = scale.muscle_mass
    assert result == [49.4, 59.5]


def test_muscle_mass_medium_male() -> None:
    """Male 160-169 cm must return the second muscle mass entry."""
    scale = Scale(height=165, gender=Gender.MALE)
    result = scale.muscle_mass
    assert result == [44.0, 52.5]


def test_muscle_mass_tall_female() -> None:
    """Female ≥ 160 cm must return the first muscle mass entry."""
    scale = Scale(height=162, gender=Gender.FEMALE)
    result = scale.muscle_mass
    assert result == [36.5, 42.6]


def test_muscle_mass_medium_female() -> None:
    """Female 150-159 cm must return the second muscle mass entry."""
    scale = Scale(height=155, gender=Gender.FEMALE)
    result = scale.muscle_mass
    assert result == [32.9, 37.6]


# ===========================================================================
# muscle_mass — fallback (height < last threshold)
# ===========================================================================


def test_muscle_mass_fallback_very_short_male() -> None:
    """Male height below all thresholds must fall back to the last entry."""
    scale = Scale(height=50, gender=Gender.MALE)
    result = scale.muscle_mass
    assert result == [38.5, 46.6]


def test_muscle_mass_fallback_very_short_female() -> None:
    """Female height below all thresholds must fall back to the last entry."""
    scale = Scale(height=50, gender=Gender.FEMALE)
    result = scale.muscle_mass
    assert result == [29.1, 34.8]


def test_muscle_mass_fallback_height_zero() -> None:
    """Height=0 must always return a valid 2-element list via fallback."""
    scale = Scale(height=0, gender=Gender.MALE)
    result = scale.muscle_mass
    assert len(result) == 2


# ===========================================================================
# muscle_mass — cached_property
# ===========================================================================


def test_muscle_mass_is_cached() -> None:
    """muscle_mass result must be identical on repeated access (cached_property)."""
    scale = Scale(height=170, gender=Gender.MALE)
    result1 = scale.muscle_mass
    result2 = scale.muscle_mass
    assert result1 is result2

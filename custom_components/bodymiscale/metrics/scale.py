"""Body scale module."""

from functools import cached_property

from ..models import Gender


class Scale:
    """Scale implementation."""

    # Fat% table: [very low, low, normal, high] by age range / gender
    _FAT_SCALES: list[tuple[int, int, list[float], list[float]]] = [
        # (age_min, age_max, female_values, male_values)
        (0, 12, [12.0, 21.0, 30.0, 34.0], [7.0, 16.0, 25.0, 30.0]),
        (12, 14, [15.0, 24.0, 33.0, 37.0], [7.0, 16.0, 25.0, 30.0]),
        (14, 16, [18.0, 27.0, 36.0, 40.0], [7.0, 16.0, 25.0, 30.0]),
        (16, 18, [20.0, 28.0, 37.0, 41.0], [7.0, 16.0, 25.0, 30.0]),
        (18, 40, [21.0, 28.0, 35.0, 40.0], [11.0, 17.0, 22.0, 27.0]),
        (40, 60, [22.0, 29.0, 36.0, 41.0], [12.0, 18.0, 23.0, 28.0]),
        (60, 101, [23.0, 30.0, 37.0, 42.0], [14.0, 20.0, 25.0, 30.0]),
    ]

    # Muscle mass table: [low, normal] by height / gender
    _MUSCLE_SCALES: list[tuple[dict[Gender, int], list[float], list[float]]] = [
        ({Gender.MALE: 170, Gender.FEMALE: 160}, [36.5, 42.6], [49.4, 59.5]),
        ({Gender.MALE: 160, Gender.FEMALE: 150}, [32.9, 37.6], [44.0, 52.5]),
        ({Gender.MALE: 0, Gender.FEMALE: 0}, [29.1, 34.8], [38.5, 46.6]),
    ]

    def __init__(self, height: int, gender: Gender) -> None:
        """Initialize the scale with height and gender."""
        self._height = height
        self._gender = gender

    def get_fat_percentage(self, age: int) -> list[float]:
        """Return [very_low, low, normal, high] fat% thresholds for age/gender."""
        for age_min, age_max, female_vals, male_vals in self._FAT_SCALES:
            if age_min <= age < age_max:
                return female_vals if self._gender == Gender.FEMALE else male_vals
        # Fallback: age range 60-101 (>100 years)
        _, _, female_vals, male_vals = self._FAT_SCALES[-1]
        return female_vals if self._gender == Gender.FEMALE else male_vals

    @cached_property
    def muscle_mass(self) -> list[float]:
        """Return [low, normal] muscle mass thresholds for height/gender."""
        for min_heights, female_vals, male_vals in self._MUSCLE_SCALES:
            if self._height >= min_heights[self._gender]:
                return female_vals if self._gender == Gender.FEMALE else male_vals
        # Fallback: last entry (height 0)
        _, female_vals, male_vals = self._MUSCLE_SCALES[-1]
        return female_vals if self._gender == Gender.FEMALE else male_vals

"""Body scale module."""

from functools import cached_property

from ..models import Gender


class Scale:
    """Scale implementation."""

    def __init__(self, height: int, gender: Gender):
        self._height = height
        self._gender = gender

    def get_fat_percentage(self, age: int) -> list[float]:
        """Get fat percentage."""

        # The included tables where quite strange, maybe bogus, replaced them with better ones...
        scales: list[dict] = [
            {
                "min": 0,
                "max": 12,
                Gender.FEMALE: [12.0, 21.0, 30.0, 34.0],
                Gender.MALE: [7.0, 16.0, 25.0, 30.0],
            },
            {
                "min": 12,
                "max": 14,
                Gender.FEMALE: [15.0, 24.0, 33.0, 37.0],
                Gender.MALE: [7.0, 16.0, 25.0, 30.0],
            },
            {
                "min": 14,
                "max": 16,
                Gender.FEMALE: [18.0, 27.0, 36.0, 40.0],
                Gender.MALE: [7.0, 16.0, 25.0, 30.0],
            },
            {
                "min": 16,
                "max": 18,
                Gender.FEMALE: [20.0, 28.0, 37.0, 41.0],
                Gender.MALE: [7.0, 16.0, 25.0, 30.0],
            },
            {
                "min": 18,
                "max": 40,
                Gender.FEMALE: [21.0, 28.0, 35.0, 40.0],
                Gender.MALE: [11.0, 17.0, 22.0, 27.0],
            },
            {
                "min": 40,
                "max": 60,
                Gender.FEMALE: [22.0, 29.0, 36.0, 41.0],
                Gender.MALE: [12.0, 18.0, 23.0, 28.0],
            },
            {
                "min": 60,
                "max": 100,
                Gender.FEMALE: [23.0, 30.0, 37.0, 42.0],
                Gender.MALE: [14.0, 20.0, 25.0, 30.0],
            },
        ]

        for scale in scales:
            if scale["min"] <= age < scale["max"]:
                return scale[self._gender]  # type: ignore

        # will never happen but mypy required it
        raise NotImplementedError

    @cached_property
    def muscle_mass(self) -> list[float]:
        """Get muscle mass."""
        scales: list[dict] = [
            {
                "min": {Gender.MALE: 170, Gender.FEMALE: 160},
                Gender.FEMALE: [36.5, 42.6],
                Gender.MALE: [49.4, 59.5],
            },
            {
                "min": {Gender.MALE: 160, Gender.FEMALE: 150},
                Gender.FEMALE: [32.9, 37.6],
                Gender.MALE: [44.0, 52.5],
            },
            {
                "min": {Gender.MALE: 0, Gender.FEMALE: 0},
                Gender.FEMALE: [29.1, 34.8],
                Gender.MALE: [38.5, 46.6],
            },
        ]

        for scale in scales:
            if self._height >= scale["min"][self._gender]:
                return scale[self._gender]  # type: ignore

        # will never happen but mypy required it
        raise NotImplementedError

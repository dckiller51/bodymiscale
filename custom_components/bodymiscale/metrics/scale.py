"""Body scale module."""
from functools import cached_property

from ..models import Gender


class Scale:
    """Scale implementation."""

    def __init__(self, height: int, gender: Gender):
        self._height = height
        self._gender = gender

    @property
    def bmi(self) -> list[float]:
        """Get BMI."""
        # Amazfit/new mi fit
        # return [18.5, 24, 28]
        # Old mi fit // amazfit for body figure
        return [18.5, 25.0, 28.0, 32.0]

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

    @property
    def water_percentage(self) -> list[float]:
        """Get water percentage."""
        if self._gender == Gender.MALE:
            return [55.0, 65.1]

        return [45.0, 60.1]

    @property
    def visceral_fat(self) -> list[float]:
        """Get visceral fat."""
        return [10.0, 15.0]

    def get_bone_mass(self, weight: float) -> list[float]:
        """Get bone mass."""
        scales = [
            {
                Gender.MALE: {"min": 75.0, "scale": [2.0, 4.2]},
                Gender.FEMALE: {"min": 60.0, "scale": [1.8, 3.9]},
            },
            {
                Gender.MALE: {"min": 60.0, "scale": [1.9, 4.1]},
                Gender.FEMALE: {"min": 45.0, "scale": [1.5, 3.8]},
            },
            {
                Gender.MALE: {"min": 0.0, "scale": [1.6, 3.9]},
                Gender.FEMALE: {"min": 0.0, "scale": [1.3, 3.6]},
            },
        ]

        for scale in scales:
            if weight >= scale[self._gender]["min"]:  # type: ignore
                return scale[self._gender]["scale"]  # type: ignore

        # will never happen but mypy required it
        raise NotImplementedError

    def get_bmr(self, age: int, weight: float) -> float:
        """Get BMR."""
        coefficients = {
            Gender.MALE: {30: 21.6, 50: 20.07, 100: 19.35},
            Gender.FEMALE: {30: 21.24, 50: 19.53, 100: 18.63},
        }

        for c_age, coefficient in coefficients[self._gender].items():
            if age < c_age:
                return weight * coefficient

        # will never happen but mypy required it
        raise NotImplementedError

    @property
    def protein_percentage(self) -> list[float]:
        """Get protein percentage."""
        return [16, 20]

    @cached_property
    def ideal_weight(self) -> list[float]:
        """Get ideal weight scale (BMI scale converted to weights)."""
        scales = []
        for scale in self.bmi:
            scales.append((scale * self._height) * self._height / 10000)
        return scales

    @property
    def body_score(self) -> list[float]:
        """Get body score."""
        # very bad, bad, normal, good, better
        return [50.0, 60.0, 80.0, 90.0]

    @property
    def body_type(self) -> list[str]:
        """Get body type."""
        return [
            "obese",
            "overweight",
            "thick-set",
            "lack-exercise",
            "balanced",
            "balanced-muscular",
            "skinny",
            "balanced-skinny",
            "skinny-muscular",
        ]

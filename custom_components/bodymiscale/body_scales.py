from custom_components.bodymiscale.models import Gender


class BodyScale:
    def __init__(self, age: int, height: int, gender: Gender, weight: float):
        self._age = age
        self._height = height
        self._gender = gender
        self._weight = weight

    @property
    def bmi(self):
        """Get BMI."""
        # Amazfit/new mi fit
        # return [18.5, 24, 28]
        # Old mi fit // amazfit for body figure
        return [18.5, 25.0, 28.0, 32.0]

    @property
    def fat_percentage(self):
        """Get fat percentage."""

        # The included tables where quite strange, maybe bogus, replaced them with better ones...
        scales = [
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
            if scale["min"] <= self._age < scale["max"]:
                return scale[self._gender]

    @property
    def muscle_mass(self):
        scales = [
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
                return scale[self._gender]

    @property
    def water_percentage(self):
        if self._gender == Gender.MALE:
            return [55.0, 65.1]
        else:
            return [45.0, 60.1]

    @property
    def visceral_fat(self):
        # Actually the same in mi fit/amazfit and holtek's sdk
        return [10.0, 15.0]

    @property
    def bone_mass(self):
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
            if self._weight >= scale[self._gender]["min"]:
                return scale[self._gender]["scale"]

    @property
    def bmr(self):
        coefficients = {
            Gender.MALE: {30: 21.6, 50: 20.07, 100: 19.35},
            Gender.FEMALE: {30: 21.24, 50: 19.53, 100: 18.63},
        }

        for age, coefficient in coefficients[self._gender].items():
            if self._age < age:
                return [self._weight * coefficient]

    @property
    def protein_percentage(self):
        # Actually the same in mi fit and holtek's sdk
        return [16, 20]

    @property
    def ideal_weight(self):
        """Get ideal weight scale (BMI scale converted to weights)."""
        scale = []
        for bmiScale in self.bmi:
            scale.append((bmiScale * self._height) * self._height / 10000)
        return scale

    @property
    def body_score(self):
        # very bad, bad, normal, good, better
        return [50.0, 60.0, 80.0, 90.0]

    @property
    def body_type(self):
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

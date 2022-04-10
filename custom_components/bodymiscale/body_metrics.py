"""Body metrics module."""
from functools import cached_property

from .body_scales import BodyScale
from .const import (
    CONSTRAINT_HEIGHT_MAX,
    CONSTRAINT_IMPEDANCE_MAX,
    CONSTRAINT_WEIGHT_MAX,
    CONSTRAINT_WEIGHT_MIN,
)
from .models import Gender


def _check_value_constraints(value: float, minimum: float, maximum: float) -> float:
    """Set the value to a boundary if it overflows."""
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


class BodyMetrics:
    """Body metrics implementation."""

    def __init__(self, weight: float, height: int, age: int, gender: Gender):
        # Check for potential out of boundaries
        if height > CONSTRAINT_HEIGHT_MAX:
            raise Exception(f"Height is too high (limit: {CONSTRAINT_HEIGHT_MAX}cm)")
        if not (CONSTRAINT_WEIGHT_MIN < weight < CONSTRAINT_WEIGHT_MAX):
            raise Exception(
                f"Weight not within {CONSTRAINT_WEIGHT_MIN} and {CONSTRAINT_WEIGHT_MAX} kg"
            )
        if age > 99:
            raise Exception("Age is too high (limit >99 years)")

        self._weight = weight
        self._height = height
        self._age = age
        self._gender = gender

    @property
    def weight(self) -> float:
        """Get weight."""
        return self._weight

    @property
    def height(self) -> int:
        """Get height."""
        return self._height

    @property
    def age(self) -> int:
        """Get age."""
        return self._age

    @property
    def gender(self) -> Gender:
        """Get gender."""
        return self._gender

    @cached_property
    def bmi(self) -> float:
        """Get MBI."""
        bmi = self._weight / ((self._height / 100) * (self._height / 100))
        return _check_value_constraints(bmi, 10, 90)

    @cached_property
    def bmr(self) -> float:
        """Get BMR."""
        if self._gender == Gender.FEMALE:
            bmr = 864.6 + self._weight * 10.2036
            bmr -= self._height * 0.39336
            bmr -= self._age * 6.204

            if bmr > 2996:
                bmr = 5000
        else:
            bmr = 877.8 + self._weight * 14.916
            bmr -= self._height * 0.726
            bmr -= self._age * 8.976

            if bmr > 2322:
                bmr = 5000

        return _check_value_constraints(bmr, 500, 5000)

    @cached_property
    def visceral_fat(self) -> float:
        """Get Visceral Fat."""
        if self._gender == Gender.FEMALE:
            if self._weight > (13 - (self._height * 0.5)) * -1:
                subsubcalc = (
                    (self._height * 1.45) + (self._height * 0.1158) * self._height
                ) - 120
                subcalc = self._weight * 500 / subsubcalc
                vfal = (subcalc - 6) + (self._age * 0.07)
            else:
                subcalc = 0.691 + (self._height * -0.0024) + (self._height * -0.0024)
                vfal = (
                    (((self._height * 0.027) - (subcalc * self._weight)) * -1)
                    + (self._age * 0.07)
                    - self._age
                )
        else:
            if self._height < self._weight * 1.6:
                subcalc = (
                    (self._height * 0.4) - (self._height * (self._height * 0.0826))
                ) * -1
                vfal = (
                    ((self._weight * 305) / (subcalc + 48)) - 2.9 + (self._age * 0.15)
                )
            else:
                subcalc = 0.765 + self._height * -0.0015
                vfal = (
                    (((self._height * 0.143) - (self._weight * subcalc)) * -1)
                    + (self._age * 0.15)
                    - 5.0
                )

        return _check_value_constraints(vfal, 1, 50)

    @cached_property
    def ideal_weight(self) -> float:
        """Get ideal weight (just doing a reverse BMI, should be something better)."""
        # Uses mi fit algorithm (or holtek's one)
        if self._gender == Gender.FEMALE:
            return (self._height - 70) * 0.6
        return (self._height - 80) * 0.7

    @property
    def bmi_label(self) -> str:  # pylint: disable=too-many-return-statements
        """Get BMI label."""
        bmi = self.bmi
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


class BodyMetricsImpedance(BodyMetrics):
    """body metrics with impedance implementation."""

    def __init__(  # pylint: disable=too-many-arguments
        self, weight: float, height: int, age: int, gender: Gender, impedance: int
    ):
        super().__init__(weight, height, age, gender)
        if impedance > CONSTRAINT_IMPEDANCE_MAX:
            raise Exception(
                f"Impedance is too high (limit >{CONSTRAINT_IMPEDANCE_MAX}ohm)"
            )
        self._impedance = impedance
        self._scale = BodyScale(age, height, gender, weight)

    @property
    def scale(self) -> BodyScale:
        """Get body scale."""
        return self._scale

    @cached_property
    def lbm_coefficient(self) -> float:
        """Get LBM coefficient (with impedance)."""
        lbm = (self._height * 9.058 / 100) * (self._height / 100)
        lbm += self._weight * 0.32 + 12.226
        lbm -= self._impedance * 0.0068
        lbm -= self._age * 0.0542

        return lbm

    @cached_property
    def fat_percentage(self) -> float:
        """Get fat percentage."""
        # Set a constant to remove from LBM
        if self._gender == "female":
            const = 9.25 if self._age <= 49 else 7.25
        else:
            const = 0.8

        # Calculate body fat percentage
        coefficient = 1.0
        if self._gender == "female":
            if self._weight > 60:
                coefficient = 0.96
            elif self._weight < 50:
                coefficient = 1.02

            if self._height > 160 and (self._weight < 50 or self._weight > 60):
                coefficient *= 1.03
        elif self._weight < 61:  # gender = male
            coefficient = 0.98

        fat_percentage = (
            1.0 - (((self.lbm_coefficient - const) * coefficient) / self._weight)
        ) * 100

        # Capping body fat percentage
        if fat_percentage > 63:
            fat_percentage = 75
        return _check_value_constraints(fat_percentage, 5, 75)

    @cached_property
    def water_percentage(self) -> float:
        """Get water percentage."""
        water_percentage = (100 - self.fat_percentage) * 0.7

        coefficient = 1.02 if water_percentage <= 50 else 0.98

        # Capping water percentage
        if water_percentage * coefficient >= 65:
            water_percentage = 75
        return _check_value_constraints(water_percentage * coefficient, 35, 75)

    @cached_property
    def bone_mass(self) -> float:
        """Get bone mass."""
        if self._gender == Gender.FEMALE:
            base = 0.245691014
        else:
            base = 0.18016894

        bone_mass = (base - (self.lbm_coefficient * 0.05158)) * -1

        if bone_mass > 2.2:
            bone_mass += 0.1
        else:
            bone_mass -= 0.1

        # Capping bone mass
        if self._gender == Gender.FEMALE and bone_mass > 5.1:
            bone_mass = 8
        elif self._gender == Gender.MALE and bone_mass > 5.2:
            bone_mass = 8

        return _check_value_constraints(bone_mass, 0.5, 8)

    @cached_property
    def muscle_mass(self) -> float:
        """Get muscle mass."""
        muscle_mass = (
            self._weight
            - ((self.fat_percentage * 0.01) * self._weight)
            - self.bone_mass
        )

        # Capping muscle mass
        if self._gender == Gender.FEMALE and muscle_mass >= 84:
            muscle_mass = 120
        elif self._gender == Gender.MALE and muscle_mass >= 93.5:
            muscle_mass = 120

        return _check_value_constraints(muscle_mass, 10, 120)

    @cached_property
    def metabolic_age(self) -> float:
        """Get metabolic age."""
        if self._gender == Gender.FEMALE:
            metabolic_age = (
                (self._height * -1.1165)
                + (self._weight * 1.5784)
                + (self._age * 0.4615)
                + (self._impedance * 0.0415)
                + 83.2548
            )
        else:
            metabolic_age = (
                (self._height * -0.7471)
                + (self._weight * 0.9161)
                + (self._age * 0.4184)
                + (self._impedance * 0.0517)
                + 54.2267
            )
        return _check_value_constraints(metabolic_age, 15, 80)

    @cached_property
    def fat_mass_to_ideal(self) -> float:
        """Get missig mass to ideal weight."""
        return (self._weight * (self._scale.fat_percentage[2] / 100)) - (
            self._weight * (self.fat_percentage / 100)
        )

    @cached_property
    def protein_percentage(self) -> float:
        """Get protetin percentage (warn: guessed formula)."""
        # Use original algorithm from mi fit (or legacy guess one)
        protein_percentage = (self.muscle_mass / self._weight) * 100
        protein_percentage -= self.water_percentage

        return _check_value_constraints(protein_percentage, 5, 32)

    @cached_property
    def body_type(self) -> str:
        """Get body type."""
        types = [
            "Obese",
            "Overweight",
            "Thick-set",
            "Lack-exercise",
            "Balanced",
            "Balanced-muscular",
            "Skinny",
            "Balanced-skinny",
            "Skinny-muscular",
        ]

        if self.fat_percentage > self._scale.fat_percentage[2]:
            factor = 0
        elif self.fat_percentage < self._scale.fat_percentage[1]:
            factor = 2
        else:
            factor = 1

        if self.muscle_mass > self._scale.muscle_mass[1]:
            type_num = 2 + (factor * 3)
        if self.muscle_mass < self._scale.muscle_mass[0]:
            type_num = factor * 3

        type_num = 1 + (factor * 3)
        return types[type_num]

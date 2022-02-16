# Reverse engineered from amazfit's app (also known as Mi Fit)
from . import BodyMetricsImpedance
from .models import Gender


def _get_malus(data, min_data, max_data, max_malus, min_malus):
    result = ((data - max_data) / (min_data - max_data)) * float(max_malus - min_malus)
    if result >= 0.0:
        return result
    return 0.0


class BodyScore:
    def __init__(self, metrics: BodyMetricsImpedance):
        self._metrics = metrics

        # Store calculation result in variable to avoid recalculation
        self.__body_score = None

    @property
    def body_score(self):
        if self.__body_score is not None:
            return self.__body_score

        score = 100
        score -= self._calculate_bmi_deduct_score()
        score -= self._calculate_body_fat_deduct_score()
        score -= self._calculate_muscle_deduct_score()
        score -= self._calculate_water_deduct_score()
        score -= self._calculate_body_visceral_deduct_score()
        score -= self._calculate_bone_deduct_score()
        score -= self._calculate_basal_metabolism_deduct_score()
        if self._metrics.protein_percentage():
            score -= self._calculate_protein_deduct_score()

        self.__body_score = score
        return self.__body_score

    def _calculate_bmi_deduct_score(self):
        if not self._metrics.height >= 90:
            # "BMI is not reasonable
            return 0.0

        bmi_low = 15.0
        bmi_very_low = 14.0
        bmi_normal = 18.5
        bmi_overweight = 28.0
        bmi_obese = 32.0
        fat_scale = self._metrics.scale.fat_percentage

        # Perfect range (bmi >= 18.5 and fat_percentage not high for adults, bmi >= 15.0 for kids
        if self._metrics.fat_percentage < fat_scale[2] and (
            (self._metrics.bmi >= 18.5 and self._metrics.age >= 18)
            or self._metrics.bmi >= bmi_very_low
            and self._metrics.age < 18
        ):
            return 0.0

        # Extremely skinny (bmi < 14)
        elif self._metrics.bmi <= bmi_very_low:
            return 30.0
        # Too skinny (bmi between 14 and 15)
        if self._metrics.bmi < bmi_low:
            return _get_malus(self._metrics.bmi, bmi_very_low, bmi_low, 30, 15) + 15.0
        # Skinny (for adults, between 15 and 18.5)
        if self._metrics.bmi < bmi_normal and self._metrics.age >= 18:
            return _get_malus(self._metrics.bmi, 15.0, 18.5, 15, 5) + 5.0

        # Normal or high bmi but too much bodyfat
        if (
            self._metrics.fat_percentage >= fat_scale[2]
            and (self._metrics.bmi >= bmi_low and self._metrics.age < 18)
            or (self._metrics.bmi >= bmi_normal and self._metrics.age >= 18)
        ):
            # Obese
            if self._metrics.bmi >= bmi_obese:
                return 10.0
            # Overweight
            if self._metrics.bmi > bmi_overweight:
                return _get_malus(self._metrics.bmi, 28.0, 25.0, 5, 10) + 5.0

        return 0.0

    def _calculate_body_fat_deduct_score(self):
        scale = self._metrics.scale.fat_percentage

        if self._metrics.gender == Gender.MALE:
            best = scale[2] - 3.0
        else:
            best = scale[2] - 2.0

        # Slightly low in fat or low part or normal fat
        if scale[0] <= self._metrics.fat_percentage < best:
            return 0.0
        if self._metrics.fat_percentage >= scale[3]:
            return 20.0

        # Sightly high body fat
        if self._metrics.fat_percentage < scale[3]:
            return (
                _get_malus(self._metrics.fat_percentage, scale[3], scale[2], 20, 10)
                + 10.0
            )

        # High part of normal fat
        if self._metrics.fat_percentage <= scale[2]:
            return _get_malus(self._metrics.fat_percentage, scale[2], best, 3, 9) + 3.0

        # Very low in fat
        if self._metrics.fat_percentage < scale[0]:
            return _get_malus(self._metrics.fat_percentage, 1.0, scale[0], 3, 10) + 3.0

        return 0.0

    def _calculate_muscle_deduct_score(self):
        scale = self._metrics.scale.muscle_mass

        # For some reason, there's code to return self.calculate(muscle, normal[0], normal[0]+2.0, 3, 5) + 3.0
        # if your muscle is between normal[0] and normal[0] + 2.0, but it's overwritten with 0.0 before return
        if self._metrics.muscle_mass >= scale[0]:
            return 0.0
        if self._metrics.muscle_mass < (scale[0] - 5.0):
            return 10.0
        return (
            _get_malus(self._metrics.muscle_mass, scale[0] - 5.0, scale[0], 10, 5) + 5.0
        )

    def _calculate_water_deduct_score(self):
        # No malus = normal or good; maximum malus (10.0) = less than normal-5.0;
        # malus = between 5 and 10, on your water being between normal-5.0 and normal
        scale = self._metrics.scale.water_percentage

        if self._metrics.water_percentage >= scale[0]:
            return 0.0
        if self._metrics.water_percentage <= (scale[0] - 5.0):
            return 10.0
        return (
            _get_malus(self._metrics.water_percentage, scale[0] - 5.0, scale[0], 10, 5)
            + 5.0
        )

    def _calculate_body_visceral_deduct_score(self):
        # No malus = normal; maximum malus (15.0) = very high; malus = between 10 and 15
        # with your visceral fat in your high range
        scale = self._metrics.scale.visceral_fat

        if self._metrics.visceral_fat < scale[0]:
            # For some reason, the original app would try to
            # return 3.0 if vfat == 8 and 5.0 if vfat == 9
            # but i's overwritten with 0.0 anyway before return
            return 0.0
        if self._metrics.visceral_fat >= scale[1]:
            return 15.0
        return _get_malus(self._metrics.visceral_fat, scale[1], scale[0], 15, 10) + 10.0

    def _calculate_bone_deduct_score(self):
        scale = self._metrics.scale.bone_mass

        if self._metrics.bone_mass >= scale[0]:
            return 0.0
        if self._metrics.bone_mass <= (scale[0] - 0.3):
            return 10.0
        return (
            _get_malus(self._metrics.bone_mass, scale[0] - 0.3, scale[0], 10, 5) + 5.0
        )

    def _calculate_basal_metabolism_deduct_score(self):
        # Get normal BMR
        normal = self._metrics.scale.bmr()[0]

        if self._metrics.bmr >= normal:
            return 0.0
        if self._metrics.bmr <= (normal - 300):
            return 6.0
        # It's really + 5.0 in the app, but it's probably a mistake, should be 3.0
        return _get_malus(self._metrics.bmr, normal - 300, normal, 6, 3) + 5.0

    def _calculate_protein_deduct_score(self):
        # low: 10,16; normal: 16,17
        # Check limits
        if self._metrics.protein_percentage > 17.0:
            return 0.0
        if self._metrics.protein_percentage < 10.0:
            return 10.0

        # Return values for low proteins or normal proteins
        if self._metrics.protein_percentage <= 16.0:
            return _get_malus(self._metrics.protein_percentage, 10.0, 16.0, 10, 5) + 5.0
        elif self._metrics.protein_percentage <= 17.0:
            return _get_malus(self._metrics.protein_percentage, 16.0, 17.0, 5, 3) + 3.0

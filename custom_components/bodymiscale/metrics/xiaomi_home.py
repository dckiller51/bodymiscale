"""Xiaomi Home (S400) calculation mode — the scale's own firmware formulas.

Body composition engine recovered by RX14 from the Xiaomi Body Composition
Scale S400 Pro firmware (image 2.1.1_0063, xiaomi.scales.ms110), contributed
under the Apache-2.0 license in
https://github.com/dckiller51/bodymiscale/issues/474.

Coefficients are byte-exact from the binary. RX14 verified every function
against the unmodified firmware running under qemu (3218 pathological inputs,
ages 6-90, zero divergences). The S400 shows identical app values, and the
weighings reported in #349 are reproduced (see
``tests/components/bodymiscale/test_xiaomi_home.py``).

Inputs: height (cm), weight (kg), age (years), sex, and both impedances.
``z50`` is the 50 kHz impedance (always the larger value) and ``z250`` the
250 kHz one. Body fat, and therefore lean mass and BMR, use ``z50`` only.

The firmware rounds intermediate values (fat mass, lean mass, bone, muscle,
the water/protein split chain) to 0.1; those roundings are part of the
algorithm and are kept. The public functions return the values as displayed
by the scale and the app (0.1, or integers for BMR, visceral fat and age).

Known gap: for the values sent to the app, the scale smooths the impedances
with the profile's previous measurement. Home Assistant receives the raw
impedances, so values can differ slightly from the app after several
weigh-ins close together.
"""

from collections.abc import Mapping
from math import ceil, floor, sqrt

from ..models import Gender

# Body fat coefficients: height, weight, age, z50, constant.
_BODY_FAT_COEFFS: Mapping[Gender, tuple[float, float, float, float, float]] = {
    Gender.FEMALE: (-0.3332, 0.7509, 0.0196, 0.0072, 22.7193),
    Gender.MALE: (-0.3315, 0.6216, 0.0183, 0.0085, 22.554),
}

# Regression coefficients (times 1e6): h, w, z50, z250, √h, √w, √z50, √z250, constant.
_WATER = (
    2935892,
    149065,
    -468183,
    589094,
    -63286091,
    -778045,
    23941529,
    -29784715,
    424044966,
)
_BONE = (
    118543,
    26106,
    -45544,
    48749,
    -2271994,
    -155662,
    2151182,
    -2248649,
    12272558,
)
_SOLIDS = (
    160696,
    28769,
    -60093,
    65412,
    -3163648,
    -169504,
    2860478,
    -3043837,
    18045896,
)
_SKELETAL_MUSCLE = (
    2475795,
    118673,
    -457174,
    556218,
    -53616294,
    -574893,
    23989719,
    -28648257,
    352065003,
)
_VISCERAL_FAT = (
    -1849883,
    424124,
    366784,
    -455322,
    39648934,
    -359012,
    -20035428,
    24213934,
    -265509571,
)

# Reference BMI (mid value) by sex for ages 6..17, then adults.
_BMI_MID: Mapping[Gender, tuple[float, ...]] = {
    Gender.FEMALE: (
        14.95,
        15.15,
        15.4,
        15.85,
        16.35,
        17.0,
        17.75,
        18.5,
        19.25,
        19.9,
        20.3,
        20.65,
        21.0,
    ),
    Gender.MALE: (
        15.0,
        15.2,
        15.45,
        15.8,
        16.25,
        16.75,
        17.35,
        18.0,
        18.75,
        19.5,
        20.2,
        20.75,
        22.0,
    ),
}
# Reference body fat (mid value): fixed for men; ages 6..13 then adult for women.
_BFP_MID_MALE = 15.0
_BFP_MID_FEMALE = (16.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 22.0)
_BFP_MID_FEMALE_ADULT = 23.0
# Body age weights for (weight - standard weight), (BMR - reference BMR),
# (fat% - reference fat%) and (muscle% - reference muscle%).
_BODY_AGE_ADULT = (-1.48615435, 0.129089458, 0.591458258, -0.000405611446)
_BODY_AGE_YOUTH = (-1.0136192, 0.107155831, 0.277336024, -0.0349702346)


def _round_01(x: float) -> float:
    """Round to 0.1, half away from zero, like the firmware."""
    return (floor(x * 10.0 + 0.5) if x >= 0 else ceil(x * 10.0 - 0.5)) / 10.0


def _regression(
    k: tuple[float, ...], h: float, w: float, z50: float, z250: float
) -> float:
    return (
        k[0] * h
        + k[1] * w
        + k[2] * z50
        + k[3] * z250
        + k[4] * sqrt(h)
        + k[5] * sqrt(w)
        + k[6] * sqrt(z50)
        + k[7] * sqrt(z250)
        + k[8]
    ) / 1e6


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _bmr(lbm: float) -> int:
    return int(_clamp(21.6 * lbm + 370.0 + 0.5, 400.0, 3500.0))


def body_fat(gender: Gender, h: float, w: float, age: float, z50: float) -> float:
    """Body fat (%), from the 50 kHz impedance only, clamped to 3-55 %."""
    c = _BODY_FAT_COEFFS[gender]
    raw = (c[0] * h + c[1] * w + c[2] * age + c[3] * z50 + c[4]) / w * 100.0
    return _clamp(_round_01(raw), 3.0, 55.0)


def lean_body_mass(gender: Gender, h: float, w: float, age: float, z50: float) -> float:
    """Lean body mass (kg) = weight − fat mass, both rounded to 0.1 kg."""
    fat = body_fat(gender, h, w, age, z50)
    return _round_01(w - _round_01(fat / 100.0 * w))


def _water_protein(
    gender: Gender, h: float, w: float, age: float, z50: float, z250: float
) -> tuple[float, float]:
    """Firmware split chain, returning (water mass kg, protein %).

    Water's first-pass percentage is clamped and turned back into a mass,
    protein % is rounded and clamped, and the final water mass is the
    remainder of lean mass − solids − protein mass.
    """
    lbm = lean_body_mass(gender, h, w, age, z50)
    solids = _round_01(_regression(_SOLIDS, h, w, z50, z250))
    water = _round_01(_round_01(_regression(_WATER, h, w, z50, z250)) + 3.0 * w / 100.0)
    water_pct = _clamp(_round_01(water / w * 100.0), 20.0, 85.0)
    water = _round_01(water_pct * w / 100.0)
    protein_pct = _clamp(_round_01((lbm - solids - water) / w * 100.0), 5.0, 32.0)
    protein = _round_01(protein_pct * w / 100.0)
    return lbm - solids - protein, protein_pct


def water_percentage(
    gender: Gender, h: float, w: float, age: float, z50: float, z250: float
) -> float:
    """Total body water (% of weight)."""
    water, _ = _water_protein(gender, h, w, age, z50, z250)
    return _round_01(_round_01(water) / w * 100.0)


def protein_percentage(
    gender: Gender, h: float, w: float, age: float, z50: float, z250: float
) -> float:
    """Protein (% of weight), clamped to 5-32 %."""
    _, protein_pct = _water_protein(gender, h, w, age, z50, z250)
    return protein_pct


def bone_mass(h: float, w: float, z50: float, z250: float) -> float:
    """Bone mass (kg); the firmware stores 0 below 0.3 kg and caps at 5 kg."""
    bone = _round_01(_regression(_BONE, h, w, z50, z250))
    return 0.0 if bone < 0.3 else min(5.0, bone)


def muscle_mass(
    gender: Gender, h: float, w: float, age: float, z50: float, z250: float
) -> float:
    """Muscle mass (kg) = lean mass − bone mass, clamped to 7-141.5 kg."""
    muscle = lean_body_mass(gender, h, w, age, z50) - bone_mass(h, w, z50, z250)
    return _clamp(_round_01(muscle), 7.0, 141.5)


def skeletal_muscle_mass(
    gender: Gender, h: float, w: float, age: float, z50: float, z250: float
) -> float:
    """Skeletal muscle mass (kg), kept within 45-70 % of the muscle mass."""
    smm = _round_01(_regression(_SKELETAL_MUSCLE, h, w, z50, z250))
    muscle = muscle_mass(gender, h, w, age, z50, z250)
    return _round_01(_clamp(smm, 0.45 * muscle, 0.70 * muscle))


def visceral_fat(h: float, w: float, z50: float, z250: float) -> float:
    """Visceral fat level (1-59)."""
    level = _clamp(_regression(_VISCERAL_FAT, h, w, z50, z250), 1.0, 59.0)
    return float(int(level + 0.5))


def basal_metabolism(
    gender: Gender, h: float, w: float, age: float, z50: float
) -> float:
    """Basal metabolic rate (kcal/day) from the stored lean body mass."""
    return float(_bmr(lean_body_mass(gender, h, w, age, z50)))


def metabolic_age(
    gender: Gender, h: float, w: float, age: float, z50: float, z250: float
) -> float:
    """Metabolic age, shown as "body age" in Xiaomi Home.

    Compares weight, BMR, body fat and muscle with the reference values of a
    person of the same sex, age and height. Adults get 18-100 years; under
    18 the body age stays within one year of the real age (6-17).
    """
    age_int = int(age)
    bmi_mid = _BMI_MID[gender][min(max(age_int, 6), 18) - 6]
    if gender == Gender.MALE:
        bfp_mid = _BFP_MID_MALE
    elif age_int >= 14:
        bfp_mid = _BFP_MID_FEMALE_ADULT
    else:
        bfp_mid = _BFP_MID_FEMALE[min(max(age_int, 6), 13) - 6]

    standard_weight = _round_01(bmi_mid * h * h / 10000.0)
    reference_bmr = _bmr(_round_01((100 - bfp_mid) * standard_weight / 100.0))
    reference_muscle_pct = _round_01((100 - bfp_mid) * 0.944)
    muscle_pct = _round_01(muscle_mass(gender, h, w, age, z50, z250) / w * 100.0)

    c_w, c_bmr, c_fat, c_muscle = _BODY_AGE_YOUTH if age_int < 18 else _BODY_AGE_ADULT
    score = (
        (w - standard_weight) * c_w
        + (basal_metabolism(gender, h, w, age, z50) - reference_bmr) * c_bmr
        + (body_fat(gender, h, w, age, z50) - bfp_mid) * c_fat
        + (muscle_pct - reference_muscle_pct) * c_muscle
    ) / 2.5

    if age_int < 18:
        shift = -1 if score < -2 else (1 if score >= 2 else 0)
        return float(_clamp(age_int + shift, 6, 17))
    if score < -10:
        shift = -10
    elif score >= 2:
        shift = 2
    elif score >= 0:
        shift = int(score) + 1
    else:
        shift = int(score)
    return float(_clamp(age_int - shift - 4, 18, 100))

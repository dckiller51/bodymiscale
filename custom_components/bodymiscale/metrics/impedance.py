"""Metrics module — impedance-based calculations.

Three distinct modes, each with its own formulas:

  XIAOMI (standard, mono-frequency)
    Exact copy of the Zepp Life / Mi Fit algorithm.
    Formulas identical to the official Xiaomi application.
    Impedance: single frequency (single sensor).

  SCIENCE (standard, mono-frequency)
    Based on WHO recommendations and validated equations:
      - LBM    : Janmahasatian et al. 2005 (J Clin Pharm Ther)
      - Fat%   : direct 2-compartment method (Siri 1956)
      - Water  : Pace constant 1963 (73% lean mass)
      - BMR    : Mifflin–St Jeor 1990 (recommended AND/WHO)
      - Age    : ratio fat%/target fat% WHO by age/gender group

  S400 (dual-frequency, 50 kHz + 250 kHz)
    Specific formulas for dual-frequency scales (Xiaomi S400).
      - LBM    : Lukaski et al. 1985, coefficient recalibrated for
                 4-electrode scales with Z ~300-600 Ω at 50 kHz (vs ~100-200 Ω
                 for standard Xiaomi floor scales).
                 Coefficient adjusted based on S400 manufacturer data:
                 male 62 years, 170 cm, 76.9 kg, Z_lf=387 → LBM=58.0 kg.
      - Fat%   : direct 2-compartment method
      - Water  : blend of Pace constant (fat-free method) and Kushner 1992
                 BIA equation using Z_hf (250 kHz), which penetrates cell
                 membranes and estimates Total Body Water (TBW = ECW + ICW).
                 TBW = 0.5813 × (H²/Z_hf) + 0.065×W + 0.04
                 water% = (Pace% + TBW%) / 2
                 Calibrated on reference point: water% = 55.8% ✓
      - BMR    : Harris-Benedict revised (Roza & Shizgal 1984)
      - Visceral : S400 formula (divisor ×2 compared to standard Xiaomi)
      - Age    : ratio fat%/target fat% by age/gender group
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from homeassistant.helpers.typing import StateType

from ..const import (
    ALGO_SCIENCE,
    ALGO_XIAOMI,
    CONF_CALCULATION_MODE,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_IMPEDANCE_MODE,
    CONF_SCALE,
    IMPEDANCE_MODE_DUAL,
)
from ..models import Gender, Metric
from ..util import check_value_constraints, to_float

# ─────────────────────────────────────────────────────────────────────────────
# Helper : effective impedance according to hardware mode
# ─────────────────────────────────────────────────────────────────────────────


def _is_dual(config: Mapping[str, Any]) -> bool:
    return config.get(CONF_IMPEDANCE_MODE) == IMPEDANCE_MODE_DUAL


def _get_z_lf(metrics: Mapping[Metric, StateType | datetime]) -> float:
    """Impedance 50 kHz (low frequency) in dual mode."""
    return to_float(metrics.get(Metric.IMPEDANCE_LOW))


def _get_z_hf(metrics: Mapping[Metric, StateType | datetime]) -> float:
    """Impedance 250 kHz (high frequency) in dual mode.

    Used in get_water_percentage (S400 mode) via the Kushner 1992 BIA equation
    to estimate Total Body Water (TBW). At 250 kHz the current penetrates cell
    membranes, giving access to intracellular water (ICW) in addition to
    extracellular water (ECW), yielding a more accurate TBW estimate than
    the Pace fat-free constant alone.
    """
    return to_float(metrics.get(Metric.IMPEDANCE_HIGH))


def _get_z_std(metrics: Mapping[Metric, StateType | datetime]) -> float:
    """Single impedance in standard mode."""
    return to_float(metrics.get(Metric.IMPEDANCE))


# ─────────────────────────────────────────────────────────────────────────────
# LBM — Lean Body Mass
# ─────────────────────────────────────────────────────────────────────────────


def get_lbm(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate Lean Body Mass.

    XIAOMI / SCIENCE (single-frequency):
        Original Xiaomi formula (same as Zepp Life).
        LBM = (H × 9.058/100) × (H/100) + W × 0.32 + 12.226 − Z × 0.0068 − A × 0.0542

    S400 (dual 50 kHz + 250 kHz):
        Lukaski 1985 with coefficient recalibrated for 4-electrode scales.
        RI_lf = H² / Z_lf
        Male   : LBM = 0.7909 × RI_lf + 0.116 × W − 0.096 × A − 4.03
        Female : LBM = 0.8014 × RI_lf + 0.102 × W − 0.071 × A − 4.85
    """
    h = to_float(config.get(CONF_HEIGHT))
    w = to_float(metrics.get(Metric.WEIGHT))
    a = to_float(metrics.get(Metric.AGE))
    gender = config.get(CONF_GENDER)

    if h <= 0 or w <= 0 or a <= 0 or gender is None:
        return 0.0

    if _is_dual(config):
        z_lf = _get_z_lf(metrics)
        if z_lf <= 0:
            return 0.0
        ri_lf = (h * h) / z_lf
        if gender == Gender.MALE:
            lbm = 0.7909 * ri_lf + 0.116 * w - 0.096 * a - 4.03
        else:
            lbm = 0.8014 * ri_lf + 0.102 * w - 0.071 * a - 4.85
    else:
        # XIAOMI and SCIENCE use the same Xiaomi LBM formula
        # (the difference between modes is in fat%, water, BMR, etc.)
        z = _get_z_std(metrics)
        if z <= 0:
            return 0.0
        lbm = (h * 9.058 / 100.0) * (h / 100.0)
        lbm += w * 0.32 + 12.226
        lbm -= z * 0.0068
        lbm -= a * 0.0542

    # Borne physiologique
    lbm = min(lbm, w * 0.98)
    return float(lbm)


# ─────────────────────────────────────────────────────────────────────────────
# FAT PERCENTAGE
# ─────────────────────────────────────────────────────────────────────────────


def get_fat_percentage(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate body fat percentage.

    XIAOMI :
        Zepp Life formula. Empirical Xiaomi coefficients according to gender/weight/height.

    SCIENCE :
        Direct 2-compartment method (Siri 1956) :
        fat% = (W − LBM) / W × 100

    S400 :
        Direct 2-compartment method (calibrated Lukaski LBM → precise fat%).
    """
    w = to_float(metrics.get(Metric.WEIGHT))
    lbm = to_float(metrics.get(Metric.LBM))
    a = to_float(metrics.get(Metric.AGE))
    h = to_float(config.get(CONF_HEIGHT))
    gender = config.get(CONF_GENDER)
    mode = config.get(CONF_CALCULATION_MODE, ALGO_XIAOMI)

    if w <= 0 or lbm <= 0:
        return 0.0

    if _is_dual(config) or mode == ALGO_SCIENCE:
        # 2-compartment direct
        fat_pct = (w - lbm) / w * 100.0

    else:
        # XIAOMI — exact Zepp Life formula
        if gender == Gender.MALE:
            adjust = 0.8
            coefficient = 0.98 if w < 61 else 1.0
        else:
            adjust = 9.25 if a <= 49 else 7.25
            coefficient = 1.0
            if w > 60:
                coefficient = 0.96
                if h > 160:
                    coefficient *= 1.03
            elif w < 50:
                coefficient = 1.02
                if h > 160:
                    coefficient *= 1.03

        fat_pct = (1.0 - ((lbm - adjust) * coefficient / w)) * 100.0

    if fat_pct > 63:
        fat_pct = 75

    return check_value_constraints(fat_pct, 5, 75)


# ─────────────────────────────────────────────────────────────────────────────
# WATER PERCENTAGE
# ─────────────────────────────────────────────────────────────────────────────


def get_water_percentage(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate water percentage.

    XIAOMI :
        Zepp Life Formula — (100 − fat%) × 0.7, correction coefficient ×1.02 or ×0.98.

    SCIENCE :
        Pace constant 1963 : water represents 73% of lean mass (fat-free mass).
        water% = (100 − fat%) × 0.73

    S400 :
        Blend of two estimates for better accuracy:
          1. Pace fat-free method : water_pace% = (100 − fat%) × 0.73
          2. Kushner 1992 BIA equation using Z_hf (250 kHz):
             TBW (L) = 0.5813 × (H²/Z_hf) + 0.065 × W + 0.04
             At 250 kHz the current crosses cell membranes, giving access
             to intracellular water (ICW), yielding a more accurate TBW.
        water% = (water_pace% + TBW%) / 2
        Calibrated on reference point: 55.8% ✓
    """
    fat_pct = to_float(metrics.get(Metric.FAT_PERCENTAGE))
    mode = config.get(CONF_CALCULATION_MODE, ALGO_XIAOMI)

    if _is_dual(config):
        # S400 — blend Pace + Kushner 1992 (Z_hf)
        h = to_float(config.get(CONF_HEIGHT))
        w = to_float(metrics.get(Metric.WEIGHT))
        z_hf = _get_z_hf(metrics)

        water_pace = (100.0 - fat_pct) * 0.73

        if h > 0 and w > 0 and z_hf > 0:
            ri_hf = (h * h) / z_hf
            tbw_l = 0.5813 * ri_hf + 0.065 * w + 0.04
            tbw_pct = (tbw_l / w) * 100.0
            water_pct = (water_pace + tbw_pct) / 2.0
        else:
            water_pct = water_pace

    elif mode == ALGO_SCIENCE:
        # Pace constant only
        water_pct = (100.0 - fat_pct) * 0.73

    else:
        # XIAOMI — Zepp Life exact
        water_pct = (100.0 - fat_pct) * 0.7
        coefficient = 1.02 if water_pct <= 50 else 0.98
        water_pct *= coefficient

    if water_pct >= 65:
        water_pct = 75

    return check_value_constraints(water_pct, 35, 75)


# ─────────────────────────────────────────────────────────────────────────────
# BONE MASS
# ─────────────────────────────────────────────────────────────────────────────


def get_bone_mass(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate bone mass.

    Common empirical formula for all 3 modes (based on LBM).
    Each mode calculates a different LBM, which indirectly differentiates bone mass.
    """
    lbm = to_float(metrics.get(Metric.LBM))
    gender = config.get(CONF_GENDER)

    base = 0.245691014 if gender == Gender.FEMALE else 0.18016894
    bone_mass = (base - (lbm * 0.05158)) * -1

    if bone_mass > 2.2:
        bone_mass += 0.1
    else:
        bone_mass -= 0.1

    if gender == Gender.FEMALE and bone_mass > 5.1:
        bone_mass = 8.0
    elif gender == Gender.MALE and bone_mass > 5.2:
        bone_mass = 8.0

    return check_value_constraints(bone_mass, 0.5, 8)


# ─────────────────────────────────────────────────────────────────────────────
# MUSCLE MASS
# ─────────────────────────────────────────────────────────────────────────────


def get_muscle_mass(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate muscle mass.

    Common formula: W − (fat% × W) − bone_mass.
    Identical in all 3 modes (the difference comes from the fat% calculated upstream).
    """
    w = to_float(metrics.get(Metric.WEIGHT))
    fat_pct = to_float(metrics.get(Metric.FAT_PERCENTAGE))
    bone_mass = to_float(metrics.get(Metric.BONE_MASS))
    gender = config.get(CONF_GENDER)

    muscle_mass = w - (fat_pct * 0.01 * w) - bone_mass

    if gender == Gender.FEMALE and muscle_mass >= 84:
        muscle_mass = 120.0
    elif gender == Gender.MALE and muscle_mass >= 93.5:
        muscle_mass = 120.0

    return check_value_constraints(muscle_mass, 10, 120)


# ─────────────────────────────────────────────────────────────────────────────
# METABOLIC AGE
# ─────────────────────────────────────────────────────────────────────────────


def get_metabolic_age(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate metabolic age.

    XIAOMI / SCIENCE (mono-frequency) :
        Exact Zepp Life formula.
        Male   : MA = H×−0.7471 + W×0.9161 + A×0.4184 + Z×0.0517 + 54.2267
        Female : MA = H×−1.1165 + W×1.5784 + A×0.4615 + Z×0.0415 + 83.2548
        Note: calibrated for Z ~100-200 Ω (classic Xiaomi floor scales).

    S400 (dual 50 kHz + 250 kHz) :
        Proportional approach based on body fat percentage
        relative to WHO target value for age and gender.
        MA = real_age × (current_fat% / target_fat%)
        where target_fat% = median of WHO table for age/gender range.
        → If fat% = target → MA = real age (subject within normal range).
        → Xiaomi formula out-of-range for Z > 250 Ω (4-electrode full-body).
    """
    h = to_float(config.get(CONF_HEIGHT))
    w = to_float(metrics.get(Metric.WEIGHT))
    a = to_float(metrics.get(Metric.AGE))
    gender = config.get(CONF_GENDER)

    if h <= 0 or w <= 0 or a <= 0 or gender is None:
        return a if a > 0 else 15.0

    if _is_dual(config):
        fat_pct = to_float(metrics.get(Metric.FAT_PERCENTAGE))
        scale = config.get(CONF_SCALE)
        if scale is not None and fat_pct > 0:
            fat_scale = scale.get_fat_percentage(int(a))
            # fat_scale[1] = lower bound "normal", fat_scale[2] = upper bound "normal"
            # Median of normal range as reference
            fat_target = (fat_scale[1] + fat_scale[2]) / 2.0
            if fat_target > 0:
                metab_age = a * (fat_pct / fat_target)
            else:
                metab_age = a
        else:
            metab_age = a
    else:
        # XIAOMI and SCIENCE — Zepp Life formula (same single impedance)
        z = _get_z_std(metrics)
        if z <= 0:
            return a
        if gender == Gender.MALE:
            metab_age = (
                (h * -0.7471) + (w * 0.9161) + (a * 0.4184) + (z * 0.0517) + 54.2267
            )
        else:
            metab_age = (
                (h * -1.1165) + (w * 1.5784) + (a * 0.4615) + (z * 0.0415) + 83.2548
            )

    return check_value_constraints(metab_age, 15, 80)


# ─────────────────────────────────────────────────────────────────────────────
# PROTEIN PERCENTAGE
# ─────────────────────────────────────────────────────────────────────────────


def get_protein_percentage(
    _: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate protein percentage.

    Common formula for all 3 modes: protein% = (muscle / W) × 100 − water%
    """
    muscle = to_float(metrics.get(Metric.MUSCLE_MASS))
    w = to_float(metrics.get(Metric.WEIGHT))
    water = to_float(metrics.get(Metric.WATER_PERCENTAGE))

    if w <= 0:
        return 0.0

    return check_value_constraints((muscle / w) * 100.0 - water, 5, 32)


# ─────────────────────────────────────────────────────────────────────────────
# FAT MASS TO IDEAL WEIGHT
# ─────────────────────────────────────────────────────────────────────────────


def get_fat_mass_to_ideal_weight(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> float:
    """Calculate fat mass delta vs ideal weight.

    Common to all 3 modes. Uses the fat_percentage table from Scale.
    fat_mass_delta = W × (target_fat%/100) − W × (current_fat%/100)
    Negative → fat loss needed, positive → possible fat gain.
    """
    w = to_float(metrics.get(Metric.WEIGHT))
    a = to_float(metrics.get(Metric.AGE))
    fat_pct = to_float(metrics.get(Metric.FAT_PERCENTAGE))

    target = config[CONF_SCALE].get_fat_percentage(int(a))[2]
    return float(w * (target / 100.0) - w * (fat_pct / 100.0))


# ─────────────────────────────────────────────────────────────────────────────
# BODY TYPE
# ─────────────────────────────────────────────────────────────────────────────


def get_body_type(
    config: Mapping[str, Any], metrics: Mapping[Metric, StateType | datetime]
) -> str:
    """Classify body type based on fat% and muscle mass.

    Common to all 3 modes (the difference comes from calculated values).
    """
    fat = to_float(metrics.get(Metric.FAT_PERCENTAGE))
    muscle = to_float(metrics.get(Metric.MUSCLE_MASS))
    a = to_float(metrics.get(Metric.AGE))
    scale = config[CONF_SCALE]

    f_scale = scale.get_fat_percentage(int(a))
    factor = 0 if fat > f_scale[2] else (2 if fat < f_scale[1] else 1)
    m_factor = (
        2
        if muscle > scale.muscle_mass[1]
        else (0 if muscle < scale.muscle_mass[0] else 1)
    )
    body_type = m_factor + (factor * 3)

    return [
        "obese",
        "overweight",
        "thick_set",
        "lack_exercise",
        "balanced",
        "balanced_muscular",
        "skinny",
        "balanced_skinny",
        "skinny_muscular",
    ][body_type]

"""Tests for bodymiscale metrics/body_score.py."""

from __future__ import annotations

from datetime import UTC
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.bodymiscale.const import (
    CONF_BIRTHDAY,
    CONF_CALCULATION_MODE,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_IMPEDANCE_MODE,
    CONF_PROFILE_METHOD,
    CONF_SCALE,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_WEIGHT,
    IMPEDANCE_MODE_DUAL,
    IMPEDANCE_MODE_NONE,
    IMPEDANCE_MODE_STANDARD,
    PROFILE_METHOD_NONE,
    PROFILE_METHOD_NOTIFY,
)
from custom_components.bodymiscale.metrics import BodyScaleMetricsHandler, body_score
from custom_components.bodymiscale.metrics.scale import Scale
from custom_components.bodymiscale.models import Gender, Metric
from custom_components.bodymiscale.profile import (
    NotificationCoordinator,
    NotificationFilter,
)

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _make_config(
    birthday: str = "1990-01-15",
    gender: Gender = Gender.FEMALE,
    height: float = 165.0,
    impedance_mode: str = IMPEDANCE_MODE_NONE,
    profile_method: str = PROFILE_METHOD_NONE,
    weight_sensor: str = "sensor.weight",
    impedance_sensor: str | None = None,
) -> dict[str, Any]:
    config: dict[str, Any] = {
        "name": "TestUser",
        CONF_BIRTHDAY: birthday,
        CONF_GENDER: gender,
        CONF_HEIGHT: height,
        CONF_CALCULATION_MODE: "xiaomi",
        CONF_IMPEDANCE_MODE: impedance_mode,
        CONF_PROFILE_METHOD: profile_method,
        CONF_SENSOR_WEIGHT: weight_sensor,
    }
    if impedance_sensor:
        config[CONF_SENSOR_IMPEDANCE] = impedance_sensor
    return config


# ===========================================================================
# Body score — notification coordinator pending/accept
# ===========================================================================


async def test_weight_with_notification_coordinator_stores_pending(
    hass: HomeAssistant,
) -> None:
    """When a NotificationCoordinator is set, weight must be stored as pending."""
    config = _make_config(
        weight_sensor="sensor.w_notify",
        profile_method=PROFILE_METHOD_NOTIFY,
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    coordinator = MagicMock(spec=NotificationCoordinator)
    coordinator.async_notify = AsyncMock()
    handler.set_notification_coordinator(coordinator)

    values: list[float] = []
    handler.subscribe(Metric.WEIGHT, lambda v: values.append(float(v)))

    hass.states.async_set("sensor.w_notify", "70.0")
    await hass.async_block_till_done()

    assert len(values) == 0
    coordinator.async_notify.assert_awaited_once()
    assert handler._pending_weight == pytest.approx(70.0)
    handler.unload()


async def test_accept_pending_measurement_publishes_weight(hass: HomeAssistant) -> None:
    """accept_pending_measurement must replay the pending weight and publish it."""
    config = _make_config(
        weight_sensor="sensor.w_accept",
        profile_method=PROFILE_METHOD_NOTIFY,
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    coordinator = MagicMock(spec=NotificationCoordinator)
    coordinator.async_notify = AsyncMock()
    handler.set_notification_coordinator(coordinator)

    values: list[float] = []
    handler.subscribe(Metric.WEIGHT, lambda v: values.append(float(v)))

    hass.states.async_set("sensor.w_accept", "68.0")
    await hass.async_block_till_done()
    assert len(values) == 0

    assert isinstance(handler.profile_filter, NotificationFilter)
    handler.profile_filter.confirm()
    handler.accept_pending_measurement()

    assert values, "Weight must be published after accept_pending_measurement"
    assert values[-1] == pytest.approx(68.0, abs=0.1)
    handler.unload()


async def test_accept_pending_measurement_noop_when_no_pending(
    hass: HomeAssistant,
) -> None:
    """accept_pending_measurement must do nothing when no measurement is pending."""
    config = _make_config(
        weight_sensor="sensor.w_nopending",
        profile_method=PROFILE_METHOD_NOTIFY,
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    values: list[float] = []
    handler.subscribe(Metric.WEIGHT, lambda v: values.append(float(v)))

    handler.accept_pending_measurement()
    assert len(values) == 0
    handler.unload()


async def test_accept_pending_measurement_replays_impedance(
    hass: HomeAssistant,
) -> None:
    """accept_pending_measurement must replay buffered impedance after weight."""
    config = _make_config(
        height=175.0,
        gender=Gender.MALE,
        birthday="1990-03-10",
        impedance_mode=IMPEDANCE_MODE_STANDARD,
        weight_sensor="sensor.w_imp_accept",
        impedance_sensor="sensor.imp_accept",
        profile_method=PROFILE_METHOD_NOTIFY,
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    coordinator = MagicMock(spec=NotificationCoordinator)
    coordinator.async_notify = AsyncMock()
    handler.set_notification_coordinator(coordinator)

    fat_values: list[float] = []
    handler.subscribe(Metric.FAT_PERCENTAGE, lambda v: fat_values.append(float(v)))

    hass.states.async_set("sensor.w_imp_accept", "78.0")
    await hass.async_block_till_done()

    hass.states.async_set("sensor.imp_accept", "500")
    await hass.async_block_till_done()

    assert len(fat_values) == 0

    assert isinstance(handler.profile_filter, NotificationFilter)
    handler.profile_filter.confirm()
    handler.accept_pending_measurement()

    assert fat_values, "FAT_PERCENTAGE should be computed after replay"
    handler.unload()


# ===========================================================================
# Pending measurement timeout
# ===========================================================================


async def test_pending_measurement_timeout_discards_weight(hass: HomeAssistant) -> None:
    """_expire_pending_measurement must discard the pending weight after timeout."""
    from datetime import datetime

    config = _make_config(
        weight_sensor="sensor.w_timeout",
        profile_method=PROFILE_METHOD_NOTIFY,
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    coordinator = MagicMock(spec=NotificationCoordinator)
    coordinator.async_notify = AsyncMock()
    handler.set_notification_coordinator(coordinator)

    hass.states.async_set("sensor.w_timeout", "70.0")
    await hass.async_block_till_done()

    assert handler._pending_weight is not None

    handler._expire_pending_measurement(datetime.now(UTC))

    assert handler._pending_weight is None
    assert handler._pending_state is None
    handler.unload()


async def test_expire_pending_noop_when_no_pending(hass: HomeAssistant) -> None:
    """_expire_pending_measurement must do nothing when no measurement is pending."""
    from datetime import datetime

    config = _make_config()
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    handler._expire_pending_measurement(datetime.now(UTC))
    handler.unload()


# ===========================================================================
# Body score — pure scoring functions (direct unit tests)
#
# The functions below were previously untested: this file only exercised
# the notification/pending-measurement plumbing, never the actual scoring
# arithmetic in body_score.py.
# ===========================================================================


def _score_config(
    gender: Gender = Gender.FEMALE,
    height: float = 165.0,
    impedance_mode: str = IMPEDANCE_MODE_NONE,
) -> dict[str, Any]:
    """Build a minimal config dict with a real Scale for scoring tests."""
    return {
        CONF_GENDER: gender,
        CONF_HEIGHT: height,
        CONF_IMPEDANCE_MODE: impedance_mode,
        CONF_SCALE: Scale(int(height), gender),
    }


# ---------------------------------------------------------------------------
# _get_malus
# ---------------------------------------------------------------------------


def test_get_malus_zero_range_returns_zero() -> None:
    """When min_data == max_data, _get_malus must return 0.0 (avoid /0)."""
    assert body_score._get_malus(10.0, 5.0, 5.0, 100, 0) == 0.0


def test_get_malus_negative_result_clamped_to_zero() -> None:
    """A result that would be negative must be clamped to 0.0."""
    # data beyond max_data on an increasing scale makes the raw ratio negative.
    result = body_score._get_malus(25.0, 10.0, 20.0, 10, 0)
    assert result == 0.0


def test_get_malus_computes_expected_value() -> None:
    """_get_malus must follow the documented linear-interpolation formula."""
    result = body_score._get_malus(16.0, 14.0, 15.0, 30, 15)
    expected = ((16.0 - 15.0) / (14.0 - 15.0)) * float(30 - 15)
    assert result == pytest.approx(max(0.0, expected))


# ---------------------------------------------------------------------------
# _calculate_bmi_deduct_score
# ---------------------------------------------------------------------------


def test_bmi_deduct_score_zero_for_unrealistic_height() -> None:
    """A height below 90cm must be treated as unreliable -> no deduction."""
    config = _score_config(height=50.0)
    metrics = {Metric.BMI: 10.0, Metric.AGE: 30, Metric.FAT_PERCENTAGE: 50.0}
    assert body_score._calculate_bmi_deduct_score(config, metrics) == 0.0


def test_bmi_deduct_score_very_low_bmi_returns_30() -> None:
    """A BMI at or below 14.0 must deduct a flat 30 points."""
    config = _score_config()
    metrics = {Metric.BMI: 14.0, Metric.AGE: 30, Metric.FAT_PERCENTAGE: 20.0}
    assert body_score._calculate_bmi_deduct_score(config, metrics) == 30.0


def test_bmi_deduct_score_optimal_range_returns_zero() -> None:
    """A normal BMI with low-enough fat% for an adult must deduct nothing."""
    config = _score_config()
    metrics = {Metric.BMI: 21.0, Metric.AGE: 30, Metric.FAT_PERCENTAGE: 20.0}
    assert body_score._calculate_bmi_deduct_score(config, metrics) == 0.0


def test_bmi_deduct_score_low_bmi_below_15_applies_malus() -> None:
    """A BMI between 14 and 15 must apply the underweight malus + 15."""
    config = _score_config()
    metrics = {Metric.BMI: 14.5, Metric.AGE: 30, Metric.FAT_PERCENTAGE: 5.0}
    result = body_score._calculate_bmi_deduct_score(config, metrics)
    assert result > 15.0


def test_bmi_deduct_score_underweight_adult_applies_malus() -> None:
    """A BMI between 15 and 18.5 for an adult must apply malus + 5."""
    config = _score_config()
    metrics = {Metric.BMI: 17.0, Metric.AGE: 30, Metric.FAT_PERCENTAGE: 36.0}
    result = body_score._calculate_bmi_deduct_score(config, metrics)
    assert result > 5.0


def test_bmi_deduct_score_obese_returns_10() -> None:
    """A BMI >= 32 with high fat% must deduct a flat 10 points."""
    config = _score_config()
    metrics = {Metric.BMI: 33.0, Metric.AGE: 30, Metric.FAT_PERCENTAGE: 36.0}
    assert body_score._calculate_bmi_deduct_score(config, metrics) == 10.0


def test_bmi_deduct_score_overweight_applies_malus() -> None:
    """A BMI between 28 and 32 with high fat% must apply malus + 5."""
    config = _score_config()
    metrics = {Metric.BMI: 29.0, Metric.AGE: 30, Metric.FAT_PERCENTAGE: 36.0}
    result = body_score._calculate_bmi_deduct_score(config, metrics)
    assert result >= 5.0


# ---------------------------------------------------------------------------
# _calculate_body_fat_deduct_score
# ---------------------------------------------------------------------------


def test_body_fat_deduct_score_optimal_range_returns_zero() -> None:
    """Fat% between the low threshold and the 'best' level deducts nothing."""
    config = _score_config()  # female, 18-40 scale: [21, 28, 35, 40]
    metrics = {Metric.FAT_PERCENTAGE: 25.0, Metric.AGE: 30}
    assert body_score._calculate_body_fat_deduct_score(config, metrics) == 0.0


def test_body_fat_deduct_score_very_high_returns_20() -> None:
    """Fat% at or above the 'high' threshold must deduct a flat 20 points."""
    config = _score_config()
    metrics = {Metric.FAT_PERCENTAGE: 41.0, Metric.AGE: 30}
    assert body_score._calculate_body_fat_deduct_score(config, metrics) == 20.0


def test_body_fat_deduct_score_below_high_threshold_applies_malus() -> None:
    """Fat% just under the 'high' threshold must apply a malus + 10.

    Note: because ``fat_percentage < scale[3]`` unconditionally returns here,
    the later branches in the function (checking scale[2]/scale[0]) can never
    be reached for any real-valued fat_percentage — this test documents the
    function's actual current behavior rather than asserting on dead code.
    """
    config = _score_config()
    metrics = {Metric.FAT_PERCENTAGE: 38.0, Metric.AGE: 30}
    result = body_score._calculate_body_fat_deduct_score(config, metrics)
    assert result > 10.0


def test_body_fat_deduct_score_very_low_fat_also_hits_below_high_branch() -> None:
    """Even very low fat% falls into the same 'below high threshold' branch.

    This confirms the malus-vs-scale[3] branch is exhaustive: any fat%
    below scale[3] returns here, so the low-fat-specific branches lower in
    the function are unreachable dead code as currently written.
    """
    config = _score_config()
    metrics = {Metric.FAT_PERCENTAGE: 5.0, Metric.AGE: 30}
    result = body_score._calculate_body_fat_deduct_score(config, metrics)
    assert result > 0.0


# ---------------------------------------------------------------------------
# _calculate_common_deduct_score
# ---------------------------------------------------------------------------


def test_common_deduct_score_at_or_above_max_returns_zero() -> None:
    """A value at/above max_value must deduct nothing."""
    assert body_score._calculate_common_deduct_score(10.0, 20.0, 20.0) == 0.0
    assert body_score._calculate_common_deduct_score(10.0, 20.0, 25.0) == 0.0


def test_common_deduct_score_below_min_returns_full_penalty() -> None:
    """A value below min_value must deduct the full 10-point penalty."""
    assert body_score._calculate_common_deduct_score(10.0, 20.0, 5.0) == 10.0


def test_common_deduct_score_between_bounds_applies_malus() -> None:
    """A value strictly between min/max must apply a partial malus + 5."""
    result = body_score._calculate_common_deduct_score(10.0, 20.0, 15.0)
    assert 5.0 < result < 10.0


# ---------------------------------------------------------------------------
# _calculate_muscle_deduct_score
# ---------------------------------------------------------------------------


def test_muscle_deduct_score_s400_zero_smm_returns_zero() -> None:
    """In dual-frequency (S400) mode, a zero/failed SMM must deduct nothing."""
    config = _score_config(impedance_mode=IMPEDANCE_MODE_DUAL)
    metrics = {Metric.SKELETAL_MUSCLE_MASS: 0.0}
    assert body_score._calculate_muscle_deduct_score(config, metrics) == 0.0


def test_muscle_deduct_score_classic_zero_mass_returns_zero() -> None:
    """In classic modes, a zero/failed total muscle mass must deduct nothing."""
    config = _score_config(impedance_mode=IMPEDANCE_MODE_NONE)
    metrics = {Metric.MUSCLE_MASS: 0.0}
    assert body_score._calculate_muscle_deduct_score(config, metrics) == 0.0


def test_muscle_deduct_score_s400_uses_skeletal_muscle_mass() -> None:
    """In S400 mode, the SMM-adjusted thresholds must drive the malus."""
    config = _score_config(
        impedance_mode=IMPEDANCE_MODE_DUAL, gender=Gender.MALE, height=175.0
    )
    scale = config[CONF_SCALE].muscle_mass
    target_max = scale[0] * 0.77
    metrics = {Metric.SKELETAL_MUSCLE_MASS: target_max}
    assert body_score._calculate_muscle_deduct_score(config, metrics) == 0.0


def test_muscle_deduct_score_classic_uses_total_muscle_mass() -> None:
    """In classic modes, total muscle mass below threshold must be penalized."""
    config = _score_config(
        impedance_mode=IMPEDANCE_MODE_STANDARD, gender=Gender.FEMALE, height=165.0
    )
    scale = config[CONF_SCALE].muscle_mass
    metrics = {Metric.MUSCLE_MASS: scale[0] - 10.0}  # well below target_min
    assert body_score._calculate_muscle_deduct_score(config, metrics) == 10.0


# ---------------------------------------------------------------------------
# _calculate_water_deduct_score
# ---------------------------------------------------------------------------


def test_water_deduct_score_uses_male_threshold() -> None:
    """Male water% target is 55.0; at target, deduction must be zero."""
    config = _score_config(gender=Gender.MALE)
    assert body_score._calculate_water_deduct_score(config, 55.0) == 0.0


def test_water_deduct_score_uses_female_threshold() -> None:
    """Female water% target is 45.0; at target, deduction must be zero."""
    config = _score_config(gender=Gender.FEMALE)
    assert body_score._calculate_water_deduct_score(config, 45.0) == 0.0


def test_water_deduct_score_below_threshold_penalized() -> None:
    """Water% far below the gender target must incur the full penalty."""
    config = _score_config(gender=Gender.FEMALE)
    assert body_score._calculate_water_deduct_score(config, 30.0) == 10.0


# ---------------------------------------------------------------------------
# _calculate_body_visceral_deduct_score
# ---------------------------------------------------------------------------


def test_visceral_deduct_score_below_min_returns_zero() -> None:
    """Visceral fat below 10 must deduct nothing."""
    assert body_score._calculate_body_visceral_deduct_score(5.0) == 0.0


def test_visceral_deduct_score_at_or_above_max_returns_15() -> None:
    """Visceral fat at/above 15 must deduct a flat 15 points."""
    assert body_score._calculate_body_visceral_deduct_score(15.0) == 15.0
    assert body_score._calculate_body_visceral_deduct_score(20.0) == 15.0


def test_visceral_deduct_score_between_bounds_applies_malus() -> None:
    """Visceral fat strictly between 10 and 15 must apply a partial malus."""
    result = body_score._calculate_body_visceral_deduct_score(12.0)
    assert 10.0 < result < 15.0


# ---------------------------------------------------------------------------
# _calculate_basal_metabolism_deduct_score
# ---------------------------------------------------------------------------


def test_basal_metabolism_deduct_score_at_or_above_normal_returns_zero() -> None:
    """BMR at/above the expected value for age/weight must deduct nothing."""
    config = _score_config(gender=Gender.FEMALE)
    # age < 30 -> coefficient 21.24; weight 60 -> normal_bmr = 1274.4
    metrics = {Metric.AGE: 25, Metric.WEIGHT: 60.0, Metric.BMR: 1300.0}
    assert body_score._calculate_basal_metabolism_deduct_score(config, metrics) == 0.0


def test_basal_metabolism_deduct_score_far_below_normal_returns_6() -> None:
    """BMR at/below normal_bmr - 300 must deduct a flat 6 points."""
    config = _score_config(gender=Gender.FEMALE)
    metrics = {Metric.AGE: 25, Metric.WEIGHT: 60.0, Metric.BMR: 900.0}
    assert body_score._calculate_basal_metabolism_deduct_score(config, metrics) == 6.0


def test_basal_metabolism_deduct_score_moderately_low_applies_malus() -> None:
    """BMR moderately below normal must apply a partial malus + 5.

    Note: this exposes a discontinuity in the source function. As bmr
    decreases from normal_bmr towards normal_bmr-300, this branch's result
    climbs from ~5 up to ~8 — but at bmr <= normal_bmr - 300 exactly, the
    flat-6.0 branch above takes over instead, so the deduction actually
    *drops* right at the boundary where bmr gets worse. This test just
    documents the current (discontinuous) behavior.
    """
    config = _score_config(gender=Gender.FEMALE)
    metrics = {Metric.AGE: 25, Metric.WEIGHT: 60.0, Metric.BMR: 1100.0}
    result = body_score._calculate_basal_metabolism_deduct_score(config, metrics)
    assert 5.0 < result < 8.0


# ---------------------------------------------------------------------------
# _calculate_protein_deduct_score
# ---------------------------------------------------------------------------


def test_protein_deduct_score_above_17_returns_zero() -> None:
    """Protein% above 17.0 must deduct nothing."""
    assert body_score._calculate_protein_deduct_score(18.0) == 0.0


def test_protein_deduct_score_below_10_returns_10() -> None:
    """Protein% below 10.0 must deduct a flat 10 points."""
    assert body_score._calculate_protein_deduct_score(9.0) == 10.0


def test_protein_deduct_score_between_10_and_16_applies_malus() -> None:
    """Protein% in (10, 16] must apply a malus scaled between 5 and 10."""
    result = body_score._calculate_protein_deduct_score(13.0)
    assert 5.0 < result < 10.0


def test_protein_deduct_score_between_16_and_17_applies_smaller_malus() -> None:
    """Protein% in (16, 17] must apply a smaller malus scaled between 3 and 5.

    Note: this branch (``protein_percentage <= 17.0``) is always true once
    we reach it, since anything > 17.0 already returned above — so the
    function's final ``return 0.0`` fallback is unreachable dead code.
    """
    result = body_score._calculate_protein_deduct_score(16.5)
    assert 3.0 < result < 5.0


# ---------------------------------------------------------------------------
# get_body_score — integration / clamping
# ---------------------------------------------------------------------------


def test_get_body_score_perfect_metrics_returns_100() -> None:
    """All metrics in their optimal ranges must yield a perfect score of 100."""
    config = _score_config(gender=Gender.FEMALE, height=165.0)
    scale = config[CONF_SCALE]
    fat_scale = scale.get_fat_percentage(30)
    muscle_scale = scale.muscle_mass
    metrics = {
        Metric.BMI: 21.0,
        Metric.AGE: 30,
        Metric.FAT_PERCENTAGE: fat_scale[0],
        Metric.MUSCLE_MASS: muscle_scale[1],
        Metric.WATER_PERCENTAGE: 45.0,
        Metric.VISCERAL_FAT: 5.0,
        Metric.WEIGHT: 60.0,
        Metric.BONE_MASS: 3.0,
        Metric.BMR: 1400.0,
        Metric.PROTEIN_PERCENTAGE: 18.0,
    }
    assert body_score.get_body_score(config, metrics) == 100.0


def test_get_body_score_clamped_to_minimum_10() -> None:
    """Even with every metric far out of range, the score cannot drop below 10."""
    config = _score_config(gender=Gender.FEMALE, height=165.0)
    metrics = {
        Metric.BMI: 5.0,
        Metric.AGE: 30,
        Metric.FAT_PERCENTAGE: 90.0,
        Metric.MUSCLE_MASS: 0.1,
        Metric.WATER_PERCENTAGE: 1.0,
        Metric.VISCERAL_FAT: 30.0,
        Metric.WEIGHT: 200.0,
        Metric.BONE_MASS: 0.1,
        Metric.BMR: 1.0,
        Metric.PROTEIN_PERCENTAGE: 1.0,
    }
    assert body_score.get_body_score(config, metrics) == 10.0

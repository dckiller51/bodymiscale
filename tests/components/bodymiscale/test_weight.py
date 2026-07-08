"""Tests for bodymiscale metrics/weight.py."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from homeassistant.core import HomeAssistant

from custom_components.bodymiscale.const import (
    CONF_BIRTHDAY,
    CONF_CALCULATION_MODE,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_IMPEDANCE_MODE,
    CONF_PROFILE_METHOD,
    CONF_SENSOR_WEIGHT,
    CONF_WEIGHT_MAX,
    CONF_WEIGHT_MIN,
    IMPEDANCE_MODE_NONE,
    PROFILE_METHOD_NONE,
    PROFILE_METHOD_WEIGHT,
)
from custom_components.bodymiscale.metrics import BodyScaleMetricsHandler
from custom_components.bodymiscale.models import Gender, Metric

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
) -> dict[str, Any]:
    return {
        "name": "TestUser",
        CONF_BIRTHDAY: birthday,
        CONF_GENDER: gender,
        CONF_HEIGHT: height,
        CONF_CALCULATION_MODE: "xiaomi",
        CONF_IMPEDANCE_MODE: impedance_mode,
        CONF_PROFILE_METHOD: profile_method,
        CONF_SENSOR_WEIGHT: weight_sensor,
    }


# ===========================================================================
# Weight processing — basic
# ===========================================================================


async def test_weight_update_triggers_weight_metric(hass: HomeAssistant) -> None:
    """A weight sensor state change must publish Metric.WEIGHT to subscribers."""
    config = _make_config(weight_sensor="sensor.scale_weight")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="test_entry")

    weight_values: list[float] = []
    handler.subscribe(Metric.WEIGHT, lambda v: weight_values.append(float(v)))

    hass.states.async_set("sensor.scale_weight", "70.5")
    await hass.async_block_till_done()

    assert weight_values, "Expected at least one WEIGHT update"
    assert weight_values[-1] == pytest.approx(70.5, abs=0.01)
    handler.unload()


async def test_weight_update_computes_bmi(hass: HomeAssistant) -> None:
    """A valid weight update must trigger BMI calculation for no-impedance mode."""
    config = _make_config(
        height=170.0,
        gender=Gender.MALE,
        birthday="1985-06-20",
        weight_sensor="sensor.weight_bmi",
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="test_entry")

    bmi_values: list[float] = []
    handler.subscribe(Metric.BMI, lambda v: bmi_values.append(float(v)))

    hass.states.async_set("sensor.weight_bmi", "75.0")
    await hass.async_block_till_done()

    assert bmi_values, "Expected at least one BMI update"
    assert bmi_values[-1] == pytest.approx(75.0 / (1.70**2), abs=0.5)
    handler.unload()


async def test_invalid_weight_state_ignored(hass: HomeAssistant) -> None:
    """Non-numeric weight sensor state must not trigger metric updates."""
    config = _make_config(weight_sensor="sensor.weight_bad")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="test_entry")

    weight_values: list[Any] = []
    handler.subscribe(Metric.WEIGHT, weight_values.append)

    hass.states.async_set("sensor.weight_bad", "unavailable")
    await hass.async_block_till_done()

    assert len(weight_values) == 0
    handler.unload()


async def test_last_measurement_time_updated_on_weight(hass: HomeAssistant) -> None:
    """A valid weight update must publish Metric.LAST_MEASUREMENT_TIME."""
    config = _make_config(weight_sensor="sensor.weight_ts")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="test_entry")

    timestamps: list[Any] = []
    handler.subscribe(Metric.LAST_MEASUREMENT_TIME, timestamps.append)

    hass.states.async_set("sensor.weight_ts", "65.0")
    await hass.async_block_till_done()

    assert timestamps, "Expected LAST_MEASUREMENT_TIME to be published"
    assert isinstance(timestamps[-1], datetime)
    handler.unload()


# ===========================================================================
# Weight processing — edge cases
# ===========================================================================


async def test_weight_below_minimum_ignored(hass: HomeAssistant) -> None:
    """Weight below CONSTRAINT_WEIGHT_MIN must be silently ignored."""
    config = _make_config(weight_sensor="sensor.w_low")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    values: list[float] = []
    handler.subscribe(Metric.WEIGHT, lambda v: values.append(float(v)))

    hass.states.async_set("sensor.w_low", "5.0")
    await hass.async_block_till_done()

    assert len(values) == 0
    handler.unload()


async def test_weight_above_maximum_sets_problem(hass: HomeAssistant) -> None:
    """Weight above CONSTRAINT_WEIGHT_MAX must record a 'high' sensor problem."""
    config = _make_config(weight_sensor="sensor.w_high")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    status_values: list[Any] = []
    handler.subscribe(Metric.STATUS, status_values.append)

    hass.states.async_set("sensor.w_high", "250.0")
    await hass.async_block_till_done()

    assert any("weight_high" in str(v) for v in status_values)
    handler.unload()


async def test_weight_in_pounds_converted_to_kg(hass: HomeAssistant) -> None:
    """Weight sensor reporting in pounds must be converted to kg before storage."""
    config = _make_config(weight_sensor="sensor.w_lbs")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    values: list[float] = []
    handler.subscribe(Metric.WEIGHT, lambda v: values.append(float(v)))

    hass.states.async_set("sensor.w_lbs", "154.0", {"unit_of_measurement": "lb"})
    await hass.async_block_till_done()

    assert values, "Expected WEIGHT update"
    assert values[-1] == pytest.approx(154.0 * 0.45359237, abs=0.1)
    handler.unload()


async def test_weight_unknown_state_clears_problem(hass: HomeAssistant) -> None:
    """Weight sensor going to 'unknown' must clear any existing problem."""
    config = _make_config(weight_sensor="sensor.w_unknown")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    hass.states.async_set("sensor.w_unknown", "250.0")
    await hass.async_block_till_done()

    status_after_problem: list[Any] = []
    handler.subscribe(Metric.STATUS, status_after_problem.append)

    hass.states.async_set("sensor.w_unknown", "unknown")
    await hass.async_block_till_done()

    assert any("none" in str(v).lower() for v in status_after_problem)
    handler.unload()


# ===========================================================================
# Weight-range profile filter
# ===========================================================================


async def test_weight_range_filter_accepts_in_range(hass: HomeAssistant) -> None:
    """Weight-range profile: measurement within range must be published."""
    config = _make_config(
        weight_sensor="sensor.w_range",
        profile_method=PROFILE_METHOD_WEIGHT,
    )
    config[CONF_WEIGHT_MIN] = 60.0
    config[CONF_WEIGHT_MAX] = 80.0

    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="test_entry")

    weight_values: list[float] = []
    handler.subscribe(Metric.WEIGHT, lambda v: weight_values.append(float(v)))

    hass.states.async_set("sensor.w_range", "70.0")
    await hass.async_block_till_done()

    assert weight_values, "Weight within range should be accepted"
    handler.unload()


async def test_weight_range_filter_rejects_out_of_range(hass: HomeAssistant) -> None:
    """Weight-range profile: measurement outside range must be silently ignored."""
    config = _make_config(
        weight_sensor="sensor.w_range_out",
        profile_method=PROFILE_METHOD_WEIGHT,
    )
    config[CONF_WEIGHT_MIN] = 60.0
    config[CONF_WEIGHT_MAX] = 80.0

    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="test_entry")

    weight_values: list[float] = []
    handler.subscribe(Metric.WEIGHT, lambda v: weight_values.append(float(v)))

    hass.states.async_set("sensor.w_range_out", "90.0")
    await hass.async_block_till_done()

    assert len(weight_values) == 0, "Weight outside range should be rejected"
    handler.unload()

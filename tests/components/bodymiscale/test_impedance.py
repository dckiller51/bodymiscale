"""Tests for bodymiscale metrics/impedance.py."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from homeassistant.core import HomeAssistant

from custom_components.bodymiscale.const import (
    CONF_BIRTHDAY,
    CONF_CALCULATION_MODE,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_IMPEDANCE_MODE,
    CONF_PROFILE_METHOD,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_IMPEDANCE_HIGH,
    CONF_SENSOR_IMPEDANCE_LOW,
    CONF_SENSOR_WEIGHT,
    CONF_WEIGHT_MAX,
    CONF_WEIGHT_MIN,
    IMPEDANCE_MODE_DUAL,
    IMPEDANCE_MODE_NONE,
    IMPEDANCE_MODE_STANDARD,
    PROFILE_METHOD_NONE,
    PROFILE_METHOD_NOTIFY,
    PROFILE_METHOD_WEIGHT,
)
from custom_components.bodymiscale.metrics import BodyScaleMetricsHandler
from custom_components.bodymiscale.models import Gender, Metric
from custom_components.bodymiscale.profile import (
    NotificationCoordinator,
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
    impedance_low_sensor: str | None = None,
    impedance_high_sensor: str | None = None,
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
    if impedance_low_sensor:
        config[CONF_SENSOR_IMPEDANCE_LOW] = impedance_low_sensor
    if impedance_high_sensor:
        config[CONF_SENSOR_IMPEDANCE_HIGH] = impedance_high_sensor
    return config


# ===========================================================================
# Standard impedance mode
# ===========================================================================


async def test_standard_impedance_computes_fat(hass: HomeAssistant) -> None:
    """Standard impedance mode must compute FAT_PERCENTAGE after both sensors update."""
    config = _make_config(
        height=175.0,
        gender=Gender.MALE,
        birthday="1990-03-10",
        impedance_mode=IMPEDANCE_MODE_STANDARD,
        weight_sensor="sensor.w_std",
        impedance_sensor="sensor.imp_std",
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="test_entry")

    fat_values: list[float] = []
    handler.subscribe(Metric.FAT_PERCENTAGE, lambda v: fat_values.append(float(v)))

    hass.states.async_set("sensor.w_std", "78.0")
    hass.states.async_set("sensor.imp_std", "500")
    await hass.async_block_till_done()

    assert fat_values, "FAT_PERCENTAGE should be computed with standard impedance"
    assert 0 < fat_values[-1] < 60
    handler.unload()


async def test_standard_impedance_no_fat_without_impedance(hass: HomeAssistant) -> None:
    """Standard impedance mode must not compute FAT_PERCENTAGE with weight only."""
    config = _make_config(
        height=175.0,
        gender=Gender.MALE,
        birthday="1990-03-10",
        impedance_mode=IMPEDANCE_MODE_STANDARD,
        weight_sensor="sensor.w_noimped",
        impedance_sensor="sensor.imp_noimped",
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="test_entry")

    fat_values: list[float] = []
    handler.subscribe(Metric.FAT_PERCENTAGE, lambda v: fat_values.append(float(v)))

    hass.states.async_set("sensor.w_noimped", "78.0")
    await hass.async_block_till_done()

    assert len(fat_values) == 0
    handler.unload()


# ===========================================================================
# Dual impedance mode
# ===========================================================================


async def test_dual_requires_both_sensors(hass: HomeAssistant) -> None:
    """Dual mode must require BOTH impedance_low and impedance_high."""
    config = _make_config(
        height=175.0,
        gender=Gender.MALE,
        birthday="1990-03-10",
        impedance_mode=IMPEDANCE_MODE_DUAL,
        weight_sensor="sensor.w_dual",
        impedance_low_sensor="sensor.imp_low",
        impedance_high_sensor="sensor.imp_high",
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    ecw_values: list[Any] = []
    handler.subscribe(Metric.ECW, ecw_values.append)

    hass.states.async_set("sensor.w_dual", "75.0")
    hass.states.async_set("sensor.imp_low", "300")
    await hass.async_block_till_done()
    assert len(ecw_values) == 0

    hass.states.async_set("sensor.imp_high", "250")
    await hass.async_block_till_done()
    assert ecw_values, "ECW should be computed when both impedances are available"
    handler.unload()


# ===========================================================================
# Impedance edge cases
# ===========================================================================


async def test_impedance_stored_as_pending_when_not_confirmed(
    hass: HomeAssistant,
) -> None:
    """Impedance arriving before user confirmation must be stored as pending."""
    config = _make_config(
        impedance_mode=IMPEDANCE_MODE_STANDARD,
        weight_sensor="sensor.w_imp_pend",
        impedance_sensor="sensor.imp_pend",
        profile_method=PROFILE_METHOD_NOTIFY,
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    coordinator = MagicMock(spec=NotificationCoordinator)
    coordinator.async_notify = AsyncMock()
    handler.set_notification_coordinator(coordinator)

    hass.states.async_set("sensor.w_imp_pend", "70.0")
    await hass.async_block_till_done()

    hass.states.async_set("sensor.imp_pend", "450")
    await hass.async_block_till_done()

    assert Metric.IMPEDANCE in handler._pending_impedance
    handler.unload()


async def test_impedance_rejected_when_no_weight_in_cycle(hass: HomeAssistant) -> None:
    """Impedance must be rejected when no weight was accepted in the current cycle."""
    config = _make_config(
        impedance_mode=IMPEDANCE_MODE_STANDARD,
        weight_sensor="sensor.w_no_cycle",
        impedance_sensor="sensor.imp_no_cycle",
        profile_method=PROFILE_METHOD_WEIGHT,
    )
    config[CONF_WEIGHT_MIN] = 60.0
    config[CONF_WEIGHT_MAX] = 80.0

    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    imp_values: list[Any] = []
    handler.subscribe(Metric.IMPEDANCE, imp_values.append)

    hass.states.async_set("sensor.imp_no_cycle", "450")
    await hass.async_block_till_done()

    assert len(imp_values) == 0
    handler.unload()


async def test_impedance_above_maximum_sets_problem(hass: HomeAssistant) -> None:
    """Impedance above CONSTRAINT_IMPEDANCE_MAX must record a 'high' problem."""
    config = _make_config(
        impedance_mode=IMPEDANCE_MODE_STANDARD,
        weight_sensor="sensor.w_imp_hi",
        impedance_sensor="sensor.imp_hi",
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    status_values: list[Any] = []
    handler.subscribe(Metric.STATUS, status_values.append)

    hass.states.async_set("sensor.w_imp_hi", "70.0")
    await hass.async_block_till_done()

    hass.states.async_set("sensor.imp_hi", "9999")
    await hass.async_block_till_done()

    assert any("impedance_high" in str(v) for v in status_values)
    handler.unload()

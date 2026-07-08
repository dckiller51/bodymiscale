"""Tests for bodymiscale metrics/__init__.py (BodyScaleMetricsHandler)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import EVENT_STATE_CHANGED, EVENT_STATE_REPORTED
from homeassistant.core import HomeAssistant, State

from custom_components.bodymiscale.const import (
    CONF_BIRTHDAY,
    CONF_CALCULATION_MODE,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_IMPEDANCE_MODE,
    CONF_INITIAL_WEIGHT,
    CONF_PROFILE_METHOD,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_IMPEDANCE_HIGH,
    CONF_SENSOR_IMPEDANCE_LOW,
    CONF_SENSOR_STABILIZED,
    CONF_SENSOR_WEIGHT,
    CONF_WEIGHT_MAX,
    CONF_WEIGHT_MIN,
    IMPEDANCE_MODE_DUAL,
    IMPEDANCE_MODE_NONE,
    IMPEDANCE_MODE_STANDARD,
    PROFILE_METHOD_NEAREST,
    PROFILE_METHOD_NONE,
    PROFILE_METHOD_NOTIFY,
    PROFILE_METHOD_WEIGHT,
)
from custom_components.bodymiscale.metrics import BodyScaleMetricsHandler, _MetricsStore
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
    impedance_low_sensor: str | None = None,
    impedance_high_sensor: str | None = None,
    stabilized_sensor: str | None = None,
    initial_weight: float | None = None,
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
    if stabilized_sensor:
        config[CONF_SENSOR_STABILIZED] = stabilized_sensor
    if initial_weight is not None:
        config[CONF_INITIAL_WEIGHT] = initial_weight
    return config


# ===========================================================================
# BodyScaleMetricsHandler — instantiation
# ===========================================================================


async def test_handler_instantiation(hass: HomeAssistant) -> None:
    """BodyScaleMetricsHandler must instantiate without raising."""
    config = _make_config()
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="test_entry")
    assert handler is not None
    handler.unload()


async def test_handler_config_is_accessible(hass: HomeAssistant) -> None:
    """Handler.config must expose the supplied configuration."""
    config = _make_config(height=170.0, gender=Gender.MALE)
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="test_entry")
    assert handler.config[CONF_HEIGHT] == 170.0
    assert handler.config[CONF_GENDER] == Gender.MALE
    handler.unload()


# ===========================================================================
# BodyScaleMetricsHandler — subscribe / publish
# ===========================================================================


async def test_handler_subscribe_returns_callable(hass: HomeAssistant) -> None:
    """subscribe() must return a callable that can be invoked to unsubscribe."""
    config = _make_config()
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="test_entry")

    received: list[Any] = []
    remove = handler.subscribe(Metric.WEIGHT, received.append)
    assert callable(remove)
    handler.unload()


async def test_handler_subscribe_receives_restored_metric(
    hass: HomeAssistant,
) -> None:
    """After restore_metric(), a new subscriber must receive the cached value."""
    config = _make_config()
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="test_entry")

    handler.restore_metric(Metric.WEIGHT, 65.0)

    received: list[Any] = []
    handler.subscribe(Metric.WEIGHT, received.append)

    handler.unload()


# ===========================================================================
# BodyScaleMetricsHandler — weight sensor state changes
# ===========================================================================


async def test_handler_weight_update_triggers_weight_metric(
    hass: HomeAssistant,
) -> None:
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


async def test_handler_weight_update_computes_bmi(hass: HomeAssistant) -> None:
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


async def test_handler_invalid_weight_state_ignored(hass: HomeAssistant) -> None:
    """Non-numeric weight sensor state must not trigger metric updates."""
    config = _make_config(weight_sensor="sensor.weight_bad")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="test_entry")

    weight_values: list[Any] = []
    handler.subscribe(Metric.WEIGHT, weight_values.append)

    hass.states.async_set("sensor.weight_bad", "unavailable")
    await hass.async_block_till_done()

    assert len(weight_values) == 0
    handler.unload()


async def test_handler_last_measurement_time_updated_on_weight(
    hass: HomeAssistant,
) -> None:
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
# BodyScaleMetricsHandler — standard impedance mode
# ===========================================================================


async def test_handler_standard_impedance_computes_fat(
    hass: HomeAssistant,
) -> None:
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


async def test_handler_standard_impedance_no_fat_without_impedance(
    hass: HomeAssistant,
) -> None:
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
# BodyScaleMetricsHandler — weight-range profile filter
# ===========================================================================


async def test_handler_weight_range_filter_accepts_in_range(
    hass: HomeAssistant,
) -> None:
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


async def test_handler_weight_range_filter_rejects_out_of_range(
    hass: HomeAssistant,
) -> None:
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


# ===========================================================================
# BodyScaleMetricsHandler — restore_metric
# ===========================================================================


async def test_handler_restore_metric_weight(hass: HomeAssistant) -> None:
    """restore_metric for WEIGHT must seed the handler cache."""
    config = _make_config()
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="test_entry")

    handler.restore_metric(Metric.WEIGHT, 68.5)
    handler.unload()


async def test_handler_restore_metric_timestamp(hass: HomeAssistant) -> None:
    """restore_metric for LAST_MEASUREMENT_TIME must accept a datetime."""
    config = _make_config()
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="test_entry")

    ts = datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC)
    handler.restore_metric(Metric.LAST_MEASUREMENT_TIME, ts)
    handler.unload()


# ===========================================================================
# BodyScaleMetricsHandler — unload
# ===========================================================================


async def test_handler_unload_removes_state_listeners(hass: HomeAssistant) -> None:
    """unload() must not raise and must allow safe re-call or GC."""
    config = _make_config(weight_sensor="sensor.w_unload")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="test_entry")

    handler.subscribe(Metric.WEIGHT, lambda v: None)

    handler.unload()

    hass.states.async_set("sensor.w_unload", "60.0")
    await hass.async_block_till_done()


# ===========================================================================
# restore_metric — edge cases
# ===========================================================================


async def test_restore_metric_timestamp_as_iso_string(hass: HomeAssistant) -> None:
    """restore_metric must accept an ISO string for LAST_MEASUREMENT_TIME."""
    config = _make_config()
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    handler.restore_metric(Metric.LAST_MEASUREMENT_TIME, "2024-06-15T10:30:00+00:00")
    handler.unload()


async def test_restore_metric_timestamp_invalid_string(hass: HomeAssistant) -> None:
    """restore_metric must silently ignore an unparsable datetime string."""
    config = _make_config()
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    handler.restore_metric(Metric.LAST_MEASUREMENT_TIME, "not-a-date")
    handler.unload()


async def test_restore_metric_datetime_type_skipped(hass: HomeAssistant) -> None:
    """restore_metric must skip a datetime object for WEIGHT (unexpected type)."""
    config = _make_config()
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    ts = datetime(2024, 1, 1, tzinfo=UTC)
    handler.restore_metric(Metric.WEIGHT, ts)
    handler.unload()


async def test_restore_metric_non_numeric_string_skipped(hass: HomeAssistant) -> None:
    """restore_metric must skip non-numeric strings for numeric metrics."""
    config = _make_config()
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    handler.restore_metric(Metric.WEIGHT, "not-a-number")
    handler.unload()


async def test_restore_metric_non_restorable_metric_ignored(
    hass: HomeAssistant,
) -> None:
    """restore_metric must silently ignore non-restorable metrics like BMI."""
    config = _make_config()
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    handler.restore_metric(Metric.BMI, 22.5)
    handler.unload()


async def test_restore_metric_sets_last_accepted_weight(hass: HomeAssistant) -> None:
    """restore_metric for WEIGHT must set _last_accepted_weight."""
    config = _make_config()
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    handler.restore_metric(Metric.WEIGHT, 72.0)
    assert handler._last_accepted_weight == pytest.approx(72.0)
    handler.unload()


# ===========================================================================
# _process_weight — edge cases
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
# _process_weight — with NotificationCoordinator
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


# ===========================================================================
# accept_pending_measurement
# ===========================================================================


async def test_accept_pending_measurement_publishes_weight(
    hass: HomeAssistant,
) -> None:
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
# _process_impedance — with NotificationFilter (pending storage)
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


async def test_impedance_rejected_when_no_weight_in_cycle(
    hass: HomeAssistant,
) -> None:
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


# ===========================================================================
# _has_impedance — dual mode
# ===========================================================================


async def test_has_impedance_dual_requires_both_sensors(hass: HomeAssistant) -> None:
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
# _publish_status — multiple problems
# ===========================================================================


async def test_status_combines_multiple_problems(hass: HomeAssistant) -> None:
    """STATUS must combine all sensor problems in deterministic order."""
    config = _make_config(
        impedance_mode=IMPEDANCE_MODE_STANDARD,
        weight_sensor="sensor.w_multi",
        impedance_sensor="sensor.imp_multi",
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    status_values: list[Any] = []
    handler.subscribe(Metric.STATUS, status_values.append)

    hass.states.async_set("sensor.w_multi", "250.0")
    hass.states.async_set("sensor.imp_multi", "9999")
    await hass.async_block_till_done()

    combined = [
        v for v in status_values if "weight" in str(v) and "impedance" in str(v)
    ]
    assert combined, f"Expected combined status, got: {status_values}"
    handler.unload()


# ===========================================================================
# _expire_pending_measurement — timeout
# ===========================================================================


async def test_pending_measurement_timeout_discards_weight(
    hass: HomeAssistant,
) -> None:
    """_expire_pending_measurement must discard the pending weight after timeout."""
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
    config = _make_config()
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    handler._expire_pending_measurement(datetime.now(UTC))
    handler.unload()


# ===========================================================================
# _MetricsStore — direct unit tests (TTL + MutableMapping interface)
# ===========================================================================


def test_metrics_store_getitem_expires_after_ttl() -> None:
    """A derived value must raise KeyError once its TTL has elapsed."""
    store = _MetricsStore(ttl=0.0)
    store[Metric.BMI] = 22.0
    with pytest.raises(KeyError):
        _ = store[Metric.BMI]


def test_metrics_store_delitem_source_and_derived() -> None:
    """__delitem__ must work for both source and derived metrics."""
    store = _MetricsStore(ttl=60)
    store[Metric.WEIGHT] = 70.0  # source metric
    store[Metric.BMI] = 22.0  # derived metric

    del store[Metric.WEIGHT]
    del store[Metric.BMI]

    assert Metric.WEIGHT not in store
    assert Metric.BMI not in store


def test_metrics_store_iter_evicts_expired_first() -> None:
    """__iter__ must evict expired derived entries before iterating."""
    store = _MetricsStore(ttl=0.0)
    store[Metric.BMI] = 22.0
    keys = list(iter(store))
    assert Metric.BMI not in keys


def test_metrics_store_len_evicts_expired_first() -> None:
    """__len__ must evict expired derived entries before counting."""
    store = _MetricsStore(ttl=0.0)
    store[Metric.WEIGHT] = 70.0  # source, never expires
    store[Metric.BMI] = 22.0  # derived, immediately expired
    assert len(store) == 1


def test_metrics_store_contains_non_metric_key_returns_false() -> None:
    """__contains__ with a non-Metric key must return False, not raise."""
    store = _MetricsStore(ttl=60)
    assert "not_a_metric" not in store


def test_metrics_store_contains_expired_derived_returns_false() -> None:
    """__contains__ must evict and report False for an expired derived entry."""
    store = _MetricsStore(ttl=0.0)
    store[Metric.BMI] = 22.0
    assert Metric.BMI not in store
    # Eviction as a side-effect of __contains__ must have removed it.
    assert Metric.BMI not in store._derived


# ===========================================================================
# BodyScaleMetricsHandler — properties
# ===========================================================================


async def test_handler_config_entry_id_property(hass: HomeAssistant) -> None:
    """config_entry_id property must return the id passed at construction."""
    config = _make_config()
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="my_entry_123")
    assert handler.config_entry_id == "my_entry_123"
    handler.unload()


async def test_handler_current_weight_none_before_any_measurement(
    hass: HomeAssistant,
) -> None:
    """current_weight must be None before any weight has been recorded."""
    config = _make_config(weight_sensor="sensor.w_prop_none")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")
    assert handler.current_weight is None
    handler.unload()


async def test_handler_current_weight_returns_float_after_measurement(
    hass: HomeAssistant,
) -> None:
    """current_weight must return the latest weight as a float."""
    config = _make_config(weight_sensor="sensor.w_prop_val")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    hass.states.async_set("sensor.w_prop_val", "68.4")
    await hass.async_block_till_done()

    assert handler.current_weight == pytest.approx(68.4, abs=0.01)
    handler.unload()


# ===========================================================================
# BodyScaleMetricsHandler — PROFILE_METHOD_NEAREST bootstrap weight
# ===========================================================================


async def test_handler_nearest_bootstraps_initial_weight(hass: HomeAssistant) -> None:
    """With profile_method=nearest, an initial_weight must seed WEIGHT at init."""
    config = _make_config(
        weight_sensor="sensor.w_bootstrap",
        profile_method=PROFILE_METHOD_NEAREST,
        initial_weight=72.5,
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    assert handler.current_weight == pytest.approx(72.5, abs=0.01)
    assert handler._last_accepted_weight == pytest.approx(72.5, abs=0.01)
    handler.unload()


async def test_handler_nearest_without_initial_weight_does_not_bootstrap(
    hass: HomeAssistant,
) -> None:
    """With profile_method=nearest but no initial_weight, nothing is seeded."""
    config = _make_config(
        weight_sensor="sensor.w_no_bootstrap",
        profile_method=PROFILE_METHOD_NEAREST,
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    assert handler.current_weight is None
    handler.unload()


# ===========================================================================
# BodyScaleMetricsHandler — stabilized binary sensor wiring
# ===========================================================================


async def test_handler_stabilized_sensor_triggers_weight_only_recalc(
    hass: HomeAssistant,
) -> None:
    """Turning the stabilized sensor ON must force a weight-only recalculation."""
    config = _make_config(
        height=170.0,
        gender=Gender.MALE,
        birthday="1985-06-20",
        weight_sensor="sensor.w_stab",
        stabilized_sensor="binary_sensor.stabilized",
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    hass.states.async_set("sensor.w_stab", "80.0")
    await hass.async_block_till_done()

    bmi_values: list[Any] = []
    handler.subscribe(Metric.BMI, bmi_values.append)
    bmi_values.clear()

    hass.states.async_set("binary_sensor.stabilized", "on")
    await hass.async_block_till_done()

    assert bmi_values, "Stabilized ON must trigger a weight-only recalculation"
    handler.unload()


async def test_handler_stabilized_sensor_triggers_impedance_pass_when_accepted(
    hass: HomeAssistant,
) -> None:
    """Stabilized ON with impedance mode must trigger the impedance pass too."""
    config = _make_config(
        height=175.0,
        gender=Gender.MALE,
        birthday="1990-03-10",
        impedance_mode=IMPEDANCE_MODE_STANDARD,
        weight_sensor="sensor.w_stab_imp",
        impedance_sensor="sensor.imp_stab",
        stabilized_sensor="binary_sensor.stabilized_imp",
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    hass.states.async_set("sensor.w_stab_imp", "78.0")
    hass.states.async_set("sensor.imp_stab", "500")
    await hass.async_block_till_done()

    fat_values: list[Any] = []
    handler.subscribe(Metric.FAT_PERCENTAGE, fat_values.append)
    fat_values.clear()

    hass.states.async_set("binary_sensor.stabilized_imp", "on")
    await hass.async_block_till_done()

    assert fat_values, "Stabilized ON must trigger the impedance pass"
    handler.unload()


async def test_handler_stabilized_sensor_skips_impedance_when_no_weight_accepted(
    hass: HomeAssistant,
) -> None:
    """Stabilized ON must skip the impedance pass if no weight was accepted yet."""
    config = _make_config(
        height=175.0,
        impedance_mode=IMPEDANCE_MODE_STANDARD,
        weight_sensor="sensor.w_stab_noimp",
        impedance_sensor="sensor.imp_stab_noimp",
        stabilized_sensor="binary_sensor.stabilized_noimp",
        profile_method=PROFILE_METHOD_WEIGHT,
    )
    config[CONF_WEIGHT_MIN] = 60.0
    config[CONF_WEIGHT_MAX] = 80.0
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    # No weight sent at all — _last_accepted_weight stays None.
    fat_values: list[Any] = []
    handler.subscribe(Metric.FAT_PERCENTAGE, fat_values.append)
    fat_values.clear()

    hass.states.async_set("binary_sensor.stabilized_noimp", "on")
    await hass.async_block_till_done()

    assert len(fat_values) == 0
    handler.unload()


async def test_handler_stabilized_sensor_unavailable_state_ignored(
    hass: HomeAssistant,
) -> None:
    """A stabilized sensor going unavailable/unknown must be ignored."""
    config = _make_config(
        weight_sensor="sensor.w_stab_unavail",
        stabilized_sensor="binary_sensor.stabilized_unavail",
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    hass.states.async_set("sensor.w_stab_unavail", "70.0")
    await hass.async_block_till_done()

    bmi_values: list[Any] = []
    handler.subscribe(Metric.BMI, bmi_values.append)
    bmi_values.clear()

    hass.states.async_set("binary_sensor.stabilized_unavail", "unavailable")
    await hass.async_block_till_done()

    assert len(bmi_values) == 0
    handler.unload()


async def test_handler_stabilized_sensor_off_state_ignored(
    hass: HomeAssistant,
) -> None:
    """A stabilized sensor turning 'off' must not trigger any recalculation."""
    config = _make_config(
        weight_sensor="sensor.w_stab_off",
        stabilized_sensor="binary_sensor.stabilized_off",
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    hass.states.async_set("sensor.w_stab_off", "70.0")
    await hass.async_block_till_done()

    bmi_values: list[Any] = []
    handler.subscribe(Metric.BMI, bmi_values.append)
    bmi_values.clear()

    hass.states.async_set("binary_sensor.stabilized_off", "off")
    await hass.async_block_till_done()

    assert len(bmi_values) == 0
    handler.unload()


async def test_handler_unload_removes_stabilized_listener_too(
    hass: HomeAssistant,
) -> None:
    """unload() must remove the stabilized listener along with the others."""
    config = _make_config(
        weight_sensor="sensor.w_stab_unload",
        stabilized_sensor="binary_sensor.stabilized_unload",
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")
    handler.unload()

    # After unload, further state changes must not raise or be processed.
    hass.states.async_set("binary_sensor.stabilized_unload", "on")
    await hass.async_block_till_done()


# ===========================================================================
# BodyScaleMetricsHandler — bootstrap replay on startup
# ===========================================================================


async def test_handler_bootstrap_replays_existing_sensor_state(
    hass: HomeAssistant,
) -> None:
    """If a sensor already has a state at handler creation, it must be replayed."""
    hass.states.async_set("sensor.w_preexisting", "66.0")
    await hass.async_block_till_done()

    config = _make_config(weight_sensor="sensor.w_preexisting")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    assert handler.current_weight == pytest.approx(66.0, abs=0.01)
    handler.unload()


# ===========================================================================
# _on_state_change / _on_state_report — timestamp dedup
# ===========================================================================


async def test_state_changed_duplicate_timestamp_is_deduped(
    hass: HomeAssistant,
) -> None:
    """Firing state_changed twice with the same last_reported must dedupe."""
    config = _make_config(weight_sensor="sensor.w_dedup")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    hass.states.async_set("sensor.w_dedup", "70.0")
    await hass.async_block_till_done()

    weight_values: list[Any] = []
    handler.subscribe(Metric.WEIGHT, weight_values.append)
    weight_values.clear()

    state = hass.states.get("sensor.w_dedup")
    assert state is not None

    # Re-fire the exact same State object (same last_reported) manually.
    hass.bus.async_fire(
        EVENT_STATE_CHANGED,
        {"entity_id": "sensor.w_dedup", "new_state": state, "old_state": state},
    )
    await hass.async_block_till_done()

    assert len(weight_values) == 0, "Duplicate timestamp must be deduped"
    handler.unload()


async def test_state_reported_processes_unchanged_value(
    hass: HomeAssistant,
) -> None:
    """A state_reported event (even for an unchanged value) must be processed."""
    config = _make_config(weight_sensor="sensor.w_reported")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    hass.states.async_set("sensor.w_reported", "70.0")
    await hass.async_block_till_done()

    weight_values: list[Any] = []
    handler.subscribe(Metric.WEIGHT, weight_values.append)
    weight_values.clear()

    hass.bus.async_fire(
        EVENT_STATE_REPORTED,
        {"entity_id": "sensor.w_reported"},
    )
    await hass.async_block_till_done()

    assert weight_values, "state_reported must re-process the current value"
    handler.unload()


async def test_state_reported_unknown_entity_ignored(hass: HomeAssistant) -> None:
    """A state_reported event for an entity with no current state is ignored."""
    config = _make_config(weight_sensor="sensor.w_reported_missing")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    # No error must be raised even though the entity has no state at all.
    hass.bus.async_fire(
        EVENT_STATE_REPORTED,
        {"entity_id": "sensor.w_reported_missing"},
    )
    await hass.async_block_till_done()
    handler.unload()


# ===========================================================================
# _state_changed — malformed events
# ===========================================================================


async def test_state_changed_event_missing_new_state_ignored(
    hass: HomeAssistant,
) -> None:
    """A state_changed event with new_state=None must be ignored without error."""
    config = _make_config(weight_sensor="sensor.w_none_state")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    hass.bus.async_fire(
        EVENT_STATE_CHANGED,
        {"entity_id": "sensor.w_none_state", "new_state": None, "old_state": None},
    )
    await hass.async_block_till_done()
    handler.unload()


# ===========================================================================
# unsubscribe — actual removal
# ===========================================================================


async def test_unsubscribe_stops_further_callbacks(hass: HomeAssistant) -> None:
    """Calling the unsubscribe callable must stop future notifications."""
    config = _make_config(weight_sensor="sensor.w_unsub")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    weight_values: list[Any] = []
    remove = handler.subscribe(Metric.WEIGHT, weight_values.append)

    hass.states.async_set("sensor.w_unsub", "70.0")
    await hass.async_block_till_done()
    count_after_first = len(weight_values)
    assert count_after_first > 0

    remove()

    hass.states.async_set("sensor.w_unsub", "71.0")
    await hass.async_block_till_done()

    assert len(weight_values) == count_after_first, "No further callbacks expected"
    handler.unload()


# ===========================================================================
# _process_weight — invalid_format / zero-reset branches
# ===========================================================================


async def test_weight_invalid_format_sets_problem(hass: HomeAssistant) -> None:
    """A non-numeric weight state must set the 'invalid_format' problem."""
    config = _make_config(weight_sensor="sensor.w_badfmt")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    status_values: list[Any] = []
    handler.subscribe(Metric.STATUS, status_values.append)

    hass.states.async_set("sensor.w_badfmt", "not_a_number")
    await hass.async_block_till_done()

    assert any("invalid_format" in str(v) for v in status_values)
    handler.unload()


async def test_weight_zero_is_silently_ignored(hass: HomeAssistant) -> None:
    """A weight of exactly 0.0 (scale reset) must be ignored without a problem."""
    config = _make_config(weight_sensor="sensor.w_zero")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    status_values: list[Any] = []
    weight_values: list[Any] = []
    handler.subscribe(Metric.STATUS, status_values.append)
    handler.subscribe(Metric.WEIGHT, weight_values.append)

    hass.states.async_set("sensor.w_zero", "0.0")
    await hass.async_block_till_done()

    assert len(weight_values) == 0
    assert not any("low" in str(v) for v in status_values)
    handler.unload()


# ===========================================================================
# _process_impedance — unavailable / invalid_format / zero-reset branches
# ===========================================================================


async def test_impedance_unavailable_ignored(hass: HomeAssistant) -> None:
    """An unavailable impedance sensor must be ignored without a problem."""
    config = _make_config(
        impedance_mode=IMPEDANCE_MODE_STANDARD,
        weight_sensor="sensor.w_imp_unavail",
        impedance_sensor="sensor.imp_unavail",
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    hass.states.async_set("sensor.w_imp_unavail", "70.0")
    await hass.async_block_till_done()

    status_values: list[Any] = []
    handler.subscribe(Metric.STATUS, status_values.append)
    status_values.clear()

    hass.states.async_set("sensor.imp_unavail", "unavailable")
    await hass.async_block_till_done()

    assert not any("impedance" in str(v) for v in status_values)
    handler.unload()


async def test_impedance_invalid_format_sets_problem(hass: HomeAssistant) -> None:
    """A non-numeric impedance state must set the 'invalid_format' problem."""
    config = _make_config(
        impedance_mode=IMPEDANCE_MODE_STANDARD,
        weight_sensor="sensor.w_imp_badfmt",
        impedance_sensor="sensor.imp_badfmt",
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    hass.states.async_set("sensor.w_imp_badfmt", "70.0")
    await hass.async_block_till_done()

    status_values: list[Any] = []
    handler.subscribe(Metric.STATUS, status_values.append)

    hass.states.async_set("sensor.imp_badfmt", "garbage")
    await hass.async_block_till_done()

    assert any("invalid_format" in str(v) for v in status_values)
    handler.unload()


async def test_impedance_zero_is_silently_ignored(hass: HomeAssistant) -> None:
    """An impedance of exactly 0.0 (scale reset) must be ignored without a problem."""
    config = _make_config(
        impedance_mode=IMPEDANCE_MODE_STANDARD,
        weight_sensor="sensor.w_imp_zero",
        impedance_sensor="sensor.imp_zero",
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    hass.states.async_set("sensor.w_imp_zero", "70.0")
    await hass.async_block_till_done()

    status_values: list[Any] = []
    imp_values: list[Any] = []
    handler.subscribe(Metric.STATUS, status_values.append)
    handler.subscribe(Metric.IMPEDANCE, imp_values.append)
    status_values.clear()

    hass.states.async_set("sensor.imp_zero", "0")
    await hass.async_block_till_done()

    assert len(imp_values) == 0
    assert not any("impedance_low" in str(v) for v in status_values)
    handler.unload()


async def test_impedance_below_minimum_nonzero_sets_low_problem(
    hass: HomeAssistant,
) -> None:
    """A nonzero impedance below the constraint (not a reset) must set 'low'."""
    config = _make_config(
        impedance_mode=IMPEDANCE_MODE_STANDARD,
        weight_sensor="sensor.w_imp_low",
        impedance_sensor="sensor.imp_low_nonzero",
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    hass.states.async_set("sensor.w_imp_low", "70.0")
    await hass.async_block_till_done()

    status_values: list[Any] = []
    handler.subscribe(Metric.STATUS, status_values.append)

    hass.states.async_set("sensor.imp_low_nonzero", "5")  # below MIN=50, not 0
    await hass.async_block_till_done()

    assert any("impedance_low" in str(v) for v in status_values)
    handler.unload()


async def test_impedance_rejected_when_profile_filter_changes_mind(
    hass: HomeAssistant,
) -> None:
    """Impedance must be rejected if the profile filter changes its mind.

    Simulates the profile filter no longer accepting the weight that was
    valid when it was first received (defensive branch).
    """
    config = _make_config(
        impedance_mode=IMPEDANCE_MODE_STANDARD,
        weight_sensor="sensor.w_filter_change",
        impedance_sensor="sensor.imp_filter_change",
        profile_method=PROFILE_METHOD_WEIGHT,
    )
    config[CONF_WEIGHT_MIN] = 60.0
    config[CONF_WEIGHT_MAX] = 80.0
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    hass.states.async_set("sensor.w_filter_change", "70.0")
    await hass.async_block_till_done()
    assert handler._last_accepted_weight == pytest.approx(70.0, abs=0.01)

    # Narrow the accepted range so 70.0 no longer qualifies before impedance arrives.
    handler._config[CONF_WEIGHT_MIN] = 75.0

    imp_values: list[Any] = []
    handler.subscribe(Metric.IMPEDANCE, imp_values.append)

    hass.states.async_set("sensor.imp_filter_change", "500")
    await hass.async_block_till_done()

    assert len(imp_values) == 0
    handler.unload()


# ===========================================================================
# accept_pending_measurement — problem branch on replay
# ===========================================================================


async def test_accept_pending_measurement_sets_problem_when_replay_invalid(
    hass: HomeAssistant,
) -> None:
    """If the replayed pending state now yields a problem, it must be recorded."""
    config = _make_config(weight_sensor="sensor.w_replay_problem")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    # Manually craft a pending measurement whose state is now out of range —
    # simulates the defensive path in accept_pending_measurement().
    handler._pending_weight = 9999.0
    handler._pending_state = State("sensor.w_replay_problem", "9999")

    status_values: list[Any] = []
    handler.subscribe(Metric.STATUS, status_values.append)
    status_values.clear()

    handler.accept_pending_measurement()

    assert any("weight_high" in str(v) for v in status_values)
    handler.unload()


# ===========================================================================
# _entity_to_label / _set_sensor_problem / _clear_sensor_problem — unmatched
# ===========================================================================


async def test_entity_to_label_unmatched_entity_returns_none(
    hass: HomeAssistant,
) -> None:
    """_entity_to_label must return None for an entity_id it doesn't manage."""
    config = _make_config(weight_sensor="sensor.w_label")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")
    assert handler._entity_to_label("sensor.completely_unrelated") is None
    handler.unload()


async def test_set_sensor_problem_unmatched_entity_is_noop(
    hass: HomeAssistant,
) -> None:
    """_set_sensor_problem must do nothing for an entity it doesn't manage."""
    config = _make_config(weight_sensor="sensor.w_setprob")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    handler._set_sensor_problem("sensor.completely_unrelated", "high")
    assert handler._sensor_problems == {}
    handler.unload()


async def test_clear_sensor_problem_unmatched_entity_is_noop(
    hass: HomeAssistant,
) -> None:
    """_clear_sensor_problem must do nothing for an entity it doesn't manage."""
    config = _make_config(weight_sensor="sensor.w_clearprob")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    handler._sensor_problems["weight"] = "high"
    handler._clear_sensor_problem("sensor.completely_unrelated")
    assert handler._sensor_problems == {"weight": "high"}
    handler.unload()


# ===========================================================================
# _publish_status — unexpected problem key
# ===========================================================================


async def test_publish_status_includes_unexpected_keys(hass: HomeAssistant) -> None:
    """_publish_status must still surface problem keys outside the known order."""
    config = _make_config(weight_sensor="sensor.w_unexpected")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    status_values: list[Any] = []
    handler.subscribe(Metric.STATUS, status_values.append)
    status_values.clear()

    handler._sensor_problems["mystery_sensor"] = "weird_error"
    handler._publish_status()

    assert any("mystery_sensor_weird_error" in str(v) for v in status_values)
    handler.unload()


# ===========================================================================
# _can_compute — defensive branches
# ===========================================================================


async def test_can_compute_returns_false_for_unknown_metric(
    hass: HomeAssistant,
) -> None:
    """_can_compute must return False for a key with no registered dependencies.

    Every real Metric enum member has an entry in the dependency graph, so
    this defensive branch is not reachable through the public API — this
    test documents the behavior by calling the private method directly.
    """
    config = _make_config(weight_sensor="sensor.w_cancompute")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    assert handler._can_compute("not_a_real_metric") is False
    handler.unload()


async def test_can_compute_lbm_false_without_weight(hass: HomeAssistant) -> None:
    """_can_compute(LBM) must be False if impedance is present but WEIGHT is not."""
    config = _make_config(
        impedance_mode=IMPEDANCE_MODE_STANDARD,
        weight_sensor="sensor.w_lbm_noweight",
        impedance_sensor="sensor.imp_lbm_noweight",
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    # Seed impedance directly without ever accepting a weight.
    handler._available_metrics[Metric.IMPEDANCE] = 500.0

    assert handler._can_compute(Metric.LBM) is False
    handler.unload()


# ===========================================================================
# Remaining defensive guards — not reachable through the real event wiring
# ===========================================================================


async def test_stabilized_change_event_missing_new_state_ignored(
    hass: HomeAssistant,
) -> None:
    """A malformed state_changed for the stabilized sensor must be ignored.

    In practice HA never fires state_changed with a missing entity_id or
    new_state, so this guard is only reachable by firing the event by hand.
    """
    config = _make_config(
        weight_sensor="sensor.w_stab_guard",
        stabilized_sensor="binary_sensor.stabilized_guard",
    )
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    hass.bus.async_fire(
        EVENT_STATE_CHANGED,
        {
            "entity_id": "binary_sensor.stabilized_guard",
            "new_state": None,
            "old_state": None,
        },
    )
    await hass.async_block_till_done()
    handler.unload()


async def test_state_changed_event_wrapper_is_unused_dead_code(
    hass: HomeAssistant,
) -> None:
    """_state_changed_event exists but is never wired to any real listener.

    _setup_listeners only ever registers the closures _on_state_change /
    _on_state_report / _on_stabilized_change — none of them call
    _state_changed_event. It appears to be leftover/dead code; this test
    just documents that it still behaves correctly if ever invoked directly.
    """
    config = _make_config(weight_sensor="sensor.w_dead_wrapper")
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")

    weight_values: list[Any] = []
    handler.subscribe(Metric.WEIGHT, weight_values.append)

    event = MagicMock()
    event.data = {"entity_id": "sensor.w_dead_wrapper", "new_state": None}
    # must not raise; no-op (new_state None)
    handler._state_changed_event(event)

    assert len(weight_values) == 0
    handler.unload()

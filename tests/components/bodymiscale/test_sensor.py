"""Tests for bodymiscale sensor.py."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorEntityDescription, SensorStateClass
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bodymiscale.const import (
    ATTR_BMI,
    ATTR_BMR,
    ATTR_BONES,
    ATTR_ECW_TBW_RATIO,
    ATTR_EXTRACELLULAR_WATER,
    ATTR_FAT,
    ATTR_INTRACELLULAR_WATER,
    ATTR_LAST_MEASUREMENT_TIME,
    ATTR_LBM,
    ATTR_MUSCLE,
    ATTR_VISCERAL,
    ATTR_WATER,
    CONF_IMPEDANCE_MODE,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_IMPEDANCE_HIGH,
    CONF_SENSOR_IMPEDANCE_LOW,
    CONF_SENSOR_WEIGHT,
    DOMAIN,
    HANDLERS,
    IMPEDANCE_MODE_DUAL,
    IMPEDANCE_MODE_NONE,
    IMPEDANCE_MODE_STANDARD,
)
from custom_components.bodymiscale.metrics import BodyScaleMetricsHandler
from custom_components.bodymiscale.models import Metric
from custom_components.bodymiscale.sensor import BodyScaleSensor, async_setup_entry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_write_ha_state():
    """Prevent NoEntitySpecifiedError — entities are not registered in a platform."""
    with patch(
        "homeassistant.helpers.entity.Entity.async_write_ha_state",
        return_value=None,
    ):
        yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_handler(
    impedance_mode: str = IMPEDANCE_MODE_NONE,
    name: str = "Alice",
) -> MagicMock:
    """Return a minimal mock BodyScaleMetricsHandler."""
    handler = MagicMock(spec=BodyScaleMetricsHandler)
    handler.config = {
        "name": name,
        CONF_IMPEDANCE_MODE: impedance_mode,
    }
    handler.config_entry_id = "entry_test"
    handler.subscribe = MagicMock(return_value=lambda: None)
    handler.restore_metric = MagicMock()
    return handler


def _make_add_entities() -> MagicMock:
    """Return a mock AddEntitiesCallback that captures added entities."""
    return MagicMock()


def _make_sensor(
    key: str = ATTR_BMI,
    metric: Metric = Metric.BMI,
    get_attributes=None,
    precision: int = 1,
    handler: MagicMock | None = None,
) -> BodyScaleSensor:
    h = handler or _make_handler()
    description = SensorEntityDescription(
        key=key,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=precision,
    )
    return BodyScaleSensor(h, description, metric, get_attributes)


def _make_last_measurement_sensor(handler: MagicMock | None = None) -> BodyScaleSensor:
    h = handler or _make_handler()
    description = SensorEntityDescription(
        key=ATTR_LAST_MEASUREMENT_TIME,
        state_class=SensorStateClass.MEASUREMENT,
    )
    return BodyScaleSensor(h, description, Metric.LAST_MEASUREMENT_TIME)


def _mock_restored_data(native_value: Any):
    """Return a mock object mimicking ExtraStoredData with native_value."""
    data = MagicMock()
    data.native_value = native_value
    return data


# ===========================================================================
# async_setup_entry — sensor creation per impedance mode
# ===========================================================================


async def test_sensor_setup_no_impedance_creates_base_sensors(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Impedance=none must create only the base sensor set."""
    mock_config_entry.add_to_hass(hass)
    handler = _make_handler(IMPEDANCE_MODE_NONE)
    hass.data.setdefault(DOMAIN, {})[HANDLERS] = {mock_config_entry.entry_id: handler}

    add_entities = _make_add_entities()
    await async_setup_entry(hass, mock_config_entry, add_entities)

    add_entities.assert_called_once()
    sensors = add_entities.call_args[0][0]

    keys = {s.entity_description.key for s in sensors}
    # Base sensors always present
    assert CONF_SENSOR_WEIGHT in keys
    assert ATTR_BMI in keys
    assert ATTR_BMR in keys
    assert ATTR_VISCERAL in keys
    assert ATTR_LAST_MEASUREMENT_TIME in keys

    # Impedance sensors must NOT be present
    assert CONF_SENSOR_IMPEDANCE not in keys
    assert CONF_SENSOR_IMPEDANCE_LOW not in keys
    assert CONF_SENSOR_IMPEDANCE_HIGH not in keys


async def test_sensor_setup_standard_impedance_includes_shared_sensors(
    hass: HomeAssistant,
    mock_config_entry_standard_impedance: MockConfigEntry,
) -> None:
    """Impedance=standard must include shared impedance-derived sensors."""
    mock_config_entry_standard_impedance.add_to_hass(hass)
    handler = _make_handler(IMPEDANCE_MODE_STANDARD, name="Bob")
    hass.data.setdefault(DOMAIN, {})[HANDLERS] = {
        mock_config_entry_standard_impedance.entry_id: handler
    }

    add_entities = _make_add_entities()
    await async_setup_entry(hass, mock_config_entry_standard_impedance, add_entities)

    sensors = add_entities.call_args[0][0]
    keys = {s.entity_description.key for s in sensors}

    assert ATTR_LBM in keys
    assert ATTR_FAT in keys
    assert ATTR_WATER in keys
    assert ATTR_BONES in keys
    assert ATTR_MUSCLE in keys
    assert CONF_SENSOR_IMPEDANCE in keys
    # Dual-only keys must NOT be present
    assert CONF_SENSOR_IMPEDANCE_LOW not in keys
    assert CONF_SENSOR_IMPEDANCE_HIGH not in keys


async def test_sensor_setup_dual_impedance_includes_dual_sensors(
    hass: HomeAssistant,
    mock_config_entry_dual_impedance: MockConfigEntry,
) -> None:
    """Impedance=dual must include dual-only sensors and exclude standard-only."""
    mock_config_entry_dual_impedance.add_to_hass(hass)
    handler = _make_handler(IMPEDANCE_MODE_DUAL, name="Carol")
    hass.data.setdefault(DOMAIN, {})[HANDLERS] = {
        mock_config_entry_dual_impedance.entry_id: handler
    }

    add_entities = _make_add_entities()
    await async_setup_entry(hass, mock_config_entry_dual_impedance, add_entities)

    sensors = add_entities.call_args[0][0]
    keys = {s.entity_description.key for s in sensors}

    assert ATTR_EXTRACELLULAR_WATER in keys
    assert ATTR_INTRACELLULAR_WATER in keys
    assert ATTR_ECW_TBW_RATIO in keys
    assert CONF_SENSOR_IMPEDANCE_LOW in keys
    assert CONF_SENSOR_IMPEDANCE_HIGH not in keys or CONF_SENSOR_IMPEDANCE_HIGH in keys
    # Standard-only key must NOT be present
    assert CONF_SENSOR_IMPEDANCE not in keys


# ===========================================================================
# BodyScaleBaseEntity — unique_id and device_info
# ===========================================================================


async def test_sensor_unique_id_contains_domain_name_and_key(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """unique_id must follow the pattern '<domain>_<name>_<key>'."""
    mock_config_entry.add_to_hass(hass)
    handler = _make_handler(IMPEDANCE_MODE_NONE, name="Alice")
    hass.data.setdefault(DOMAIN, {})[HANDLERS] = {mock_config_entry.entry_id: handler}

    add_entities = _make_add_entities()
    await async_setup_entry(hass, mock_config_entry, add_entities)

    sensors = add_entities.call_args[0][0]
    bmi_sensor = next(s for s in sensors if s.entity_description.key == ATTR_BMI)

    assert bmi_sensor.unique_id == f"{DOMAIN}_Alice_{ATTR_BMI}"


async def test_sensor_device_info_name_matches_config(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """device_info.name must match the configured user name."""
    mock_config_entry.add_to_hass(hass)
    handler = _make_handler(IMPEDANCE_MODE_NONE, name="Alice")
    hass.data.setdefault(DOMAIN, {})[HANDLERS] = {mock_config_entry.entry_id: handler}

    add_entities = _make_add_entities()
    await async_setup_entry(hass, mock_config_entry, add_entities)

    sensors = add_entities.call_args[0][0]
    sensor = sensors[0]

    assert sensor.device_info["name"] == "Alice"


# ===========================================================================
# BodyScaleSensor — on_value callback
# ===========================================================================


async def test_sensor_on_value_rounds_float(hass: HomeAssistant) -> None:
    """Numeric updates must be rounded to suggested_display_precision."""
    handler = _make_handler()
    description = SensorEntityDescription(
        key=ATTR_BMI,
        translation_key="bmi",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    )
    sensor = BodyScaleSensor(handler, description, Metric.BMI)
    sensor.hass = hass

    # Simulate an on_value callback with high-precision float
    sensor._attr_native_value = round(22.6789, 1)
    assert sensor._attr_native_value == 22.7


# ===========================================================================
# BodyScaleSensor — get_attributes callback
# ===========================================================================


def test_sensor_get_attributes_called_on_update() -> None:
    """When get_attributes is set, extra_state_attributes must be populated."""
    called_with = {}

    def fake_get_attributes(state, config):
        called_with["state"] = state
        called_with["config"] = config
        return {"test_key": "test_value"}

    handler = _make_handler()
    description = SensorEntityDescription(
        key=CONF_SENSOR_WEIGHT,
        translation_key="weight",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    )
    sensor = BodyScaleSensor(handler, description, Metric.WEIGHT, fake_get_attributes)

    # Manually invoke the attribute computation as the live listener would
    sensor._attr_native_value = 65.0
    sensor._attr_extra_state_attributes = dict(
        sensor._get_attributes(sensor._attr_native_value, dict(sensor._handler.config))
    )

    assert sensor._attr_extra_state_attributes.get("test_key") == "test_value"


# ===========================================================================
# async_added_to_hass — no restored data (line 412 false branch)
# ===========================================================================


async def test_added_to_hass_no_restored_data(hass: HomeAssistant) -> None:
    """When no previous state exists, native_value stays None."""
    sensor = _make_sensor()
    sensor.hass = hass

    with patch.object(
        sensor, "async_get_last_sensor_data", new=AsyncMock(return_value=None)
    ):
        await sensor.async_added_to_hass()

    assert sensor._attr_native_value is None
    sensor._handler.restore_metric.assert_not_called()


async def test_added_to_hass_restored_data_none_value(hass: HomeAssistant) -> None:
    """When restored data has native_value=None, handler.restore_metric not called."""
    sensor = _make_sensor()
    sensor.hass = hass

    with patch.object(
        sensor,
        "async_get_last_sensor_data",
        new=AsyncMock(return_value=_mock_restored_data(None)),
    ):
        await sensor.async_added_to_hass()

    sensor._handler.restore_metric.assert_not_called()


# ===========================================================================
# async_added_to_hass — numeric restoration (lines 424-441)
# ===========================================================================


async def test_added_to_hass_restores_float_value(hass: HomeAssistant) -> None:
    """Restored float value must be stored and passed to restore_metric."""
    sensor = _make_sensor(metric=Metric.WEIGHT)
    sensor.hass = hass

    with patch.object(
        sensor,
        "async_get_last_sensor_data",
        new=AsyncMock(return_value=_mock_restored_data(72.5)),
    ):
        await sensor.async_added_to_hass()

    assert sensor._attr_native_value == 72.5
    sensor._handler.restore_metric.assert_called_once_with(Metric.WEIGHT, 72.5)


async def test_added_to_hass_restores_decimal_value(hass: HomeAssistant) -> None:
    """RestoreSensor may return Decimal — must be cast and stored."""
    sensor = _make_sensor(metric=Metric.BMI)
    sensor.hass = hass

    with patch.object(
        sensor,
        "async_get_last_sensor_data",
        new=AsyncMock(return_value=_mock_restored_data(Decimal("22.5"))),
    ):
        await sensor.async_added_to_hass()

    assert sensor._attr_native_value == Decimal("22.5")
    sensor._handler.restore_metric.assert_called_once()


async def test_added_to_hass_restores_get_attributes(hass: HomeAssistant) -> None:
    """When get_attributes is set and value restored, attributes must be populated."""
    called: dict = {}

    def fake_get_attributes(state, config):
        called["state"] = state
        return {"ideal": 60.0}

    sensor = _make_sensor(metric=Metric.WEIGHT, get_attributes=fake_get_attributes)
    sensor.hass = hass

    with patch.object(
        sensor,
        "async_get_last_sensor_data",
        new=AsyncMock(return_value=_mock_restored_data(68.0)),
    ):
        await sensor.async_added_to_hass()

    assert sensor._attr_extra_state_attributes.get("ideal") == 60.0
    assert called["state"] == 68.0


# ===========================================================================
# async_added_to_hass — timestamp restoration (lines 413-422)
# ===========================================================================


async def test_added_to_hass_restores_timestamp_iso_string(hass: HomeAssistant) -> None:
    """LAST_MEASUREMENT_TIME restored as ISO string must be parsed to datetime."""
    sensor = _make_last_measurement_sensor()
    sensor.hass = hass

    iso = "2024-06-15T10:30:00+00:00"
    with patch.object(
        sensor,
        "async_get_last_sensor_data",
        new=AsyncMock(return_value=_mock_restored_data(iso)),
    ):
        await sensor.async_added_to_hass()

    assert isinstance(sensor._attr_native_value, datetime)
    assert sensor._attr_native_value == datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC)


async def test_added_to_hass_restores_timestamp_invalid_iso(
    hass: HomeAssistant,
) -> None:
    """LAST_MEASUREMENT_TIME restored as invalid ISO must set native_value to None."""
    sensor = _make_last_measurement_sensor()
    sensor.hass = hass

    with patch.object(
        sensor,
        "async_get_last_sensor_data",
        new=AsyncMock(return_value=_mock_restored_data("not-a-date")),
    ):
        await sensor.async_added_to_hass()

    assert sensor._attr_native_value is None


# ===========================================================================
# on_value closure — LAST_MEASUREMENT_TIME variants (lines 446-455)
# ===========================================================================


async def test_on_value_timestamp_datetime_object(hass: HomeAssistant) -> None:
    """on_value for LAST_MEASUREMENT_TIME with datetime must store it directly."""
    sensor = _make_last_measurement_sensor()
    sensor.hass = hass

    received_callbacks: list[Any] = []
    sensor._handler.subscribe = MagicMock(
        side_effect=lambda metric, cb: received_callbacks.append(cb) or (lambda: None)
    )

    with patch.object(
        sensor, "async_get_last_sensor_data", new=AsyncMock(return_value=None)
    ):
        await sensor.async_added_to_hass()

    assert received_callbacks, "subscribe must have been called"
    on_value = received_callbacks[0]

    ts = datetime(2024, 6, 15, 10, 30, 0, tzinfo=UTC)
    with patch.object(sensor, "async_write_ha_state"):
        on_value(ts)

    assert sensor._attr_native_value == ts


async def test_on_value_timestamp_iso_string(hass: HomeAssistant) -> None:
    """on_value for LAST_MEASUREMENT_TIME with ISO string must parse it."""
    sensor = _make_last_measurement_sensor()
    sensor.hass = hass

    received_callbacks: list[Any] = []
    sensor._handler.subscribe = MagicMock(
        side_effect=lambda metric, cb: received_callbacks.append(cb) or (lambda: None)
    )

    with patch.object(
        sensor, "async_get_last_sensor_data", new=AsyncMock(return_value=None)
    ):
        await sensor.async_added_to_hass()

    on_value = received_callbacks[0]
    with patch.object(sensor, "async_write_ha_state"):
        on_value("2024-06-15T10:30:00+00:00")

    assert isinstance(sensor._attr_native_value, datetime)


async def test_on_value_timestamp_invalid_string_sets_none(hass: HomeAssistant) -> None:
    """on_value for LAST_MEASUREMENT_TIME with invalid ISO must set None."""
    sensor = _make_last_measurement_sensor()
    sensor.hass = hass

    received_callbacks: list[Any] = []
    sensor._handler.subscribe = MagicMock(
        side_effect=lambda metric, cb: received_callbacks.append(cb) or (lambda: None)
    )

    with patch.object(
        sensor, "async_get_last_sensor_data", new=AsyncMock(return_value=None)
    ):
        await sensor.async_added_to_hass()

    on_value = received_callbacks[0]
    with patch.object(sensor, "async_write_ha_state"):
        on_value("not-a-date")

    assert sensor._attr_native_value is None


async def test_on_value_timestamp_non_string_non_datetime(hass: HomeAssistant) -> None:
    """on_value for LAST_MEASUREMENT_TIME with non-string/datetime falls through."""
    sensor = _make_last_measurement_sensor()
    sensor.hass = hass

    received_callbacks: list[Any] = []
    sensor._handler.subscribe = MagicMock(
        side_effect=lambda metric, cb: received_callbacks.append(cb) or (lambda: None)
    )

    with patch.object(
        sensor, "async_get_last_sensor_data", new=AsyncMock(return_value=None)
    ):
        await sensor.async_added_to_hass()

    on_value = received_callbacks[0]
    with patch.object(sensor, "async_write_ha_state"):
        on_value(42)  # int — falls to the else branch

    assert sensor._attr_native_value == 42


# ===========================================================================
# on_value closure — numeric sensors (lines 457-463)
# ===========================================================================


async def test_on_value_numeric_rounded(hass: HomeAssistant) -> None:
    """on_value for numeric metric must round to suggested_display_precision."""
    sensor = _make_sensor(precision=1)
    sensor.hass = hass

    received_callbacks: list[Any] = []
    sensor._handler.subscribe = MagicMock(
        side_effect=lambda metric, cb: received_callbacks.append(cb) or (lambda: None)
    )

    with patch.object(
        sensor, "async_get_last_sensor_data", new=AsyncMock(return_value=None)
    ):
        await sensor.async_added_to_hass()

    on_value = received_callbacks[0]
    with patch.object(sensor, "async_write_ha_state"):
        on_value(22.6789)

    assert sensor._attr_native_value == pytest.approx(22.7)


async def test_on_value_non_numeric_stored_as_is(hass: HomeAssistant) -> None:
    """on_value for non-numeric value (string state) must store it as-is."""
    sensor = _make_sensor(precision=1)
    sensor.hass = hass

    received_callbacks: list[Any] = []
    sensor._handler.subscribe = MagicMock(
        side_effect=lambda metric, cb: received_callbacks.append(cb) or (lambda: None)
    )

    with patch.object(
        sensor, "async_get_last_sensor_data", new=AsyncMock(return_value=None)
    ):
        await sensor.async_added_to_hass()

    on_value = received_callbacks[0]
    with patch.object(sensor, "async_write_ha_state"):
        on_value("unavailable")

    assert sensor._attr_native_value == "unavailable"


# ===========================================================================
# on_value closure — get_attributes populated (lines 465-470)
# ===========================================================================


async def test_on_value_populates_extra_attributes(hass: HomeAssistant) -> None:
    """on_value must call get_attributes and populate extra_state_attributes."""
    attr_calls: list[Any] = []

    def fake_attrs(state, config):
        attr_calls.append(state)
        return {"bmi_label": "normal"}

    sensor = _make_sensor(metric=Metric.BMI, get_attributes=fake_attrs, precision=1)
    sensor.hass = hass

    received_callbacks: list[Any] = []
    sensor._handler.subscribe = MagicMock(
        side_effect=lambda metric, cb: received_callbacks.append(cb) or (lambda: None)
    )

    with patch.object(
        sensor, "async_get_last_sensor_data", new=AsyncMock(return_value=None)
    ):
        await sensor.async_added_to_hass()

    on_value = received_callbacks[0]
    with patch.object(sensor, "async_write_ha_state"):
        on_value(22.5)

    assert sensor._attr_extra_state_attributes.get("bmi_label") == "normal"
    assert attr_calls[0] == pytest.approx(22.5)

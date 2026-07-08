"""Tests for bodymiscale __init__.py (setup, unload, migration)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import CONF_NAME, STATE_OK, STATE_PROBLEM, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bodymiscale.const import (
    ATTR_BMI,
    ATTR_BMILABEL,
    ATTR_FATMASSTOGAIN,
    ATTR_FATMASSTOLOSE,
    ATTR_PROBLEM,
    COMPONENT,
    CONF_BIRTHDAY,
    CONF_CALCULATION_MODE,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_IMPEDANCE_MODE,
    CONF_NOTIFY_DEVICE_ID,
    CONF_PROFILE_METHOD,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_IMPEDANCE_HIGH,
    CONF_SENSOR_IMPEDANCE_LOW,
    CONF_SENSOR_WEIGHT,
    DOMAIN,
    HANDLERS,
    IMPEDANCE_MODE_DUAL,
    IMPEDANCE_MODE_NONE,
    IMPEDANCE_MODE_STANDARD,
    MAIN_ENTITIES,
    NOTIFICATION_COORDINATOR,
    PROBLEM_NONE,
    PROFILE_METHOD_NONE,
    PROFILE_METHOD_NOTIFY,
)
from custom_components.bodymiscale.models import Gender, Metric
from custom_components.bodymiscale.profile import NotificationCoordinator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_data(
    name: str = "Alice",
    birthday: str = "1990-01-15",
    gender: Gender = Gender.FEMALE,
    height: float = 165.0,
    impedance_mode: str = IMPEDANCE_MODE_NONE,
    profile_method: str = PROFILE_METHOD_NONE,
    weight_sensor: str = "sensor.weight",
) -> dict:
    return {
        "name": name,
        CONF_BIRTHDAY: birthday,
        CONF_GENDER: gender,
        CONF_HEIGHT: height,
        CONF_CALCULATION_MODE: "xiaomi",
        CONF_IMPEDANCE_MODE: impedance_mode,
        CONF_PROFILE_METHOD: profile_method,
        CONF_SENSOR_WEIGHT: weight_sensor,
    }


def _make_domain_data(
    handler: MagicMock | None = None,
    entity: MagicMock | None = None,
    coordinator: MagicMock | None = None,
    entry_id: str = "entry_1",
) -> dict:
    h = handler or MagicMock()
    h.unload = MagicMock()
    e = entity or MagicMock()
    e.async_remove = AsyncMock()
    component = MagicMock()
    component.async_add_entities = AsyncMock()
    return {
        COMPONENT: component,
        HANDLERS: {entry_id: h},
        MAIN_ENTITIES: {entry_id: e},
        NOTIFICATION_COORDINATOR: coordinator,
    }


# ===========================================================================
# async_setup_entry
# ===========================================================================


async def test_setup_entry_registers_handler(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """async_setup_entry must register a metrics handler in hass.data."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.bodymiscale.BodyScaleMetricsHandler"
    ) as mock_handler_cls:
        mock_handler = MagicMock()
        mock_handler.profile_filter = MagicMock()
        mock_handler.config = dict(mock_config_entry.data) | dict(
            mock_config_entry.options
        )
        mock_handler_cls.return_value = mock_handler

        with (
            patch("custom_components.bodymiscale.Bodymiscale") as mock_entity_cls,
            patch(
                "custom_components.bodymiscale.EntityComponent"
            ) as mock_component_cls,
            patch.object(
                hass.config_entries,
                "async_forward_entry_setups",
                new_callable=AsyncMock,
            ),
        ):
            mock_component = MagicMock()
            mock_component.async_add_entities = AsyncMock()
            mock_component_cls.return_value = mock_component
            mock_entity = MagicMock()
            mock_entity_cls.return_value = mock_entity

            from custom_components.bodymiscale import async_setup_entry

            result = await async_setup_entry(hass, mock_config_entry)

    assert result is True
    assert DOMAIN in hass.data
    assert mock_config_entry.entry_id in hass.data[DOMAIN][HANDLERS]


async def test_setup_entry_unsupported_ha_version(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """async_setup_entry must return False when HA version is too old."""
    mock_config_entry.add_to_hass(hass)

    with patch("custom_components.bodymiscale.is_ha_supported", return_value=False):
        from custom_components.bodymiscale import async_setup_entry

        result = await async_setup_entry(hass, mock_config_entry)

    assert result is False


async def test_setup_entry_notify_profile_creates_coordinator(
    hass: HomeAssistant,
) -> None:
    """async_setup_entry with PROFILE_METHOD_NOTIFY must create a NotificationCoordinator."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Alice",
        unique_id="alice_notify",
        data={
            "name": "Alice",
            CONF_BIRTHDAY: "1990-01-15",
            CONF_GENDER: Gender.FEMALE,
            CONF_HEIGHT: 165.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NOTIFY,
            CONF_SENSOR_WEIGHT: "sensor.weight",
            CONF_NOTIFY_DEVICE_ID: "device_abc",
        },
        options={
            "name": "Alice",
            CONF_BIRTHDAY: "1990-01-15",
            CONF_GENDER: Gender.FEMALE,
            CONF_HEIGHT: 165.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NOTIFY,
            CONF_SENSOR_WEIGHT: "sensor.weight",
            CONF_NOTIFY_DEVICE_ID: "device_abc",
        },
        version=4,
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.bodymiscale.BodyScaleMetricsHandler"
        ) as mock_handler_cls,
        patch("custom_components.bodymiscale.Bodymiscale") as mock_entity_cls,
        patch("custom_components.bodymiscale.EntityComponent") as mock_component_cls,
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock
        ),
        patch("custom_components.bodymiscale.is_ha_supported", return_value=True),
    ):
        mock_component = MagicMock()
        mock_component.async_add_entities = AsyncMock()
        mock_component_cls.return_value = mock_component
        mock_handler = MagicMock()
        mock_handler.profile_filter = MagicMock()
        mock_handler.profile_filter.__class__ = __import__(
            "custom_components.bodymiscale.profile", fromlist=["NotificationFilter"]
        ).NotificationFilter
        mock_handler.config = dict(entry.data) | dict(entry.options)
        mock_handler.set_notification_coordinator = MagicMock()
        mock_handler_cls.return_value = mock_handler

        mock_entity = MagicMock()
        mock_entity_cls.return_value = mock_entity

        from custom_components.bodymiscale import async_setup_entry

        result = await async_setup_entry(hass, entry)

    assert result is True
    assert hass.data[DOMAIN][NOTIFICATION_COORDINATOR] is not None


async def test_setup_entry_notify_reuses_existing_coordinator(
    hass: HomeAssistant,
) -> None:
    """async_setup_entry must reuse an existing NotificationCoordinator."""
    existing_coordinator = MagicMock(spec=NotificationCoordinator)
    existing_coordinator.register = MagicMock()

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Bob",
        unique_id="bob_notify",
        data={
            "name": "Bob",
            CONF_BIRTHDAY: "1985-06-20",
            CONF_GENDER: Gender.MALE,
            CONF_HEIGHT: 180.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NOTIFY,
            CONF_SENSOR_WEIGHT: "sensor.weight",
            CONF_NOTIFY_DEVICE_ID: "device_xyz",
        },
        options={
            "name": "Bob",
            CONF_BIRTHDAY: "1985-06-20",
            CONF_GENDER: Gender.MALE,
            CONF_HEIGHT: 180.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NOTIFY,
            CONF_SENSOR_WEIGHT: "sensor.weight",
            CONF_NOTIFY_DEVICE_ID: "device_xyz",
        },
        version=4,
    )
    entry.add_to_hass(hass)

    mock_component = MagicMock()
    mock_component.async_add_entities = AsyncMock()
    hass.data[DOMAIN] = {
        COMPONENT: mock_component,
        HANDLERS: {},
        MAIN_ENTITIES: {},
        NOTIFICATION_COORDINATOR: existing_coordinator,
    }

    with (
        patch(
            "custom_components.bodymiscale.BodyScaleMetricsHandler"
        ) as mock_handler_cls,
        patch("custom_components.bodymiscale.Bodymiscale") as mock_entity_cls,
        patch("custom_components.bodymiscale.EntityComponent") as mock_component_cls,
        patch.object(
            hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock
        ),
        patch("custom_components.bodymiscale.is_ha_supported", return_value=True),
    ):
        mock_component.async_add_entities = AsyncMock()
        mock_component_cls.return_value = mock_component
        from custom_components.bodymiscale.profile import NotificationFilter

        mock_handler = MagicMock()
        mock_handler.profile_filter = NotificationFilter()
        mock_handler.config = dict(entry.data) | dict(entry.options)
        mock_handler.set_notification_coordinator = MagicMock()
        mock_handler_cls.return_value = mock_handler

        mock_entity = MagicMock()
        mock_entity_cls.return_value = mock_entity

        from custom_components.bodymiscale import async_setup_entry

        await async_setup_entry(hass, entry)

    assert hass.data[DOMAIN][NOTIFICATION_COORDINATOR] is existing_coordinator
    existing_coordinator.register.assert_called_once()


# ===========================================================================
# async_unload_entry
# ===========================================================================


async def test_unload_entry_cleans_up(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """async_unload_entry must remove handler and entity, pop domain data when empty."""
    mock_config_entry.add_to_hass(hass)

    mock_handler = MagicMock()
    mock_handler.unload = MagicMock()
    mock_handler.profile_filter = MagicMock()
    mock_entity = AsyncMock()
    mock_entity.async_remove = AsyncMock()

    hass.data[DOMAIN] = {
        COMPONENT: MagicMock(),
        HANDLERS: {mock_config_entry.entry_id: mock_handler},
        MAIN_ENTITIES: {mock_config_entry.entry_id: mock_entity},
        NOTIFICATION_COORDINATOR: None,
    }

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ):
        from custom_components.bodymiscale import async_unload_entry

        result = await async_unload_entry(hass, mock_config_entry)

    assert result is True
    mock_handler.unload.assert_called_once()
    mock_entity.async_remove.assert_awaited_once()
    assert DOMAIN not in hass.data


async def test_unload_entry_platform_failure_keeps_data(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """async_unload_entry must preserve hass.data when platform unload fails."""
    mock_config_entry.add_to_hass(hass)

    mock_handler = MagicMock()
    hass.data[DOMAIN] = {
        COMPONENT: MagicMock(),
        HANDLERS: {mock_config_entry.entry_id: mock_handler},
        MAIN_ENTITIES: {},
        NOTIFICATION_COORDINATOR: None,
    }

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new_callable=AsyncMock,
        return_value=False,
    ):
        from custom_components.bodymiscale import async_unload_entry

        result = await async_unload_entry(hass, mock_config_entry)

    assert result is False
    assert mock_config_entry.entry_id in hass.data[DOMAIN][HANDLERS]


async def test_unload_entry_unregisters_coordinator_and_keeps_it_alive(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """When coordinator still has entries after unregister, it must NOT be unloaded."""
    mock_config_entry.add_to_hass(hass)

    coordinator = MagicMock(spec=NotificationCoordinator)
    coordinator.unregister = MagicMock()
    coordinator.has_entries = MagicMock(return_value=True)
    coordinator.unload = MagicMock()

    hass.data[DOMAIN] = _make_domain_data(
        coordinator=coordinator, entry_id=mock_config_entry.entry_id
    )
    hass.data[DOMAIN][HANDLERS]["other_entry"] = MagicMock()

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ):
        from custom_components.bodymiscale import async_unload_entry

        result = await async_unload_entry(hass, mock_config_entry)

    assert result is True
    coordinator.unregister.assert_called_once_with(mock_config_entry.entry_id)
    coordinator.unload.assert_not_called()
    assert hass.data[DOMAIN][NOTIFICATION_COORDINATOR] is coordinator


async def test_unload_entry_unloads_coordinator_when_empty(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """When coordinator has no more entries after unregister, it must be unloaded."""
    mock_config_entry.add_to_hass(hass)

    coordinator = MagicMock(spec=NotificationCoordinator)
    coordinator.unregister = MagicMock()
    coordinator.has_entries = MagicMock(return_value=False)
    coordinator.unload = MagicMock()

    domain_data = _make_domain_data(
        coordinator=coordinator, entry_id=mock_config_entry.entry_id
    )
    hass.data[DOMAIN] = domain_data

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ):
        from custom_components.bodymiscale import async_unload_entry

        result = await async_unload_entry(hass, mock_config_entry)

    assert result is True
    coordinator.unload.assert_called_once()


async def test_unload_entry_no_coordinator_is_noop(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """async_unload_entry works normally when NOTIFICATION_COORDINATOR is None."""
    mock_config_entry.add_to_hass(hass)

    hass.data[DOMAIN] = _make_domain_data(
        coordinator=None, entry_id=mock_config_entry.entry_id
    )

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ):
        from custom_components.bodymiscale import async_unload_entry

        result = await async_unload_entry(hass, mock_config_entry)

    assert result is True


# ===========================================================================
# async_migrate_entry
# ===========================================================================


async def test_migrate_entry_v1_to_v4(
    hass: HomeAssistant,
    mock_config_entry_v1: MockConfigEntry,
) -> None:
    """Migration from v1 must produce a valid v4 config entry."""
    mock_config_entry_v1.add_to_hass(hass)

    from custom_components.bodymiscale import async_migrate_entry

    result = await async_migrate_entry(hass, mock_config_entry_v1)

    assert result is True
    assert mock_config_entry_v1.version == 4
    assert CONF_PROFILE_METHOD in mock_config_entry_v1.options


async def test_migrate_entry_v2_sets_impedance_mode_standard(
    hass: HomeAssistant,
    mock_config_entry_v2: MockConfigEntry,
) -> None:
    """V2 entry with CONF_SENSOR_IMPEDANCE must get impedance_mode=standard."""
    mock_config_entry_v2.add_to_hass(hass)

    from custom_components.bodymiscale import async_migrate_entry

    result = await async_migrate_entry(hass, mock_config_entry_v2)

    assert result is True
    assert mock_config_entry_v2.version == 4
    assert (
        mock_config_entry_v2.options.get(CONF_IMPEDANCE_MODE) == IMPEDANCE_MODE_STANDARD
    )


async def test_migrate_entry_v3_adds_profile_method(
    hass: HomeAssistant,
    mock_config_entry_v3: MockConfigEntry,
) -> None:
    """V3 entry must get PROFILE_METHOD_NONE added on migration to v4."""
    mock_config_entry_v3.add_to_hass(hass)

    from custom_components.bodymiscale import async_migrate_entry

    result = await async_migrate_entry(hass, mock_config_entry_v3)

    assert result is True
    assert mock_config_entry_v3.version == 4
    assert mock_config_entry_v3.options.get(CONF_PROFILE_METHOD) == PROFILE_METHOD_NONE


async def test_migrate_entry_v4_is_noop(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Migration of a current v4 entry must succeed without modifying it."""
    mock_config_entry.add_to_hass(hass)
    original_data = dict(mock_config_entry.data)

    from custom_components.bodymiscale import async_migrate_entry

    result = await async_migrate_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.version == 4
    assert dict(mock_config_entry.data) == original_data


async def test_migrate_entry_unknown_version_returns_true(
    hass: HomeAssistant,
) -> None:
    """async_migrate_entry must return True for already-current or unknown version."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Future",
        unique_id="future",
        data={"name": "Future", CONF_BIRTHDAY: "1990-01-01", CONF_GENDER: Gender.MALE},
        options={
            CONF_HEIGHT: 180.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
            CONF_SENSOR_WEIGHT: "sensor.weight",
        },
        version=99,
    )
    entry.add_to_hass(hass)

    from custom_components.bodymiscale import async_migrate_entry

    result = await async_migrate_entry(hass, entry)

    assert result is True
    assert entry.version == 99


async def test_migrate_entry_purges_last_measurement_time(
    hass: HomeAssistant,
    mock_config_entry_v2: MockConfigEntry,
) -> None:
    """Migration must remove deprecated last_measurement_time key."""
    mock_config_entry_v2.add_to_hass(hass)
    data = dict(mock_config_entry_v2.data)
    data["last_measurement_time"] = "2024-01-01T12:00:00"
    hass.config_entries.async_update_entry(mock_config_entry_v2, data=data)

    from custom_components.bodymiscale import async_migrate_entry

    await async_migrate_entry(hass, mock_config_entry_v2)

    assert "last_measurement_time" not in mock_config_entry_v2.data
    assert "last_measurement_time" not in mock_config_entry_v2.options


# ===========================================================================
# is_ha_supported
# ===========================================================================


def test_is_ha_supported_returns_true_for_new_enough_version() -> None:
    """is_ha_supported must return True when HA_VERSION >= MIN_REQUIRED_HA_VERSION."""
    from custom_components.bodymiscale import is_ha_supported

    with patch("custom_components.bodymiscale.HA_VERSION", "2099.1.0"):
        assert is_ha_supported() is True


def test_is_ha_supported_returns_false_and_logs_for_old_version(caplog) -> None:
    """is_ha_supported must return False and log an error for too-old HA."""
    from custom_components.bodymiscale import is_ha_supported

    with patch("custom_components.bodymiscale.HA_VERSION", "2020.1.0"):
        result = is_ha_supported()

    assert result is False
    assert "Unsupported HA version" in caplog.text


# ===========================================================================
# async_reload_entry
# ===========================================================================


async def test_async_reload_entry_reloads_config_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """async_reload_entry must delegate to hass.config_entries.async_reload."""
    mock_config_entry.add_to_hass(hass)

    with patch.object(
        hass.config_entries, "async_reload", new_callable=AsyncMock
    ) as mock_reload:
        from custom_components.bodymiscale import async_reload_entry

        await async_reload_entry(hass, mock_config_entry)

    mock_reload.assert_awaited_once_with(mock_config_entry.entry_id)


# ===========================================================================
# async_migrate_entry — additional branch coverage
# ===========================================================================


async def test_migrate_entry_v1_restores_birthday_and_gender_from_options(
    hass: HomeAssistant,
) -> None:
    """V1 entries with birthday/gender stuck in options must move them to data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Gina",
        unique_id="gina",
        data={CONF_SENSOR_WEIGHT: "sensor.weight"},
        options={
            "name": "Gina",
            CONF_BIRTHDAY: "1991-02-03",
            CONF_GENDER: Gender.FEMALE,
        },
        version=1,
    )
    entry.add_to_hass(hass)

    from custom_components.bodymiscale import async_migrate_entry

    result = await async_migrate_entry(hass, entry)

    assert result is True
    assert entry.version == 4
    assert entry.data[CONF_BIRTHDAY] == "1991-02-03"
    assert entry.data[CONF_GENDER] == Gender.FEMALE


async def test_migrate_entry_v2_moves_gender_from_options_to_data(
    hass: HomeAssistant,
) -> None:
    """V2 entries with gender only in options must get it copied into data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Hank",
        unique_id="hank",
        data={"name": "Hank", CONF_BIRTHDAY: "1980-05-05"},
        options={CONF_GENDER: Gender.MALE, CONF_SENSOR_WEIGHT: "sensor.weight"},
        version=2,
    )
    entry.add_to_hass(hass)

    from custom_components.bodymiscale import async_migrate_entry

    result = await async_migrate_entry(hass, entry)

    assert result is True
    assert entry.data[CONF_GENDER] == Gender.MALE


async def test_migrate_entry_v2_dual_impedance_sets_mode_dual(
    hass: HomeAssistant,
) -> None:
    """V2 entries with dual impedance sensors must get impedance_mode=dual."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Ivy",
        unique_id="ivy",
        data={
            "name": "Ivy",
            CONF_BIRTHDAY: "1993-09-09",
            CONF_GENDER: Gender.FEMALE,
            CONF_SENSOR_IMPEDANCE_LOW: "sensor.impedance_low",
            CONF_SENSOR_IMPEDANCE_HIGH: "sensor.impedance_high",
        },
        options={CONF_SENSOR_WEIGHT: "sensor.weight"},
        version=2,
    )
    entry.add_to_hass(hass)

    from custom_components.bodymiscale import async_migrate_entry

    result = await async_migrate_entry(hass, entry)

    assert result is True
    assert entry.options.get(CONF_IMPEDANCE_MODE) == IMPEDANCE_MODE_DUAL


# ===========================================================================
# Bodymiscale entity
# ===========================================================================


def _make_bodymiscale_handler(
    impedance_mode: str = IMPEDANCE_MODE_NONE,
    name: str = "Alice",
    gender: Gender = Gender.FEMALE,
    height: float = 165.0,
    birthday: str = "1990-01-15",
) -> MagicMock:
    """Return a minimal mock BodyScaleMetricsHandler for entity-level tests."""
    from custom_components.bodymiscale.metrics import BodyScaleMetricsHandler

    handler = MagicMock(spec=BodyScaleMetricsHandler)
    handler.config = {
        CONF_NAME: name,
        CONF_IMPEDANCE_MODE: impedance_mode,
        CONF_GENDER: gender,
        CONF_HEIGHT: height,
        CONF_BIRTHDAY: birthday,
    }
    handler.config_entry_id = "entry_test"
    handler.subscribe = MagicMock(return_value=lambda: None)
    handler.restore_metric = MagicMock()
    return handler


def test_bodymiscale_init_sets_up_entity_description() -> None:
    """Bodymiscale.__init__ must configure the umbrella entity description."""
    from custom_components.bodymiscale import Bodymiscale

    handler = _make_bodymiscale_handler(name="Alice")
    entity = Bodymiscale(handler)

    assert entity.entity_description.key == "bodymiscale"
    assert entity.entity_description.icon == "mdi:human"
    assert entity._timer_handle is None
    assert entity._available_metrics == {}


async def test_bodymiscale_async_added_to_hass_no_previous_state(
    hass: HomeAssistant,
) -> None:
    """With no restored state, entity must still subscribe without restoring."""
    from custom_components.bodymiscale import Bodymiscale

    handler = _make_bodymiscale_handler()
    entity = Bodymiscale(handler)
    entity.hass = hass
    entity.entity_id = "bodymiscale.alice"

    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state",
        new=AsyncMock(return_value=None),
    ):
        await entity.async_added_to_hass()

    assert entity._available_metrics == {}
    handler.restore_metric.assert_not_called()
    assert handler.subscribe.call_count == len(list(Metric))


async def test_bodymiscale_async_added_to_hass_restores_problem_state(
    hass: HomeAssistant,
) -> None:
    """A restored 'problem' state must be kept and restorable metrics forwarded."""
    from custom_components.bodymiscale import Bodymiscale

    handler = _make_bodymiscale_handler()
    entity = Bodymiscale(handler)
    entity.hass = hass
    entity.entity_id = "bodymiscale.alice"

    last_state = MagicMock()
    last_state.state = STATE_PROBLEM
    last_state.attributes = {
        Metric.WEIGHT.value: 62.5,
        Metric.IMPEDANCE.value: 450,
        CONF_HEIGHT: 165.0,  # must be excluded from _available_metrics
        ATTR_BMILABEL: "normal",  # must be excluded too
    }

    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state",
        new=AsyncMock(return_value=last_state),
    ):
        await entity.async_added_to_hass()

    assert entity._attr_state == STATE_PROBLEM
    assert CONF_HEIGHT not in entity._available_metrics
    assert ATTR_BMILABEL not in entity._available_metrics
    assert entity._available_metrics[Metric.WEIGHT.value] == 62.5

    handler.restore_metric.assert_any_call(Metric.WEIGHT, 62.5)
    handler.restore_metric.assert_any_call(Metric.IMPEDANCE, 450)


async def test_bodymiscale_async_added_to_hass_unknown_state_defaults_to_ok(
    hass: HomeAssistant,
) -> None:
    """A restored state that isn't ok/problem must fall back to STATE_OK."""
    from custom_components.bodymiscale import Bodymiscale

    handler = _make_bodymiscale_handler()
    entity = Bodymiscale(handler)
    entity.hass = hass
    entity.entity_id = "bodymiscale.alice"

    last_state = MagicMock()
    last_state.state = STATE_UNAVAILABLE
    last_state.attributes = {}

    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state",
        new=AsyncMock(return_value=last_state),
    ):
        await entity.async_added_to_hass()

    assert entity._attr_state == STATE_OK


async def test_bodymiscale_on_value_status_updates_state_and_schedules_write(
    hass: HomeAssistant,
) -> None:
    """The internal on_value callback must map STATUS updates to attr_state."""
    from custom_components.bodymiscale import Bodymiscale

    handler = _make_bodymiscale_handler()
    entity = Bodymiscale(handler)
    entity.hass = hass
    entity.entity_id = "bodymiscale.alice"
    entity.async_write_ha_state = MagicMock()

    captured: dict[str, Any] = {}

    def fake_subscribe(metric, callback_func):
        captured.setdefault(metric, []).append(callback_func)
        return lambda: None

    handler.subscribe = MagicMock(side_effect=fake_subscribe)

    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state",
        new=AsyncMock(return_value=None),
    ):
        await entity.async_added_to_hass()

    # Trigger a STATUS update — must flip attr_state to STATE_PROBLEM
    status_cb = captured[Metric.STATUS][0]
    status_cb("some_problem")
    assert entity._attr_state == STATE_PROBLEM
    assert entity._available_metrics[ATTR_PROBLEM] == "some_problem"
    assert entity._timer_handle is not None

    # A PROBLEM_NONE value must flip it back to STATE_OK
    status_cb(PROBLEM_NONE)
    assert entity._attr_state == STATE_OK

    # A non-status metric must be stored under its own key, not affect state
    weight_cb = captured[Metric.WEIGHT][0]
    weight_cb(70.2)
    assert entity._available_metrics[Metric.WEIGHT.value] == 70.2


async def test_bodymiscale_remove_all_unsubscribes(
    hass: HomeAssistant,
) -> None:
    """on_remove callback registered by async_added_to_hass must clear subs."""
    from custom_components.bodymiscale import Bodymiscale

    handler = _make_bodymiscale_handler()
    entity = Bodymiscale(handler)
    entity.hass = hass
    entity.entity_id = "bodymiscale.alice"

    unsub_calls = []
    handler.subscribe = MagicMock(
        side_effect=lambda metric, cb: lambda: unsub_calls.append(metric)
    )

    registered_removers = []
    entity.async_on_remove = MagicMock(side_effect=registered_removers.append)

    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state",
        new=AsyncMock(return_value=None),
    ):
        await entity.async_added_to_hass()

    assert len(registered_removers) == 1
    registered_removers[0]()
    assert len(unsub_calls) == len(list(Metric))


def test_bodymiscale_state_attributes_standard_impedance_hides_dual_keys() -> None:
    """In standard mode, dual-frequency impedance keys must be hidden."""
    from custom_components.bodymiscale import Bodymiscale

    handler = _make_bodymiscale_handler(impedance_mode=IMPEDANCE_MODE_STANDARD)
    entity = Bodymiscale(handler)
    entity._available_metrics = {
        CONF_SENSOR_IMPEDANCE_LOW: 100,
        CONF_SENSOR_IMPEDANCE_HIGH: 200,
        ATTR_BMI: 22.0,
    }

    attrib = entity.state_attributes

    assert "impedance_low" not in attrib
    assert "impedance_high" not in attrib
    assert attrib[ATTR_BMILABEL]  # BMI present -> label must be computed


def test_bodymiscale_state_attributes_dual_mode_hides_standard_key() -> None:
    """In dual_frequency mode, the standard impedance key must be hidden."""
    from custom_components.bodymiscale import Bodymiscale

    handler = _make_bodymiscale_handler(impedance_mode=IMPEDANCE_MODE_DUAL)
    entity = Bodymiscale(handler)
    entity._available_metrics = {CONF_SENSOR_IMPEDANCE: 400}

    attrib = entity.state_attributes

    assert "impedance" not in attrib


def test_bodymiscale_state_attributes_none_mode_hides_all_impedance_keys() -> None:
    """With impedance_mode=none, every impedance-related key must be hidden."""
    from custom_components.bodymiscale import Bodymiscale

    handler = _make_bodymiscale_handler(impedance_mode=IMPEDANCE_MODE_NONE)
    entity = Bodymiscale(handler)
    entity._available_metrics = {
        CONF_SENSOR_IMPEDANCE: 1,
        CONF_SENSOR_IMPEDANCE_LOW: 2,
        CONF_SENSOR_IMPEDANCE_HIGH: 3,
    }

    attrib = entity.state_attributes

    assert "impedance" not in attrib
    assert "impedance_low" not in attrib
    assert "impedance_high" not in attrib


def test_bodymiscale_state_attributes_negative_fat_mass_means_lose() -> None:
    """A negative fat_mass_2_ideal_weight must surface as fat_mass_to_lose."""
    from custom_components.bodymiscale import Bodymiscale

    handler = _make_bodymiscale_handler()
    entity = Bodymiscale(handler)
    entity._available_metrics = {Metric.FAT_MASS_2_IDEAL_WEIGHT.value: -1.5}

    attrib = entity.state_attributes

    assert attrib[ATTR_FATMASSTOLOSE] == 1.5
    assert ATTR_FATMASSTOGAIN not in attrib
    assert Metric.FAT_MASS_2_IDEAL_WEIGHT.value not in attrib


def test_bodymiscale_state_attributes_positive_fat_mass_means_gain() -> None:
    """A positive fat_mass_2_ideal_weight must surface as fat_mass_to_gain."""
    from custom_components.bodymiscale import Bodymiscale

    handler = _make_bodymiscale_handler()
    entity = Bodymiscale(handler)
    entity._available_metrics = {Metric.FAT_MASS_2_IDEAL_WEIGHT.value: 2.0}

    attrib = entity.state_attributes

    assert attrib[ATTR_FATMASSTOGAIN] == 2.0
    assert ATTR_FATMASSTOLOSE not in attrib

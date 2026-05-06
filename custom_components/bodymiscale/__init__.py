"""Support for bodymiscale."""

import asyncio
import logging
from collections.abc import MutableMapping
from datetime import datetime
from functools import partial
from typing import Any

from awesomeversion import AwesomeVersion
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, STATE_OK, STATE_PROBLEM
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import StateType

from .const import (
    ALGO_XIAOMI,
    ATTR_AGE,
    ATTR_BMILABEL,
    ATTR_FATMASSTOGAIN,
    ATTR_FATMASSTOLOSE,
    ATTR_IDEAL,
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
    MIN_REQUIRED_HA_VERSION,
    NOTIFICATION_COORDINATOR,
    PLATFORMS,
    PROBLEM_NONE,
    PROFILE_METHOD_NONE,
    PROFILE_METHOD_NOTIFY,
    STARTUP_MESSAGE,
    UPDATE_DELAY,
)
from .entity import BodyScaleBaseEntity
from .metrics import BodyScaleMetricsHandler
from .models import Metric
from .profile import NotificationCoordinator, NotificationFilter
from .util import get_age, get_bmi_label, get_ideal_weight

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HA version check
# ---------------------------------------------------------------------------


def is_ha_supported() -> bool:
    """Return True if the current HA version is supported."""
    if AwesomeVersion(HA_VERSION) >= MIN_REQUIRED_HA_VERSION:
        return True
    _LOGGER.error(
        'Unsupported HA version! Please upgrade home assistant at least to "%s"',
        MIN_REQUIRED_HA_VERSION,
    )
    return False


# ---------------------------------------------------------------------------
# Config entry lifecycle
# ---------------------------------------------------------------------------


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up bodymiscale from a config entry."""
    if not is_ha_supported():
        return False

    if hass.data.get(DOMAIN) is None:
        hass.data[DOMAIN] = {
            COMPONENT: EntityComponent(_LOGGER, DOMAIN, hass),
            HANDLERS: {},
            MAIN_ENTITIES: {},
            NOTIFICATION_COORDINATOR: None,
        }
        _LOGGER.info(STARTUP_MESSAGE)

    config = {**entry.data, **entry.options}
    handler = BodyScaleMetricsHandler(hass, config, entry.entry_id)
    hass.data[DOMAIN][HANDLERS][entry.entry_id] = handler

    # Notification coordinator (method 3)
    if config.get(CONF_PROFILE_METHOD) == PROFILE_METHOD_NOTIFY:
        coordinator = hass.data[DOMAIN].get(NOTIFICATION_COORDINATOR)
        if coordinator is None:
            coordinator = NotificationCoordinator(hass)
            hass.data[DOMAIN][NOTIFICATION_COORDINATOR] = coordinator

        notify_filter = handler.profile_filter
        if isinstance(notify_filter, NotificationFilter):
            coordinator.register(
                entry_id=entry.entry_id,
                user_name=config.get(CONF_NAME, entry.title),
                notify_filter=notify_filter,
                device_id=config[CONF_NOTIFY_DEVICE_ID],
                handler=handler,
            )
            handler.set_notification_coordinator(coordinator)

    # Main umbrella entity (entity_id = "bodymiscale.<name>")
    component: EntityComponent = hass.data[DOMAIN][COMPONENT]
    entity = Bodymiscale(handler)
    await component.async_add_entities([entity])
    hass.data[DOMAIN][MAIN_ENTITIES][entry.entry_id] = entity

    # Sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok: bool = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        handler: BodyScaleMetricsHandler = hass.data[DOMAIN][HANDLERS].pop(
            entry.entry_id
        )
        handler.unload()

        entity: Bodymiscale | None = hass.data[DOMAIN][MAIN_ENTITIES].pop(
            entry.entry_id, None
        )
        if entity is not None:
            await entity.async_remove()

        coordinator = hass.data[DOMAIN].get(NOTIFICATION_COORDINATOR)
        if coordinator is not None:
            coordinator.unregister(entry.entry_id)
            if not coordinator.has_entries():
                coordinator.unload()
                hass.data[DOMAIN][NOTIFICATION_COORDINATOR] = None

        if not hass.data[DOMAIN][HANDLERS]:
            hass.data.pop(DOMAIN)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entry to the current version."""
    _LOGGER.debug("Migrating from version %d", config_entry.version)

    new_data = {**config_entry.data}
    new_options = {**config_entry.options}
    current_version = config_entry.version

    if current_version == 1:
        for key in [CONF_HEIGHT, CONF_SENSOR_WEIGHT, CONF_SENSOR_IMPEDANCE]:
            if key in new_data:
                new_options.setdefault(key, new_data.pop(key))
        if CONF_NAME in new_options:
            new_data.setdefault(CONF_NAME, new_options.pop(CONF_NAME))
        if CONF_BIRTHDAY in new_options:
            new_data.setdefault(CONF_BIRTHDAY, new_options.pop(CONF_BIRTHDAY))
        if CONF_GENDER in new_options:
            new_data.setdefault(CONF_GENDER, new_options.pop(CONF_GENDER))
        current_version = 2

    if current_version == 2:
        for key in [CONF_NAME, CONF_BIRTHDAY, CONF_GENDER]:
            if key not in new_data and key in new_options:
                new_data[key] = new_options[key]

        for key in [
            CONF_HEIGHT,
            CONF_SENSOR_WEIGHT,
            CONF_SENSOR_IMPEDANCE,
            CONF_SENSOR_IMPEDANCE_LOW,
            CONF_SENSOR_IMPEDANCE_HIGH,
        ]:
            if key in new_data:
                new_options.setdefault(key, new_data.pop(key))

        if not new_options.get(CONF_IMPEDANCE_MODE):
            if new_options.get(CONF_SENSOR_IMPEDANCE_LOW) or new_options.get(
                CONF_SENSOR_IMPEDANCE_HIGH
            ):
                new_options[CONF_IMPEDANCE_MODE] = IMPEDANCE_MODE_DUAL
            elif new_options.get(CONF_SENSOR_IMPEDANCE) or new_data.get(
                CONF_SENSOR_IMPEDANCE
            ):
                new_options[CONF_IMPEDANCE_MODE] = IMPEDANCE_MODE_STANDARD
            else:
                new_options[CONF_IMPEDANCE_MODE] = IMPEDANCE_MODE_NONE

        new_options.setdefault(CONF_CALCULATION_MODE, ALGO_XIAOMI)
        # Purge last_measurement_time — managed internally since 2026.5.0
        new_data.pop("last_measurement_time", None)
        new_options.pop("last_measurement_time", None)
        current_version = 3

    if current_version == 3:
        new_options.setdefault(CONF_PROFILE_METHOD, PROFILE_METHOD_NONE)
        # Purge last_measurement_time — managed internally since 2026.5.0
        new_data.pop("last_measurement_time", None)
        new_options.pop("last_measurement_time", None)
        current_version = 4

    if current_version != config_entry.version:
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, options=new_options, version=current_version
        )
        _LOGGER.info("Migration to version %d successful", current_version)

    return True


# ---------------------------------------------------------------------------
# Main umbrella entity
# ---------------------------------------------------------------------------


class Bodymiscale(BodyScaleBaseEntity, RestoreEntity):
    """Bodymiscale umbrella entity.

    Registered via EntityComponent(domain="bodymiscale") so that its
    entity_id is "bodymiscale.<name>" matching the original behaviour.

    Uses RestoreEntity (not RestoreSensor) because its value is stored in
    state attributes, not in a typed native_value.
    """

    _attr_should_poll = False

    def __init__(self, handler: BodyScaleMetricsHandler) -> None:
        super().__init__(
            handler,
            EntityDescription(
                key="bodymiscale",
                name=None,
                icon="mdi:human",
            ),
        )
        self._timer_handle: asyncio.TimerHandle | None = None
        self._available_metrics: MutableMapping[str, StateType | datetime] = {}

    async def async_added_to_hass(self) -> None:
        """Restore previous state and subscribe to metric updates."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None:
            # Restore the state (ok/problem) so the entity is not "unavailable"
            # after restart while waiting for the next measurement.
            if last_state.state in (STATE_OK, STATE_PROBLEM):
                self._attr_state = last_state.state
            else:
                self._attr_state = STATE_OK

            exclude_attrs = frozenset(
                {
                    ATTR_BMILABEL,
                    ATTR_FATMASSTOLOSE,
                    ATTR_FATMASSTOGAIN,
                    CONF_HEIGHT,
                    CONF_GENDER,
                    ATTR_IDEAL,
                    ATTR_AGE,
                }
            )
            self._available_metrics = {
                k: v for k, v in last_state.attributes.items() if k not in exclude_attrs
            }

            source_metrics = (
                Metric.WEIGHT,
                Metric.IMPEDANCE,
                Metric.IMPEDANCE_LOW,
                Metric.IMPEDANCE_HIGH,
                Metric.LAST_MEASUREMENT_TIME,
            )
            for metric in source_metrics:
                value = self._available_metrics.get(metric.value)
                if value is not None:
                    self._handler.restore_metric(metric, value)

        loop = asyncio.get_running_loop()

        def on_value(value: StateType | datetime, *, metric: Metric) -> None:
            if metric is Metric.STATUS:
                self._attr_state = STATE_OK if value == PROBLEM_NONE else STATE_PROBLEM
                self._available_metrics[ATTR_PROBLEM] = value
            else:
                self._available_metrics[metric.value] = value

            if self._timer_handle is not None:
                self._timer_handle.cancel()
            self._timer_handle = loop.call_later(
                UPDATE_DELAY, self.async_write_ha_state
            )

        remove_subs = []
        for metric in Metric:
            remove_subs.append(
                self._handler.subscribe(metric, partial(on_value, metric=metric))
            )

        def _remove_all() -> None:
            for sub in remove_subs:
                sub()

        self.async_on_remove(_remove_all)

    @property
    def state_attributes(self) -> dict[str, Any]:
        """Return all body metrics as state attributes."""
        mode = self._handler.config.get(CONF_IMPEDANCE_MODE)

        attrib: dict[str, Any] = {
            CONF_HEIGHT: self._handler.config[CONF_HEIGHT],
            CONF_GENDER: self._handler.config[CONF_GENDER].value,
            ATTR_IDEAL: get_ideal_weight(self._handler.config),
            ATTR_AGE: get_age(self._handler.config[CONF_BIRTHDAY]),
            **self._available_metrics,
        }

        if mode == "standard":
            attrib.pop("impedance_low", None)
            attrib.pop("impedance_high", None)
        elif mode == "dual_frequency":
            attrib.pop("impedance", None)
        else:
            attrib.pop("impedance", None)
            attrib.pop("impedance_low", None)
            attrib.pop("impedance_high", None)

        if Metric.BMI.value in attrib:
            attrib[ATTR_BMILABEL] = get_bmi_label(attrib[Metric.BMI.value])

        if Metric.FAT_MASS_2_IDEAL_WEIGHT.value in attrib:
            value = attrib.pop(Metric.FAT_MASS_2_IDEAL_WEIGHT.value)
            if isinstance(value, (int, float)):
                if value < 0:
                    attrib[ATTR_FATMASSTOLOSE] = abs(value)
                else:
                    attrib[ATTR_FATMASSTOGAIN] = value

        return attrib

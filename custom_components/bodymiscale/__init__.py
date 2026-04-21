"""Support for bodymiscale."""

import asyncio
import logging
from collections.abc import MutableMapping
from datetime import datetime
from functools import partial
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from awesomeversion import AwesomeVersion
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_SENSORS, STATE_OK, STATE_PROBLEM
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.typing import StateType

from custom_components.bodymiscale.metrics import BodyScaleMetricsHandler
from custom_components.bodymiscale.models import Metric
from custom_components.bodymiscale.util import get_age, get_bmi_label, get_ideal_weight

from .const import (
    ATTR_AGE,
    ATTR_BMILABEL,
    ATTR_FATMASSTOGAIN,
    ATTR_FATMASSTOLOSE,
    ATTR_IDEAL,
    ATTR_PROBLEM,
    COMPONENT,
    CONF_BIRTHDAY,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_IMPEDANCE_MODE,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_IMPEDANCE_HIGH,
    CONF_SENSOR_IMPEDANCE_LOW,
    CONF_SENSOR_LAST_MEASUREMENT_TIME,
    CONF_SENSOR_WEIGHT,
    DOMAIN,
    HANDLERS,
    MIN_REQUIRED_HA_VERSION,
    PLATFORMS,
    PROBLEM_NONE,
    STARTUP_MESSAGE,
    UPDATE_DELAY,
)
from .entity import BodyScaleBaseEntity

_LOGGER = logging.getLogger(__name__)

SCHEMA_SENSORS = vol.Schema(
    {
        vol.Required(CONF_SENSOR_WEIGHT): cv.entity_id,
        vol.Optional(CONF_SENSOR_IMPEDANCE): cv.entity_id,
        vol.Optional(CONF_SENSOR_IMPEDANCE_LOW): cv.entity_id,
        vol.Optional(CONF_SENSOR_IMPEDANCE_HIGH): cv.entity_id,
        vol.Optional(CONF_SENSOR_LAST_MEASUREMENT_TIME): cv.entity_id,
    }
)

BODYMISCALE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SENSORS): vol.Schema(SCHEMA_SENSORS),
        vol.Required(CONF_HEIGHT): cv.positive_int,
        vol.Required(CONF_BIRTHDAY): cv.string,
        vol.Required(CONF_GENDER): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: {cv.string: BODYMISCALE_SCHEMA}}, extra=vol.ALLOW_EXTRA
)


def is_ha_supported() -> bool:
    """Return True, if current HA version is supported."""
    if AwesomeVersion(HA_VERSION) >= MIN_REQUIRED_HA_VERSION:
        return True

    _LOGGER.error(
        'Unsupported HA version! Please upgrade home assistant at least to "%s"',
        MIN_REQUIRED_HA_VERSION,
    )
    return False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up component via UI."""
    if not is_ha_supported():
        return False

    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(
            DOMAIN,
            {
                COMPONENT: EntityComponent(_LOGGER, DOMAIN, hass),
                HANDLERS: {},
            },
        )
        _LOGGER.info(STARTUP_MESSAGE)

    handler = BodyScaleMetricsHandler(
        hass, {**entry.data, **entry.options}, entry.entry_id
    )
    hass.data[DOMAIN][HANDLERS][entry.entry_id] = handler

    component: EntityComponent = hass.data[DOMAIN][COMPONENT]
    await component.async_add_entities([Bodymiscale(handler)])

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok: bool = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        del hass.data[DOMAIN][HANDLERS][entry.entry_id]
        if len(hass.data[DOMAIN][HANDLERS]) == 0:
            hass.data.pop(DOMAIN)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when it changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %d", config_entry.version)

    new_data = {**config_entry.data}
    new_options = {**config_entry.options}
    current_version = config_entry.version

    if current_version == 1:
        for key in [CONF_HEIGHT, CONF_SENSOR_WEIGHT, CONF_SENSOR_IMPEDANCE]:
            if key in new_data:
                new_options[key] = new_data.pop(key)
        for key in [CONF_NAME, CONF_BIRTHDAY, CONF_GENDER]:
            new_options.pop(key, None)
        current_version = 2

    if current_version == 2:
        if new_options.get(CONF_SENSOR_IMPEDANCE):
            new_options[CONF_IMPEDANCE_MODE] = "standard"
        elif new_options.get(CONF_SENSOR_IMPEDANCE_LOW) or new_options.get(
            CONF_SENSOR_IMPEDANCE_HIGH
        ):
            new_options[CONF_IMPEDANCE_MODE] = "dual_frequency"
        else:
            new_options[CONF_IMPEDANCE_MODE] = "none"
        current_version = 3

    if current_version != config_entry.version:
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, options=new_options, version=current_version
        )
        _LOGGER.info("Migration to version %d successful", current_version)

    return True


class Bodymiscale(BodyScaleBaseEntity):
    """Bodymiscale entity."""

    def __init__(self, handler: BodyScaleMetricsHandler):
        """Initialize the Bodymiscale component."""
        super().__init__(
            handler,
            EntityDescription(key="bodymiscale", name=None, icon="mdi:human"),
        )
        self._timer_handle: asyncio.TimerHandle | None = None
        self._available_metrics: MutableMapping[str, StateType | datetime] = {}

    async def async_added_to_hass(self) -> None:
        """After being added to hass."""
        await super().async_added_to_hass()

        loop = asyncio.get_running_loop()

        def on_value(value: StateType | datetime, *, metric: Metric) -> None:
            if metric == Metric.STATUS:
                self._attr_state = STATE_OK if value == PROBLEM_NONE else STATE_PROBLEM
                self._available_metrics[ATTR_PROBLEM] = value
            else:
                self._available_metrics[metric.value] = value

            if self._timer_handle is not None:
                self._timer_handle.cancel()
            self._timer_handle = loop.call_later(
                UPDATE_DELAY, self.async_write_ha_state
            )

        remove_subscriptions = []
        for metric in Metric:
            remove_subscriptions.append(
                self._handler.subscribe(metric, partial(on_value, metric=metric))
            )

        def on_remove() -> None:
            for subscription in remove_subscriptions:
                subscription()

        self.async_on_remove(on_remove)

    @property
    def state_attributes(self) -> dict[str, Any]:
        """Return the attributes of the entity."""
        mode = self._handler.config.get(CONF_IMPEDANCE_MODE)

        attrib = {
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

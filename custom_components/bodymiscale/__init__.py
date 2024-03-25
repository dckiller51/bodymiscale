"""Support for bodymiscale."""

import asyncio
import logging
from collections.abc import MutableMapping
from functools import partial
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from awesomeversion import AwesomeVersion
from cachetools import TTLCache
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
    CONF_SENSOR_IMPEDANCE,
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
    }
)

BODYMISCALE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SENSORS): vol.Schema(SCHEMA_SENSORS),
        vol.Required(CONF_HEIGHT): cv.positive_int,
        vol.Required("born"): cv.string,
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

    handler = hass.data[DOMAIN][HANDLERS][entry.entry_id] = BodyScaleMetricsHandler(
        hass, {**entry.data, **entry.options}, entry.entry_id
    )

    component: EntityComponent = hass.data[DOMAIN][COMPONENT]
    await component.async_add_entities([Bodymiscale(handler)])

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # Reload entry when its updated.
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok: bool = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        component: EntityComponent = hass.data[DOMAIN][COMPONENT]
        await component.async_prepare_reload()

        del hass.data[DOMAIN][HANDLERS][entry.entry_id]
        if len(hass.data[DOMAIN][HANDLERS]) == 0:
            hass.data.pop(DOMAIN)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when it changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(_: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %d", config_entry.version)

    if config_entry.version == 1:
        data = {**config_entry.data}
        options = {
            CONF_HEIGHT: data.pop(CONF_HEIGHT),
            CONF_SENSOR_WEIGHT: data.pop(CONF_SENSOR_WEIGHT),
        }
        if CONF_SENSOR_IMPEDANCE in data:
            options[CONF_SENSOR_IMPEDANCE] = data.pop(CONF_SENSOR_IMPEDANCE)

        if config_entry.options:
            options.update(config_entry.options)
            options.pop(CONF_NAME)
            options.pop(CONF_BIRTHDAY)
            options.pop(CONF_GENDER)

        config_entry.data = data
        config_entry.options = options

        config_entry.version = 2

    _LOGGER.info("Migration to version %d successful", config_entry.version)
    return True


class Bodymiscale(BodyScaleBaseEntity):
    """Bodymiscale the well-being of a body.

    It also checks the measurements against weight, height, age,
    gender and impedance (if configured).
    """

    def __init__(self, handler: BodyScaleMetricsHandler):
        """Initialize the Bodymiscale component."""
        super().__init__(
            handler,
            EntityDescription(key="bodymiscale", name=None, icon="mdi:human"),
        )
        self._timer_handle: asyncio.TimerHandle | None = None
        self._available_metrics: MutableMapping[str, StateType] = TTLCache(
            maxsize=len(Metric), ttl=60
        )

    async def async_added_to_hass(self) -> None:
        """After being added to hass."""
        await super().async_added_to_hass()

        loop = asyncio.get_event_loop()

        def on_value(value: StateType, *, metric: Metric) -> None:
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
        attrib = {
            CONF_HEIGHT: self._handler.config[CONF_HEIGHT],
            CONF_GENDER: self._handler.config[CONF_GENDER].value,
            ATTR_IDEAL: get_ideal_weight(self._handler.config),
            ATTR_AGE: get_age(self._handler.config[CONF_BIRTHDAY]),
            **self._available_metrics,
        }

        if Metric.BMI.value in attrib:
            attrib[ATTR_BMILABEL] = get_bmi_label(attrib[Metric.BMI.value])

        if Metric.FAT_MASS_2_IDEAL_WEIGHT.value in attrib:
            value = attrib.pop(Metric.FAT_MASS_2_IDEAL_WEIGHT.value)

            if value < 0:
                attrib[ATTR_FATMASSTOLOSE] = value * -1
            else:
                attrib[ATTR_FATMASSTOGAIN] = value

        return attrib

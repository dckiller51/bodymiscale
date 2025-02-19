"""Support for bodymiscale."""

import asyncio
import logging
from collections.abc import MutableMapping
from functools import partial
from typing import Any
from datetime import datetime

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
    ATTR_LAST_MEASUREMENT_TIME,
    COMPONENT,
    CONF_BIRTHDAY,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_IMPEDANCE_SENSOR,
    CONF_WEIGHT_SENSOR,
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
        vol.Required(CONF_WEIGHT_SENSOR): cv.entity_id,  # Required weight sensor entity ID
        vol.Optional(CONF_IMPEDANCE_SENSOR): cv.entity_id,  # Optional impedance sensor entity ID
    }
)

BODYMISCALE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SENSORS): vol.Schema(SCHEMA_SENSORS),  # Required sensors configuration
        vol.Required(CONF_HEIGHT): cv.positive_int,  # Required height (positive integer)
        vol.Required("born"): cv.string,  # Required date of birth (string)
        vol.Required(CONF_GENDER): cv.string,  # Required gender (string)
    },
    extra=vol.ALLOW_EXTRA,  # Allow extra configuration options
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: {cv.string: BODYMISCALE_SCHEMA}}, extra=vol.ALLOW_EXTRA  # Configuration schema for the integration
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
                COMPONENT: EntityComponent(_LOGGER, DOMAIN, hass),  # Initialize the entity component
                HANDLERS: {},  # Dictionary to store metric handlers
            },
        )
        _LOGGER.info(STARTUP_MESSAGE)  # Log the startup message

    handler = hass.data[DOMAIN][HANDLERS][entry.entry_id] = BodyScaleMetricsHandler(
        hass, {**entry.data, **entry.options}, entry.entry_id  # Create a metrics handler
    )

    component: EntityComponent = hass.data[DOMAIN][COMPONENT]
    await component.async_add_entities([Bodymiscale(handler)])  # Add the Bodymiscale entity

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)  # Forward entry setup to platforms
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))  # Add listener for entry updates

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok: bool = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)  # Unload platforms

    if unload_ok:
        component: EntityComponent = hass.data[DOMAIN][COMPONENT]
        await component.async_prepare_reload()  # Prepare for reload

        del hass.data[DOMAIN][HANDLERS][entry.entry_id]  # Remove the metrics handler
        if len(hass.data[DOMAIN][HANDLERS]) == 0:
            hass.data.pop(DOMAIN)  # Remove the domain data if no handlers left

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when it changed."""
    await hass.config_entries.async_reload(entry.entry_id)  # Reload the entry


async def async_migrate_entry(_: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %d", config_entry.version)  # Log migration start

    if config_entry.version == 1:  # Migration from version 1
        data = {**config_entry.data}  # Copy the data
        options = {
            CONF_HEIGHT: data.pop(CONF_HEIGHT),  # Extract height from data
            CONF_WEIGHT_SENSOR: data.pop(CONF_WEIGHT_SENSOR),  # Extract weight sensor from data
        }
        if CONF_IMPEDANCE_SENSOR in data:
            options[CONF_IMPEDANCE_SENSOR] = data.pop(CONF_IMPEDANCE_SENSOR)  # Extract impedance sensor

        if config_entry.options:  # Update options if they exist
            options.update(config_entry.options)
            options.pop(CONF_NAME)  # Remove name from options
            options.pop(CONF_BIRTHDAY)  # Remove birthday from options
            options.pop(CONF_GENDER)  # Remove gender from options

        config_entry.data = data  # Update config entry data
        config_entry.options = options  # Update config entry options

        config_entry.version = 2  # Update config entry version

    _LOGGER.info("Migration to version %d successful", config_entry.version)  # Log migration success
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
            EntityDescription(key="bodymiscale", name=None, icon="mdi:human"),  # Set entity description
        )
        self._timer_handle: asyncio.TimerHandle | None = None  # Timer handle for delayed state updates
        self._available_metrics: MutableMapping[str, StateType] = TTLCache(
            maxsize=len(Metric), ttl=60  # Cache for available metrics with TTL
        )
        self._last_time = None

    async def async_added_to_hass(self) -> None:
        """After being added to hass."""
        await super().async_added_to_hass()

        loop = asyncio.get_event_loop()

        def on_value(value: StateType, *, metric: Metric) -> None:  # Callback for metric updates
            if metric == Metric.STATUS:  # Update status attribute
                self._attr_state = STATE_OK if value == PROBLEM_NONE else STATE_PROBLEM  # Set entity state
                self._available_metrics[ATTR_PROBLEM] = value  # Store problem state
            else:
                self._available_metrics[metric.value] = value  # Store metric value

            self._last_time = datetime.now().strftime("%Y-%m-%d %H:%M")  # Store the last measurement time

            if self._timer_handle is not None:  # Cancel any existing timer
                self._timer_handle.cancel()
            self._timer_handle = loop.call_later(  # Schedule a delayed state update
                UPDATE_DELAY, self.async_write_ha_state
            )

        remove_subscriptions = []  # List to store unsubscribe functions
        for metric in Metric:  # Subscribe to all metrics
            remove_subscriptions.append(
                self._handler.subscribe(metric, partial(on_value, metric=metric))  # Subscribe to metric changes
            )

        def on_remove() -> None:  # Callback for entity removal
            for subscription in remove_subscriptions:  # Unsubscribe from all metrics
                subscription()

        self.async_on_remove(on_remove)  # Register the removal callback

    @property
    def state_attributes(self) -> dict[str, Any]:
        """Return the attributes of the entity."""
        attrib = {
            CONF_HEIGHT: self._handler.config[CONF_HEIGHT],  # Store height in attributes
            CONF_GENDER: self._handler.config[CONF_GENDER].value,  # Store gender in attributes
            ATTR_IDEAL: get_ideal_weight(self._handler.config),  # Calculate and store ideal weight
            ATTR_AGE: get_age(self._handler.config[CONF_BIRTHDAY]),  # Calculate and store age
            ATTR_LAST_MEASUREMENT_TIME: self._last_time,  # Store last measurement time
            **self._available_metrics,  # Add all available metrics to attributes
        }

        if Metric.BMI.value in attrib:  # If BMI is available
            attrib[ATTR_BMILABEL] = get_bmi_label(attrib[Metric.BMI.value])  # Calculate and store BMI label

        if Metric.FAT_MASS_2_IDEAL_WEIGHT.value in attrib:  # If fat mass to ideal weight is available
            value = attrib.pop(Metric.FAT_MASS_2_IDEAL_WEIGHT.value)  # Get the value and remove it

            if value < 0:  # If value is negative (fat mass to lose)
                attrib[ATTR_FATMASSTOLOSE] = value * -1  # Store fat mass to lose
            else:  # If value is positive (fat mass to gain)
                attrib[ATTR_FATMASSTOGAIN] = value  # Store fat mass to gain

        return attrib
    
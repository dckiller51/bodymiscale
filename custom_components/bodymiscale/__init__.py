"""Support for bodymiscale."""
import asyncio
import logging
from functools import partial
from typing import Any, MutableMapping, Optional

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from awesomeversion import AwesomeVersion
from cachetools import TTLCache
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_NAME, CONF_SENSORS, STATE_OK, STATE_PROBLEM
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.typing import StateType

from custom_components.bodymiscale.metrics import BodyScaleMetricsHandler
from custom_components.bodymiscale.models import Metric
from custom_components.bodymiscale.util import get_bmi_label, get_ideal_weight

from .const import (
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


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up component via yaml."""
    if DOMAIN in config:
        if not is_ha_supported():
            return False

        _LOGGER.warning(
            "Configuration of the bodymiscale in YAML is deprecated "
            "and will be removed future versions; Your existing "
            "configuration has been imported into the UI automatically and can be "
            "safely removed from your configuration.yaml file"
        )

        for name, conf in config[DOMAIN].items():
            conf[CONF_NAME] = name
            conf[CONF_SENSOR_WEIGHT] = conf[CONF_SENSORS][CONF_SENSOR_WEIGHT]
            if CONF_SENSOR_IMPEDANCE in conf[CONF_SENSORS]:
                conf[CONF_SENSOR_IMPEDANCE] = conf[CONF_SENSORS][CONF_SENSOR_IMPEDANCE]

            del conf[CONF_SENSORS]

            conf[CONF_BIRTHDAY] = conf.pop("born")

            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN, context={"source": SOURCE_IMPORT}, data=conf
                )
            )

    return True


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
        hass, entry.data
    )

    component = hass.data[DOMAIN][COMPONENT]
    await component.async_add_entities([Bodymiscale(handler)])

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
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
            EntityDescription(
                key="bodymiscale", name=handler.config[CONF_NAME], icon="mdi:human"
            ),
        )
        self._timer_handle: Optional[asyncio.TimerHandle] = None
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

        # todo
        # body_score = BodyScore(metrics)
        # attrib[ATTR_BODY_SCORE] = f"{body_score.body_score:.0f}"

        return attrib

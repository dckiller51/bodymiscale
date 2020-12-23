"""Support for bodymiscale."""
from collections import deque
from datetime import datetime, timedelta
import logging
import voluptuous as vol

from homeassistant.components.recorder.models import States
from homeassistant.components.recorder.util import execute, session_scope
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_SENSORS,
    STATE_OK,
    STATE_PROBLEM,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_track_state_change_event

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "bodymiscale"

READING_WEIGHT = "weight"

attributes = "attributes"
ATTR_PROBLEM = "problem"
ATTR_SENSORS = "sensors"
PROBLEM_NONE = "none"
ATTR_BMI = "bmi"

# we're not returning only one value, we're returning a dict here. So we need
# to have a separate literal for it to avoid confusion.
ATTR_DICT_OF_UNITS_OF_MEASUREMENT = "unit_of_measurement_dict"

CONF_HEIGHT = "height"
CONF_AGE = "age"
CONF_GENDER = "gender"

CONF_SENSOR_WEIGHT = READING_WEIGHT

DEFAULT_HEIGHT = 60
DEFAULT_AGE = 1
DEFAULT_GENDER = "female"

SCHEMA_SENSORS = vol.Schema(
    {
        vol.Optional(CONF_SENSOR_WEIGHT): cv.entity_id,
    }
)

BODYMISCALE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SENSORS): vol.Schema(SCHEMA_SENSORS),
        vol.Optional(CONF_HEIGHT, default=DEFAULT_HEIGHT): cv.positive_int,
        vol.Optional(CONF_AGE, default=DEFAULT_AGE): cv.positive_int,
        vol.Optional(CONF_GENDER, default=DEFAULT_GENDER): cv.string,
    }
)

DOMAIN = "bodymiscale"

CONFIG_SCHEMA = vol.Schema({DOMAIN: {cv.string: BODYMISCALE_SCHEMA}}, extra=vol.ALLOW_EXTRA)

ENABLE_LOAD_HISTORY = False

async def async_setup(hass, config):
    """Set up the Bodymiscale component."""
    component = EntityComponent(_LOGGER, DOMAIN, hass)

    entities = []
    weight = config.get(CONF_SENSOR_WEIGHT)
    height = config.get(CONF_HEIGHT)
    age = config.get(CONF_AGE)
    gender = config.get(CONF_GENDER)
    for bodymiscale_name, bodymiscale_config in config[DOMAIN].items():
        _LOGGER.info("Added bodymiscale %s", bodymiscale_name)
        entity = Bodymiscale(bodymiscale_name, bodymiscale_config, weight, \
            height, age, gender)
        entities.append(entity)

    await component.async_add_entities(entities)
    return True

from . import bodymetrics

class Bodymiscale(Entity):
    """Bodymiscale the well-being of a body.

    It also checks the measurements against weight, height, age, 
    gender and *impedance (*only miscale 2)
    """

    READINGS = {
        READING_WEIGHT: {
            ATTR_UNIT_OF_MEASUREMENT: "",
        },
    }

    def __init__(self, name, config, weight, height, age, gender):
        """Initialize the Bodymiscale component."""
        self._config = config
        self._sensormap = {}
        self._readingmap = {}
        self._unit_of_measurement = {}
        for reading, entity_id in config["sensors"].items():
            self._sensormap[entity_id] = reading
            self._readingmap[reading] = entity_id
        self._state = None
        self._name = name
        self._weight = None
        self._height = None
        self._age = None
        self._gender = None
        self._body_state = None
        self._attr_mbi = None
        self._problems = PROBLEM_NONE

    @callback
    def _state_changed_event(self, event):
        """Sensor state change event."""
        self.state_changed(event.data.get("entity_id"), event.data.get("new_state"))

    @callback
    def state_changed(self, entity_id, new_state):
        """Update the sensor status."""
        if new_state is None:
            return
        value = new_state.state
        _LOGGER.debug("Received callback from %s with value %s", entity_id, value)
        if value == STATE_UNKNOWN:
            return

        reading = self._sensormap[entity_id]
        if reading == READING_WEIGHT:
            if value != STATE_UNAVAILABLE:
                value = "{:.2f}".format(float(value))
            self._weight = value
        else:
            raise HomeAssistantError(
                f"Unknown reading from sensor {entity_id}: {value}"
            )
        if ATTR_UNIT_OF_MEASUREMENT in new_state.attributes:
            self._unit_of_measurement[reading] = new_state.attributes.get(
                ATTR_UNIT_OF_MEASUREMENT
            )
        if attributes in new_state.attributes:
            self._bodymiscale_attributes = new_state.attributes.get(
                attributes
            )
        self._update_state()

    def _update_state(self):
        """Update the state of the class based sensor data."""
        result = []
        for sensor_name in self._sensormap.values():
            params = self.READINGS[sensor_name]
            value = getattr(self, f"_{sensor_name}")
            if value is not None:
                if value == STATE_UNAVAILABLE:
                    result.append(f"{sensor_name} unavailable")

        result = [r for r in result if r is not None]

        if result:
            self._state = STATE_PROBLEM
            self._problems = ", ".join(result)
        else:
            self._state = STATE_OK
            self._problems = PROBLEM_NONE
        _LOGGER.debug("New data processed")
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """After being added to hass, load from history."""
        if ENABLE_LOAD_HISTORY and "recorder" in self.hass.config.components:
            # only use the database if it's configured
            await self.hass.async_add_executor_job(self._load_history_from_db)
            self.async_write_ha_state()

        async_track_state_change_event(
            self.hass, list(self._sensormap), self._state_changed_event
        )

        for entity_id in self._sensormap:
            state = self.hass.states.get(entity_id)
            if state is not None:
                self.state_changed(entity_id, state)

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def state_attributes(self):
        lib = bodymetrics.bodyMetrics(self._weight, self._height, self._age, self._gender, 0)
        """Return the attributes of the entity.
        Provide the individual measurements from the
        sensor in the attributes of the device.
        """
        attrib = {
            ATTR_PROBLEM: self._problems,
            ATTR_SENSORS: self._readingmap,
            ATTR_DICT_OF_UNITS_OF_MEASUREMENT: self._unit_of_measurement,
            ATTR_BMI: "{:.2f}".format(lib.getBMI()),
        }

        for reading in self._sensormap.values():
            attrib[reading] = getattr(self, f"_{reading}")

        return attrib

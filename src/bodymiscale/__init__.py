"""Support for bodymiscale."""
from collections import deque
from datetime import datetime, timedelta
from math import floor
import logging
import voluptuous as vol

from custom_components.bodymiscale.const import (
    DEFAULT_NAME,
    ATTR_PROBLEM,
    ATTR_SENSORS,
    PROBLEM_NONE,
    ATTR_AGE,
    ATTR_BMI,
    ATTR_BMR,
    ATTR_IDEAL,
    ATTR_IMCLABEL,
    ATTR_DICT_OF_UNITS_OF_MEASUREMENT,
    CONF_SENSOR_WEIGHT,
    CONF_HEIGHT,
    CONF_BORN,
    CONF_GENDER,
    DEFAULT_WEIGHT,
    DEFAULT_HEIGHT,
    DEFAULT_BORN,
    DEFAULT_GENDER,
)

from homeassistant.components.recorder.util import execute, session_scope
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    EVENT_HOMEASSISTANT_START,
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

SCHEMA_SENSORS = vol.Schema(
    {
        vol.Required(CONF_SENSOR_WEIGHT, default=DEFAULT_WEIGHT): cv.entity_id,
    }
)

BODYMISCALE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SENSORS): vol.Schema(SCHEMA_SENSORS),
        vol.Required(CONF_HEIGHT, default=DEFAULT_HEIGHT): cv.positive_int,
        vol.Optional(CONF_BORN, default=DEFAULT_BORN): cv.string,
        vol.Optional(CONF_GENDER, default=DEFAULT_GENDER): cv.string,
    }
)

DOMAIN = "bodymiscale"

CONFIG_SCHEMA = vol.Schema({DOMAIN: {cv.string: BODYMISCALE_SCHEMA}}, extra=vol.ALLOW_EXTRA)

async def async_setup(hass, config):
    """Set up the Bodymiscale component."""
    component = EntityComponent(_LOGGER, DOMAIN, hass)

    entities = []
    for bodymiscale_name, bodymiscale_config in config[DOMAIN].items():
        _LOGGER.info("Added bodymiscale %s", bodymiscale_name)
        entity = Bodymiscale(bodymiscale_name, bodymiscale_config)
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
        CONF_SENSOR_WEIGHT: {
            ATTR_UNIT_OF_MEASUREMENT: "",
        },
    }

    def __init__(self, name, config):
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
        self._problems = PROBLEM_NONE
        self._weight = None

        self._height = None
        if CONF_HEIGHT in self._config:
            self._conf_height = self._config[CONF_HEIGHT]
        self._born = None
        if CONF_BORN in self._config:
            self._conf_born = self._config[CONF_BORN]
        self._gender = None
        if CONF_GENDER in self._config:
            self._conf_gender = self._config[CONF_GENDER]

    def GetAge(self, d1):
        d1 = datetime.strptime(d1, "%Y-%m-%d")
        d2 = datetime.strptime(datetime.today().strftime('%Y-%m-%d'),'%Y-%m-%d')
        return abs((d2 - d1).days)/365

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
        if reading == CONF_SENSOR_WEIGHT:
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
        await super().async_added_to_hass()

        async_track_state_change_event(
            self.hass, list(self._sensormap), self._state_changed_event
        )

        for entity_id in self._sensormap:
            state = self.hass.states.get(entity_id)
            if state is not None:
                self.state_changed(entity_id, state)

        @callback
        def _async_startup(event):
            """Init on startup."""
            if self._sensormap:
                state = self.hass.states.get(entity_id)
                if state and state.state != STATE_UNKNOWN:
                    self.state_changed(entity_id, state)

        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, _async_startup)

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Return the icon that will be shown in the interface."""
        return 'mdi:human'

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def state_attributes(self):
        weight = 70
        height = self._conf_height
        age = self.GetAge(self._conf_born)
        gender = self._conf_gender
        lib = bodymetrics.bodyMetrics(weight, height, age, gender, 0)
        """Return the attributes of the entity.
        Provide the individual measurements from the
        sensor in the attributes of the device.
        """
        attrib = {
            ATTR_PROBLEM: self._problems,
            ATTR_SENSORS: self._readingmap,
            ATTR_DICT_OF_UNITS_OF_MEASUREMENT: self._unit_of_measurement,
            ATTR_AGE: int(age),
            CONF_HEIGHT: height,
            CONF_GENDER: gender,
            ATTR_BMI: "{:.2f}".format(lib.getBMI()),
            ATTR_BMR: "{:.2f}".format(lib.getBMR()),
            ATTR_IDEAL: "{:.2f}".format(lib.getIdealWeight()),
            ATTR_IMCLABEL: lib.getImcLabel()
        }

        for reading in self._sensormap.values():
            attrib[reading] = getattr(self, f"_{reading}")

        return attrib

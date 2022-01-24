"""Support for bodymiscale."""
from collections import deque
from datetime import datetime, timedelta
from math import floor
from .body_metrics import bodyMetrics
from .body_scales import bodyScales
from .body_score import bodyScore
import logging

import voluptuous as vol

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

from custom_components.bodymiscale.const import (
    DOMAIN,
    READING_WEIGHT,
    CONF_SENSOR_WEIGHT,
    CONF_MIN_WEIGHT,
    CONF_MAX_WEIGHT,
    ATTR_WEIGHT,
    ATTR_HEIGHT,
    ATTR_BORN,
    ATTR_GENDER,
    ATTR_AGE,
    ATTR_BMI,
    ATTR_BMR,
    ATTR_VISCERAL,
    ATTR_IDEAL,
    ATTR_BMILABEL,
    READING_IMPEDANCE,
    CONF_SENSOR_IMPEDANCE,
    CONF_MIN_IMPEDANCE,
    CONF_MAX_IMPEDANCE,
    ATTR_IMPEDANCE,
    ATTR_LBM,
    ATTR_FAT,
    ATTR_WATER,
    ATTR_BONES,
    ATTR_MUSCLE,
    ATTR_FATMASSTOLOSE,
    ATTR_FATMASSTOGAIN,
    ATTR_PROTEIN,
    ATTR_BODY,
    ATTR_BODY_SCORE,
    ATTR_METABOLIC,
    ATTR_UNIT_OF_MEASUREMENT,
    UNIT_POUNDS,
    DEFAULT_NAME,
    ATTR_PROBLEM,
    ATTR_SENSORS,
    PROBLEM_NONE,
    ATTR_MODEL,
    DEFAULT_MIN_WEIGHT,
    DEFAULT_MAX_WEIGHT,
    DEFAULT_MIN_IMPEDANCE,
    DEFAULT_MAX_IMPEDANCE,
    DEFAULT_MODEL,
    STARTUP_MESSAGE,
)

SCHEMA_SENSORS = vol.Schema(
    {
        vol.Required(CONF_SENSOR_WEIGHT): cv.entity_id,
        vol.Optional(CONF_SENSOR_IMPEDANCE): cv.entity_id,
    }
)

BODYMISCALE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SENSORS): vol.Schema(SCHEMA_SENSORS),
        vol.Optional(CONF_MIN_WEIGHT, default=DEFAULT_MIN_WEIGHT): vol.Coerce(float),
        vol.Optional(CONF_MAX_WEIGHT, default=DEFAULT_MAX_WEIGHT): vol.Coerce(float),
        vol.Optional(CONF_MIN_IMPEDANCE, default=DEFAULT_MIN_IMPEDANCE): cv.positive_int,
        vol.Optional(CONF_MAX_IMPEDANCE, default=DEFAULT_MAX_IMPEDANCE): cv.positive_int,
        vol.Required(ATTR_HEIGHT): cv.positive_int,
        vol.Required(ATTR_BORN): cv.string,
        vol.Required(ATTR_GENDER): cv.string,
        vol.Optional(ATTR_MODEL, default=DEFAULT_MODEL): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema({DOMAIN: {cv.string: BODYMISCALE_SCHEMA}}, extra=vol.ALLOW_EXTRA)

SCAN_INTERVAL = timedelta(seconds=30)

async def async_setup(hass, config):
    """Set up the Bodymiscale component."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    component = EntityComponent(_LOGGER, DOMAIN, hass)

    entities = []
    for bodymiscale_name, bodymiscale_config in config[DOMAIN].items():
        _LOGGER.info("Added bodymiscale %s", bodymiscale_name)
        entity = Bodymiscale(hass, bodymiscale_name, bodymiscale_config)
        entities.append(entity)

    await component.async_add_entities(entities)

    return True

class Bodymiscale(Entity):
    """Bodymiscale the well-being of a body.

    It also checks the measurements against weight, height, age,
    gender and *impedance (*only miscale 2)
    """

    READINGS = {
        READING_WEIGHT: {
            "min": CONF_MIN_WEIGHT,
            "max": CONF_MAX_WEIGHT,
        },
        READING_IMPEDANCE: {
            "min": CONF_MIN_IMPEDANCE,
            "max": CONF_MAX_IMPEDANCE,
        },
    }

    def __init__(self, hass, name, config):
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
        self._state_attributes = {}
        self._weight = None
        self._impedance = None
        if ATTR_HEIGHT in self._config:
            self._attr_height = self._config[ATTR_HEIGHT]
        if ATTR_BORN in self._config:
            self._attr_born = self._config[ATTR_BORN]
        if ATTR_GENDER in self._config:
            self._attr_gender = self._config[ATTR_GENDER]
        if ATTR_MODEL in self._config:
            self._attr_model = self._config[ATTR_MODEL]

    def GetAge(self, d1):
        born = datetime.strptime(d1, "%Y-%m-%d")
        today = datetime.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

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
                value = float(value)
            if new_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UNIT_POUNDS:
                value = value * 0.45359237
            self._weight = value
        elif reading == READING_IMPEDANCE:
            if value != STATE_UNAVAILABLE:
                value = int(float(value))
            self._impedance = value
        else:
            raise HomeAssistantError(
                f"Unknown reading from sensor {entity_id}: {value}"
            )
        self._update_state()

    def _update_state(self):
        """Update the state of the class based sensor data."""
        result = []
        for sensor_name in self._sensormap.values():
            params = self.READINGS[sensor_name]
            if (value := getattr(self, f"_{sensor_name}")) is not None:
                if value == STATE_UNAVAILABLE:
                    result.append(f"{sensor_name} unavailable")
                else:
                    if sensor_name == READING_IMPEDANCE:
                        result.append(self._check_min(sensor_name, value, params))
                    else:
                        result.append(self._check_min(sensor_name, value, params))
                    result.append(self._check_max(sensor_name, value, params))

        result = [r for r in result if r is not None]

        if result:
            self._state = STATE_PROBLEM
            self._problems = ", ".join(result)
        else:
            self._state = STATE_OK
            self._problems = PROBLEM_NONE
        _LOGGER.debug("New data processed")
        self.async_write_ha_state()

    def _check_min(self, sensor_name, value, params):
        """If configured, check the value against the defined minimum value."""
        if "min" in params and params["min"] in self._config:
            min_value = self._config[params["min"]]
            if value < min_value:
                return f"{sensor_name} low"

    def _check_max(self, sensor_name, value, params):
        """If configured, check the value against the defined maximum value."""
        if "max" in params and params["max"] in self._config:
            max_value = self._config[params["max"]]
            if value > max_value:
                return f"{sensor_name} high"
        return None

    async def async_added_to_hass(self):
        """After being added to hass."""
        
        async_track_state_change_event(
            self.hass, list(self._sensormap), self._state_changed_event
        )

        for entity_id in self._sensormap:
            if (state := self.hass.states.get(entity_id)) is not None:
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
    def icon(self):
        """Return the icon that will be shown in the interface."""
        return 'mdi:human'

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def state_attributes(self):
        weight = self._weight
        impedance = self._impedance
        height = self._attr_height
        age = self.GetAge(self._attr_born)
        gender = self._attr_gender
        model = self._attr_model
        problem = self._state
        problem_sensor = self._problems
        """Return the attributes of the entity.
        Provide the individual measurements from the
        sensor in the attributes of the device.
        """
        attrib = {
            ATTR_PROBLEM: self._problems,
            ATTR_SENSORS: self._readingmap,
            ATTR_MODEL: self._attr_model,
            ATTR_HEIGHT: "{}".format(height),
            ATTR_GENDER: self._attr_gender,
            ATTR_AGE: "{}".format(int(age)),
        }

        for reading in self._sensormap.values():
            attrib[reading] = getattr(self, f"_{reading}")

        if impedance is None and weight is None:
            pass
        elif problem_sensor == "weight unavailable" or problem_sensor == "impedance unavailable":
            pass
        elif model == "181D" and problem == "ok" or model == "181B" and problem_sensor == "impedance low" or model == "181B" and problem_sensor == "impedance unavailable" or impedance is None:
            lib = body_metrics.bodyMetrics(weight, height, age, gender, 0)
            bmi = lib.getBMI()
            visceral_fat = lib.getVisceralFat()
            basal_metabolism = lib.getBMR()
            attrib[ATTR_BMI] = "{:.1f}".format(bmi)
            attrib[ATTR_BMR] = "{:.0f}".format(basal_metabolism)
            attrib[ATTR_VISCERAL] = "{:.0f}".format(visceral_fat)
            attrib[ATTR_IDEAL] = "{:.2f}".format(lib.getIdealWeight())
            attrib[ATTR_BMILABEL] = lib.getBmiLabel()
        elif model == "181B" and problem == "ok":
            lib = body_metrics.bodyMetrics(weight, height, age, gender, impedance)
            bodyscale = ['Obese', 'Overweight', 'Thick-set', 'Lack-exercise', 'Balanced', 'Balanced-muscular', 'Skinny', 'Balanced-skinny', 'Skinny-muscular']
            bmi = lib.getBMI()
            bodyfat = lib.getFatPercentage() 
            muscle = lib.getMuscleMass()
            water = lib.getWaterPercentage()
            visceral_fat = lib.getVisceralFat()
            bone = lib.getBoneMass()
            basal_metabolism = lib.getBMR()
            protein = lib.getProteinPercentage()
            attrib[ATTR_BMI] = "{:.1f}".format(bmi)
            attrib[ATTR_BMR] = "{:.0f}".format(basal_metabolism)
            attrib[ATTR_VISCERAL] = "{:.0f}".format(visceral_fat)
            attrib[ATTR_IDEAL] = "{:.2f}".format(lib.getIdealWeight())
            attrib[ATTR_BMILABEL] = lib.getBmiLabel()
            attrib[ATTR_LBM] = "{:.1f}".format(lib.getLBMCoefficient())
            attrib[ATTR_FAT] = "{:.1f}".format(bodyfat)
            attrib[ATTR_WATER] = "{:.1f}".format(water)
            attrib[ATTR_BONES] = "{:.2f}".format(bone)
            attrib[ATTR_MUSCLE] = "{:.2f}".format(muscle)
            if lib.getFatMassToIdeal()['type'] == 'to_lose':
                attrib[ATTR_FATMASSTOLOSE] = "{:.2f}".format(lib.getFatMassToIdeal()['mass'])
            else:
                attrib[ATTR_FATMASSTOGAIN] = "{:.2f}".format(lib.getFatMassToIdeal()['mass'])
            attrib[ATTR_PROTEIN] = "{:.1f}".format(protein)
            attrib[ATTR_BODY] = bodyscale[lib.getBodyType()]
            attrib[ATTR_METABOLIC] = "{:.0f}".format(lib.getMetabolicAge())
            bs = body_score.bodyScore(age, gender, height, weight, bmi, bodyfat, muscle, water, visceral_fat, bone, basal_metabolism, protein)
            attrib[ATTR_BODY_SCORE] = "{:.0f}".format(bs.getBodyScore())

        return attrib

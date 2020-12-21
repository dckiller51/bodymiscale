"""Support for bodymiscale."""
from collections import deque
from datetime import datetime, timedelta
from math import floor
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

ATTR_PROBLEM = "problem"
ATTR_SENSORS = "sensors"
PROBLEM_NONE = "none"

# we're not returning only one value, we're returning a dict here. So we need
# to have a separate literal for it to avoid confusion.
ATTR_DICT_OF_UNITS_OF_MEASUREMENT = "unit_of_measurement_dict"

CONF_HEIGHT = "height"

CONF_SENSOR_WEIGHT = READING_WEIGHT

DEFAULT_HEIGHT = 60

SCHEMA_SENSORS = vol.Schema(
    {
        vol.Optional(CONF_SENSOR_WEIGHT): cv.entity_id,
    }
)

BODYMISCALE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SENSORS): vol.Schema(SCHEMA_SENSORS),
        vol.Optional(CONF_HEIGHT, default=DEFAULT_HEIGHT): cv.positive_int,
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


class Bodymiscale(Entity):
    """Bodymiscale the well-being of a body.

    It also checks the measurements against weight, height, age, 
    gender and * impedance (* only miscale 2)
    """

    READINGS = {
        READING_WEIGHT: {
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
        self._height = None
        self._weight = None
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
                value = float(value)
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
        """Return the attributes of the entity.

        Provide the individual measurements from the
        sensor in the attributes of the device.
        """
        attrib = {
            ATTR_PROBLEM: self._problems,
            ATTR_SENSORS: self._readingmap,
            ATTR_DICT_OF_UNITS_OF_MEASUREMENT: self._unit_of_measurement,
        }

        for reading in self._sensormap.values():
            attrib[reading] = getattr(self, f"_{reading}")

        return attrib

class bodyMetrics:
    def __init__(self, weight, height, age, gender, impedance):
        self._weight = weight
        self._height = height
        self._age = age
        self._gender = gender
        self._impedance = impedance

        # Check for potential out of boundaries
        if self.height > 220:
            raise Exception("Height is too high (limit: >220cm)")
        elif weight < 10 or weight > 200:
            raise Exception("Weight is either too low or too high (limits: <10kg and >200kg)")
        elif age > 99:
            raise Exception("Age is too high (limit >99 years)")
        elif impedance > 3000:
            raise Exception("Impedance is too high (limit >3000ohm)")

    # Set the value to a boundary if it overflows
    def checkValueOverflow(self, value, minimum, maximum):
        if value < minimum:
            return minimum
        elif value > maximum:
            return maximum
        else:
            return value

    # Get LBM coefficient (with impedance)
    def getLBMCoefficient(self):
        lbm =  (self.height * 9.058 / 100) * (self.height / 100)
        lbm += self.weight * 0.32 + 12.226
        lbm -= self.impedance * 0.0068
        lbm -= self.age * 0.0542
        return lbm

    # Get BMR
    def getBMR(self):
        if self.gender == 'female':
            bmr = 864.6 + self.weight * 10.2036
            bmr -= self.height * 0.39336
            bmr -= self.age * 6.204
        else:
            bmr = 877.8 + self.weight * 14.916
            bmr -= self.height * 0.726
            bmr -= self.age * 8.976

        # Capping
        #if self.gender == 'female' and bmr > 2996:
        #    bmr = 5000
        #elif self.gender == 'male' and bmr > 2322:
        #    bmr = 5000
        return self.checkValueOverflow(bmr, 500, 10000)

    # Get BMR scale
    def getBMRScale(self):
        coefficients = {
            'female': {12: 34, 15: 29, 17: 24, 29: 22, 50: 20, 120: 19},
            'male': {12: 36, 15: 30, 17: 26, 29: 23, 50: 21, 120: 20}
        }

        for age, coefficient in coefficients[self.gender].items():
            if self.age < age:
                return [self.weight * coefficient]
                break

    # Get fat percentage
    def getFatPercentage(self):
        # Set a constant to remove from LBM
        if self.gender == 'female' and self.age <= 49:
            const = 9.25
        elif self.gender == 'female' and self.age > 49:
            const = 7.25
        else:
            const = 0.8

        # Calculate body fat percentage
        LBM = self.getLBMCoefficient()

        if self.gender == 'male' and self.weight < 61:
            coefficient = 0.98
        elif self.gender == 'female' and self.weight > 60:
            coefficient = 0.96
            if self.height > 160:
                coefficient *= 1.03
        elif self.gender == 'female' and self.weight < 50:
            coefficient = 1.02
            if self.height > 160:
                coefficient *= 1.03
        else:
            coefficient = 1.0
        fatPercentage = (1.0 - (((LBM - const) * coefficient) / self.weight)) * 100

        # Capping body fat percentage
        if fatPercentage > 63:
            fatPercentage = 75
        return self.checkValueOverflow(fatPercentage, 5, 75)

    # Get fat percentage scale
    def getFatPercentageScale(self):
        # The included tables where quite strange, maybe bogus, replaced them with better ones...
        scales = [
            {'min': 0, 'max': 20, 'female': [18, 23, 30, 35], 'male': [8, 14, 21, 25]},
            {'min': 21, 'max': 25, 'female': [19, 24, 30, 35], 'male': [10, 15, 22, 26]},
            {'min': 26, 'max': 30, 'female': [20, 25, 31, 36], 'male': [11, 16, 21, 27]},
            {'min': 31, 'max': 35, 'female': [21, 26, 33, 36], 'male': [13, 17, 25, 28]},
            {'min': 36, 'max': 40, 'female': [22, 27, 34, 37], 'male': [15, 20, 26, 29]},
            {'min': 41, 'max': 45, 'female': [23, 28, 35, 38], 'male': [16, 22, 27, 30]},
            {'min': 46, 'max': 50, 'female': [24, 30, 36, 38], 'male': [17, 23, 29, 31]},
            {'min': 51, 'max': 55, 'female': [26, 31, 36, 39], 'male': [19, 25, 30, 33]},
            {'min': 56, 'max': 100, 'female': [27, 32, 37, 40], 'male': [21, 26, 31, 34]},
        ]

        for scale in scales:
            if self.age >= scale['min'] and self.age <= scale['max']:
                return scale[self.gender]

    # Get water percentage
    def getWaterPercentage(self):
        waterPercentage = (100 - self.getFatPercentage()) * 0.7

        if (waterPercentage <= 50):
            coefficient = 1.02
        else:
            coefficient = 0.98

        # Capping water percentage
        if waterPercentage * coefficient >= 65:
            waterPercentage = 75
        return self.checkValueOverflow(waterPercentage * coefficient, 35, 75)

    # Get water percentage scale
    def getWaterPercentageScale(self):
        return [53, 67]

    # Get bone mass
    def getBoneMass(self):
        if self.gender == 'female':
            base = 0.245691014
        else:
            base = 0.18016894

        boneMass = (base - (self.getLBMCoefficient() * 0.05158)) * -1

        if boneMass > 2.2:
            boneMass += 0.1
        else:
            boneMass -= 0.1

        # Capping boneMass
        if self.gender == 'female' and boneMass > 5.1:
            boneMass = 8
        elif self.gender == 'male' and boneMass > 5.2:
            boneMass = 8
        return self.checkValueOverflow(boneMass, 0.5 , 8)

    # Get bone mass scale
    def getBoneMassScale(self):
        scales = [
            {'female': {'min': 60, 'optimal': 2.5}, 'male': {'min': 75, 'optimal': 3.2}},
            {'female': {'min': 45, 'optimal': 2.2}, 'male': {'min': 69, 'optimal': 2.9}},
            {'female': {'min': 0, 'optimal': 1.8}, 'male': {'min': 0, 'optimal': 2.5}}
        ]

        for scale in scales:
            if self.weight >= scale[self.gender]['min']:
                return [scale[self.gender]['optimal']-1, scale[self.gender]['optimal']+1]

    # Get muscle mass
    def getMuscleMass(self):
        muscleMass = self.weight - ((self.getFatPercentage() * 0.01) * self.weight) - self.getBoneMass()

        # Capping muscle mass
        if self.gender == 'female' and muscleMass >= 84:
            muscleMass = 120
        elif self.gender == 'male' and muscleMass >= 93.5:
            muscleMass = 120

        return self.checkValueOverflow(muscleMass, 10 ,120)

    # Get muscle mass scale
    def getMuscleMassScale(self):
        scales = [
            {'min': 170, 'female': [36.5, 42.5], 'male': [49.5, 59.4]},
            {'min': 160, 'female': [32.9, 37.5], 'male': [44.0, 52.4]},
            {'min': 0, 'female': [29.1, 34.7], 'male': [38.5, 46.5]}
        ]

        for scale in scales:
            if self.height >= scale['min']:
                return scale[self.gender]

    # Get Visceral Fat
    def getVisceralFat(self):
        if self.gender == 'female':
            if self.weight > (13 - (self.height * 0.5)) * -1:
                subsubcalc = ((self.height * 1.45) + (self.height * 0.1158) * self.height) - 120
                subcalc = self.weight * 500 / subsubcalc
                vfal = (subcalc - 6) + (self.age * 0.07)
            else:
                subcalc = 0.691 + (self.height * -0.0024) + (self.height * -0.0024)
                vfal = (((self.height * 0.027) - (subcalc * self.weight)) * -1) + (self.age * 0.07) - self.age
        else:
            if self.height < self.weight * 1.6:
                subcalc = ((self.height * 0.4) - (self.height * (self.height * 0.0826))) * -1
                vfal = ((self.weight * 305) / (subcalc + 48)) - 2.9 + (self.age * 0.15)
            else:
                subcalc = 0.765 + self.height * -0.0015
                vfal = (((self.height * 0.143) - (self.weight * subcalc)) * -1) + (self.age * 0.15) - 5.0

        return self.checkValueOverflow(vfal, 1 ,50)

    # Get visceral fat scale
    def getVisceralFatScale(self):
        return [10, 15]

    # Get BMI
    def getBMI(self):
        return self.checkValueOverflow(self.weight/((self.height/100)*(self.height/100)), 10, 90)

    # Get BMI scale
    def getBMIScale(self):
        # Replaced library's version by mi fit scale, it seems better
        return [18.5, 25, 28, 32]

    # Get ideal weight (just doing a reverse BMI, should be something better)
    def getIdealWeight(self):
        return self.checkValueOverflow((22*self.height)*self.height/10000, 5.5, 198)

    # Get ideal weight scale (BMI scale converted to weights)
    def getIdealWeightScale(self):
        scale = []
        for bmiScale in self.getBMIScale():
            scale.append((bmiScale*self.height)*self.height/10000)
        return scale

    # Get fat mass to ideal (guessing mi fit formula)
    def getFatMassToIdeal(self):
        mass = (self.weight * (self.getFatPercentage() / 100)) - (self.weight * (self.getFatPercentageScale()[2] / 100))
        return mass

    # Get protetin percentage (warn: guessed formula)
    def getProteinPercentage(self):
        proteinPercentage = 100 - (floor(self.getFatPercentage() * 100) / 100)
        proteinPercentage -= floor(self.getWaterPercentage() * 100) / 100
        proteinPercentage -= floor((self.getBoneMass()/self.weight*100) * 100) / 100
        return proteinPercentage

    # Get protein scale (hardcoded in mi fit)
    def getProteinPercentageScale(self):
        return [16, 20]

    # Get body type (out of nine possible)
    def getBodyType(self):
        if self.getFatPercentage() > self.getFatPercentageScale()[2]:
            factor = 0
        elif self.getFatPercentage() < self.getFatPercentageScale()[1]:
            factor = 2
        else:
            factor = 1

        if self.getMuscleMass() > self.getMuscleMassScale()[1]:
            return self.getBodyTypeScale()[2 + (factor * 3)]
        elif self.getMuscleMass() < self.getMuscleMassScale()[0]:
            return self.getBodyTypeScale()[(factor * 3)]
        else:
            return self.getBodyTypeScale()[1 + (factor * 3)]

    # Return body type scale
    def getBodyTypeScale(self):
        return ['Obèse', 'Surpoids', 'Trapu', 'Manque d\'exercice', 'Equilibré', 'Equilibré musclé', 'Maigre', 'Equilibré maigre', 'Maigre musclé']

    def getImcLabel(self):
        imc = self.getBMI()
        if imc <18.5:
            return 'Maigreur'
        elif imc >= 18.5 and imc <25:
            return 'Corpulence Normale'
        elif imc >= 25 and imc <27:
            return 'Léger surpoids'
        elif imc >= 27 and imc <30:
            return 'Surpoids'
        elif imc >= 30 and imc <35:
            return 'Obésité modérée'
        elif imc >= 35 and imc <40:
            return 'Obésité sévère'
        elif imc >= 40:
            return 'Obésité massive'
import logging
from collections import defaultdict
from datetime import timedelta

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    ATTR_ATTRIBUTION,
)

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import Throttle
from homeassistant.util import slugify
from homeassistant.util.dt import now, parse_date

import time

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)

__VERSION__ = "1.0.0.0"

ATTR_WEIGHT = "weight"
ATTR_BMI = "bmi"
ATTR_BASAL_METABOLISM = "basal_metabolism"
ATTR_VISCERAL_FAT = "visceral_fat"
ATTR_IDEAL_WEIGHT = "ideal_weight"
ATTR_IMCLABEL = "imclabel"

DEFAUT_WEIGHT = "0"
DEFAUT_IMPEDANCE = "0"
WEIGHT = "weight"
IMPEDANCE = "impedance"
HEIGHT = "height"
AGE = "age"
GENDER = "gender"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(HEIGHT): cv.positive_int,
        vol.Required(AGE): cv.string,
        vol.Required(GENDER): cv.string,
        vol.Optional(WEIGHT, default=DEFAUT_WEIGHT): cv.positive_int,
        vol.Optional(IMPEDANCE, default=DEFAUT_IMPEDANCE): cv.positive_int,
    }
)

from . import bodymiscale

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the platform."""
    _LOGGER.info("mybodymiscale version %s " %( __VERSION__))
    name = config.get(CONF_NAME)
    weight = float(config.get(WEIGHT))
    impedance = float(config.get(IMPEDANCE))
    height = config.get(HEIGHT)
    age = config.get(AGE)
    gender = config.get(GENDER)

    try:
        session = []
    except :
        _LOGGER.exception("Could not run my First Extension")
        return False
    mydatabody = (weight, height, age, gender, 0)
    add_entities([mybodymiscale(session, name, mydatabody )], True)

class mybodymiscale(Entity):
    """."""

    def __init__(self, session, name, mydatabody):
        """Initialize the sensor."""
        self._session = session
        self._name = name
        self._mydatabody = mydatabody
        self._data = {}
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return "bodymiscale.%s" %(self._name)

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def device_state_attributes(self):
        return {
            ATTR_WEIGHT: self._data.get("weight"),
            ATTR_BMI: self._data.get("bmi"),
            ATTR_BASAL_METABOLISM: self._data.get("basal_metabolism"),
            ATTR_VISCERAL_FAT: self._data.get("visceral_fat"),
            ATTR_IDEAL_WEIGHT: self._data.get("ideal_weight"),
            ATTR_IMCLABEL: self._data.get("imclabel")
        }

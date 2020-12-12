import logging
from datetime import datetime, timedelta

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from custom_components.bodymiscale.const import (
    CONF_USER,
    CONF_WEIGHT,
    CONF_IMPEDANCE,
    CONF_HEIGHT,
    CONF_AGE,
    CONF_GENDER,
    CURRENCY_ATTRIBUTE,
    DEFAULT_NAME,
)
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_ID, CONF_USER, CONF_NAME, CONF_WEIGHT, CONF_IMPEDANCE, CONF_HEIGHT, CONF_AGE, CONF_GENDER
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)

STOCK_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ID): cv.string,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_USER): cv.string,
        vol.Optional(CONF_WEIGHT): cv.positive_int,
        vol.Optional(CONF_IMPEDANCE): cv.positive_int,
        vol.Optional(CONF_HEIGHT): cv.positive_int,
        vol.Optional(CONF_AGE): cv.string,
        vol.Optional(CONF_GENDER): cv.string,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the BodyMiscale sensor."""
    session = async_create_clientsession(hass)
    user = config.get(CONF_USER)
    weight = config.get(CONF_WEIGHT)
    impedance = config.get(CONF_IMPEDANCE)
    height = config.get(CONF_HEIGHT)
    age = config.get(CONF_AGE)
    gender = config.get(CONF_GENDER)
    entities = []
    if isinstance(user, int):
        name = config.get(CONF_NAME)
        weight = config.get(CONF_WEIGHT)
        impedance = config.get(CONF_IMPEDANCE)
        height = config.get(CONF_HEIGHT)
        age = config.get(CONF_AGE)
        gender = config.get(CONF_GENDER)
        if name is None:
            name = DEFAULT_NAME + " " + str(user)
        entities.append(
            BodyMiscaleSensor(
                hass,
                user,
                name,
                weight,
                impedance,
                height,
                age,
                gender,
                session,
            )
        )
        _LOGGER.info("Tracking %s [%d] using Miscale Esphome" % (name, user))
    else:
        for s in user:
            id = s.get(CONF_ID)
            name = s.get(CONF_NAME)
            if name is None:
                name = DEFAULT_NAME + " " + str(id)
            entities.append(
                BodyMiscaleSensor(
                    hass,
                    id,
                    name,
                    weight,
                    impedance,
                    height,
                    age,
                    gender,
                    session,
                )
            )
            _LOGGER.info("Tracking %s [%d] using Miscale Esphome" % (name, id))
    async_add_entities(entities, True)
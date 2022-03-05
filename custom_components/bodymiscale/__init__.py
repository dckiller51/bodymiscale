"""Support for bodymiscale."""
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_SENSORS,
    STATE_OK,
    STATE_PROBLEM,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import StateType

from custom_components.bodymiscale.const import (
    ATTR_AGE,
    ATTR_BMI,
    ATTR_BMILABEL,
    ATTR_BMR,
    ATTR_BODY,
    ATTR_BODY_SCORE,
    ATTR_BONES,
    ATTR_BORN,
    ATTR_FAT,
    ATTR_FATMASSTOGAIN,
    ATTR_FATMASSTOLOSE,
    ATTR_GENDER,
    ATTR_HEIGHT,
    ATTR_IDEAL,
    ATTR_LBM,
    ATTR_METABOLIC,
    ATTR_MODEL,
    ATTR_MUSCLE,
    ATTR_PROBLEM,
    ATTR_PROTEIN,
    ATTR_SENSORS,
    ATTR_VISCERAL,
    ATTR_WATER,
    CONF_MAX_IMPEDANCE,
    CONF_MAX_WEIGHT,
    CONF_MIN_IMPEDANCE,
    CONF_MIN_WEIGHT,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_WEIGHT,
    DEFAULT_MAX_IMPEDANCE,
    DEFAULT_MAX_WEIGHT,
    DEFAULT_MIN_IMPEDANCE,
    DEFAULT_MIN_WEIGHT,
    DEFAULT_MODEL,
    DOMAIN,
    PROBLEM_NONE,
    READING_IMPEDANCE,
    READING_WEIGHT,
    STARTUP_MESSAGE,
    UNIT_POUNDS,
)

from .body_metrics import BodyMetrics, BodyMetricsImpedance
from .body_score import BodyScore

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
        vol.Optional(CONF_MIN_WEIGHT, default=DEFAULT_MIN_WEIGHT): vol.Coerce(float),
        vol.Optional(CONF_MAX_WEIGHT, default=DEFAULT_MAX_WEIGHT): vol.Coerce(float),
        vol.Optional(
            CONF_MIN_IMPEDANCE, default=DEFAULT_MIN_IMPEDANCE
        ): cv.positive_int,
        vol.Optional(
            CONF_MAX_IMPEDANCE, default=DEFAULT_MAX_IMPEDANCE
        ): cv.positive_int,
        vol.Required(ATTR_HEIGHT): cv.positive_int,
        vol.Required(ATTR_BORN): cv.string,
        vol.Required(ATTR_GENDER): cv.string,
        vol.Optional(ATTR_MODEL, default=DEFAULT_MODEL): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: {cv.string: BODYMISCALE_SCHEMA}}, extra=vol.ALLOW_EXTRA
)

SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Bodymiscale component."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    component = EntityComponent(_LOGGER, DOMAIN, hass)

    entities = []
    for bodymiscale_name, bodymiscale_config in config[DOMAIN].items():
        _LOGGER.info("Added bodymiscale %s", bodymiscale_name)
        entity = Bodymiscale(bodymiscale_name, bodymiscale_config)
        entities.append(entity)

    await component.async_add_entities(entities)

    return True


def _get_age(date: str) -> int:
    born = datetime.strptime(date, "%Y-%m-%d")
    today = datetime.today()
    age = today.year - born.year
    if (today.month, today.day) < (born.month, born.day):
        age -= 1
    return age


class Bodymiscale(Entity):  # type: ignore
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

    def __init__(self, name: str, config: dict[str, Any]):
        """Initialize the Bodymiscale component."""
        self._config = config
        self._state: Optional[str] = None
        self._name = name
        self._problems = PROBLEM_NONE
        self._weight: Optional[float] = None
        self._impedance: Optional[int] = None
        self._attr_height = self._config[ATTR_HEIGHT]
        self._attr_born = self._config[ATTR_BORN]
        self._attr_gender = self._config[ATTR_GENDER]
        self._attr_model = self._config[ATTR_MODEL]

    @callback  # type: ignore
    def _state_changed_event(self, event: Event) -> None:
        """Sensor state change event."""
        self._state_changed(event.data.get("entity_id"), event.data.get("new_state"))

    @callback  # type: ignore
    def _state_changed(self, entity_id: str, new_state: State) -> None:
        """Update the sensor status."""
        if new_state is None:
            return
        value = new_state.state
        _LOGGER.debug("Received callback from %s with value %s", entity_id, value)
        if value == STATE_UNKNOWN:
            return

        for sensor_type, sensor_entity_id in self._config[CONF_SENSORS].items():
            if entity_id != sensor_entity_id:
                continue

            if value != STATE_UNAVAILABLE:
                value = float(value)

            if sensor_type == CONF_SENSOR_WEIGHT:
                if new_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UNIT_POUNDS:
                    value = value * 0.45359237
                self._weight = value
            else:
                self._impedance = value

            self._update_state()
            return

        raise HomeAssistantError(f"Unknown reading from sensor {entity_id}: {value}")

    def _update_state(self) -> None:
        """Update the state of the class based sensor data."""
        result = []
        for sensor_type in self._config[CONF_SENSORS].keys():
            params = self.READINGS[sensor_type]
            if (value := getattr(self, f"_{sensor_type}")) is not None:
                if value == STATE_UNAVAILABLE:
                    result.append(f"{sensor_type} unavailable")
                else:
                    if self._is_below_min(value, params):
                        result.append(f"{sensor_type} low")
                    if self._is_above_max(value, params):
                        result.append(f"{sensor_type} high")

        if result:
            self._state = STATE_PROBLEM
            self._problems = ", ".join(result)
        else:
            self._state = STATE_OK
            self._problems = PROBLEM_NONE
        _LOGGER.debug("New data processed")
        self.async_write_ha_state()

    def _is_below_min(self, value: float, params: dict[str, str]) -> bool:
        """If configured, check the value against the defined minimum value."""
        if "min" in params and params["min"] in self._config:
            min_value = self._config[params["min"]]
            if value < min_value:
                return True

        return False

    def _is_above_max(self, value: float, params: dict[str, str]) -> bool:
        """If configured, check the value against the defined maximum value."""
        if "max" in params and params["max"] in self._config:
            max_value = self._config[params["max"]]
            if value > max_value:
                return True

        return False

    async def async_added_to_hass(self) -> None:
        """After being added to hass."""

        async_track_state_change_event(
            self.hass,
            list(self._config[CONF_SENSORS].values()),
            self._state_changed_event,
        )

        for entity_id in self._config[CONF_SENSORS].values():
            if (state := self.hass.states.get(entity_id)) is not None:
                self._state_changed(entity_id, state)

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self) -> str:
        """Return the icon that will be shown in the interface."""
        return "mdi:human"

    @property
    def state(self) -> StateType:
        """Return the state of the entity."""
        return self._state

    @property
    def state_attributes(self) -> dict[str, Any]:
        """Return the attributes of the entity."""
        age = _get_age(self._attr_born)
        problem = self._state
        problem_sensor = self._problems
        attrib = {
            ATTR_PROBLEM: self._problems,
            ATTR_SENSORS: self._config[CONF_SENSORS],
            ATTR_MODEL: self._attr_model,
            ATTR_HEIGHT: f"{self._attr_height}",
            ATTR_GENDER: self._attr_gender,
            ATTR_AGE: f"{age}",
        }

        for reading in self._config[CONF_SENSORS].keys():
            attrib[reading] = getattr(self, f"_{reading}")

        if self._weight is None or "unavailable" in problem_sensor or problem != "ok":
            return attrib

        metrics = BodyMetrics(self._weight, self._attr_height, age, self._attr_gender)

        if (
            self._attr_model == "181B"
            and "impedance" not in problem_sensor
            and self._impedance is not None
        ):
            metrics = BodyMetricsImpedance(
                self._weight, self._attr_height, age, self._attr_gender, self._impedance
            )

        attrib[ATTR_BMI] = f"{metrics.bmi:.1f}"
        attrib[ATTR_BMR] = f"{metrics.bmr:.0f}"
        attrib[ATTR_VISCERAL] = f"{metrics.visceral_fat:.0f}"
        attrib[ATTR_IDEAL] = f"{metrics.ideal_weight:.2f}"
        attrib[ATTR_BMILABEL] = metrics.bmi_label

        if isinstance(metrics, BodyMetricsImpedance):
            bodyscale = [
                "Obese",
                "Overweight",
                "Thick-set",
                "Lack-exercise",
                "Balanced",
                "Balanced-muscular",
                "Skinny",
                "Balanced-skinny",
                "Skinny-muscular",
            ]
            attrib[ATTR_LBM] = f"{metrics.lbm_coefficient:.1f}"
            attrib[ATTR_FAT] = f"{metrics.fat_percentage:.1f}"
            attrib[ATTR_WATER] = f"{metrics.water_percentage:.1f}"
            attrib[ATTR_BONES] = f"{metrics.bone_mass:.2f}"
            attrib[ATTR_MUSCLE] = f"{metrics.muscle_mass:.2f}"
            fat_mass_to_ideal = metrics.fat_mass_to_ideal
            if fat_mass_to_ideal["type"] == "to_lose":
                attrib[ATTR_FATMASSTOLOSE] = f"{fat_mass_to_ideal['mass']:.2f}"
            else:
                attrib[ATTR_FATMASSTOGAIN] = f"{fat_mass_to_ideal['mass']:.2f}"
            attrib[ATTR_PROTEIN] = f"{metrics.protein_percentage:.1f}"
            attrib[ATTR_BODY] = bodyscale[metrics.body_type]
            attrib[ATTR_METABOLIC] = f"{metrics.metabolic_age:.0f}"
            body_score = BodyScore(metrics)
            attrib[ATTR_BODY_SCORE] = f"{body_score.body_score:.0f}"

        return attrib

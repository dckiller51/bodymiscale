"""Coordinator module."""
import logging
from datetime import datetime
from typing import Any, Optional, Union

from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, State, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_state_change_event

from .body_metrics import BodyMetrics, BodyMetricsImpedance
from .const import (
    ATTR_AGE,
    CONF_BIRTHDAY,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_WEIGHT,
    CONSTRAINT_IMPEDANCE_MAX,
    CONSTRAINT_IMPEDANCE_MIN,
    CONSTRAINT_WEIGHT_MAX,
    CONSTRAINT_WEIGHT_MIN,
    MAX,
    MIN,
    PROBLEM_NONE,
    UNIT_POUNDS,
)
from .models import Gender

_LOGGER = logging.getLogger(__name__)


def _get_age(date: str) -> int:
    born = datetime.strptime(date, "%Y-%m-%d")
    today = datetime.today()
    age = today.year - born.year
    if (today.month, today.day) < (born.month, born.day):
        age -= 1
    return age


class BodyScaleCoordinator:
    """Body scale coordinator."""

    READINGS = {
        CONF_SENSOR_WEIGHT: {
            MIN: CONSTRAINT_WEIGHT_MIN,
            MAX: CONSTRAINT_WEIGHT_MAX,
        },
        CONF_SENSOR_IMPEDANCE: {
            MIN: CONSTRAINT_IMPEDANCE_MIN,
            MAX: CONSTRAINT_IMPEDANCE_MAX,
        },
    }

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]):
        self._hass = hass
        self._config: dict[str, Any] = {
            **config,
            ATTR_AGE: _get_age(config[CONF_BIRTHDAY]),
            CONF_GENDER: Gender(config[CONF_GENDER]),
        }
        self._subscriptions: list[CALLBACK_TYPE] = []
        self._remove_listener: Optional[CALLBACK_TYPE] = None

        self._problems = PROBLEM_NONE
        self._weight: Optional[float] = None
        self._impedance: Optional[int] = None

    def subscribe(self, callback_func: CALLBACK_TYPE) -> CALLBACK_TYPE:
        """Subscribe for changes."""
        self._subscriptions.append(callback_func)

        if len(self._subscriptions) == 1:
            sensors = [self._config[CONF_SENSOR_WEIGHT]]
            if CONF_SENSOR_IMPEDANCE in self._config:
                sensors.append(self._config[CONF_SENSOR_IMPEDANCE])

            self._remove_listener = async_track_state_change_event(
                self._hass,
                sensors,
                self._state_changed_event,
            )

            for entity_id in sensors:
                if (state := self._hass.states.get(entity_id)) is not None:
                    self._state_changed(entity_id, state)

        @callback  # type: ignore[misc]
        def remove_listener() -> None:
            """Remove subscribtion."""
            self._subscriptions.remove(callback_func)

            if len(self._subscriptions) == 0 and self._remove_listener:
                self._remove_listener()

        return remove_listener

    @callback  # type: ignore[misc]
    def _state_changed_event(self, event: Event) -> None:
        """Sensor state change event."""
        self._state_changed(event.data.get("entity_id"), event.data.get("new_state"))

    @callback  # type: ignore[misc]
    def _state_changed(self, entity_id: str, new_state: State) -> None:
        """Update the sensor status."""
        if new_state is None:
            return

        value = new_state.state
        _LOGGER.debug("Received callback from %s with value %s", entity_id, value)
        if value == STATE_UNKNOWN:
            return

        if value != STATE_UNAVAILABLE:
            value = float(value)

        if entity_id == self._config[CONF_SENSOR_WEIGHT]:
            if new_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UNIT_POUNDS:
                value = value * 0.45359237
            self._weight = value
        elif entity_id == self._config.get(CONF_SENSOR_IMPEDANCE, None):
            self._impedance = value
        else:
            raise HomeAssistantError(
                f"Unknown reading from sensor {entity_id}: {value}"
            )

        self._update_state()

    def _update_state(self) -> None:
        """Update the state of the class based sensor data."""
        problems = []
        sensor_types = [CONF_SENSOR_WEIGHT]
        if CONF_SENSOR_IMPEDANCE in self._config:
            sensor_types.append(CONF_SENSOR_IMPEDANCE)

        for sensor_type in sensor_types:
            params = self.READINGS[sensor_type]
            if (value := getattr(self, f"_{sensor_type}")) is not None:
                if value == STATE_UNAVAILABLE:
                    problems.append(f"{sensor_type} unavailable")
                else:
                    if value < params[MIN]:
                        problems.append(f"{sensor_type} low")
                    elif value > params[MAX]:
                        problems.append(f"{sensor_type} high")

        if problems:
            self._problems = ", ".join(problems)
        else:
            self._problems = PROBLEM_NONE

        _LOGGER.debug("New data processed")
        for sub_callback in self._subscriptions:
            sub_callback()

    @property
    def config(self) -> dict[str, Any]:
        """Return config."""
        return self._config

    @property
    def problems(self) -> str:
        """Return problems."""
        return self._problems

    @property
    def weight(self) -> Optional[float]:
        """Return weight."""
        return self._weight

    @property
    def impedance(self) -> Optional[float]:
        """Return impedance."""
        return self._impedance

    @property
    def metrics(self) -> Union[BodyMetrics, BodyMetricsImpedance, None]:
        """Return metrics object."""
        if CONF_SENSOR_WEIGHT in self._problems or self._weight is None:
            return None

        height: int = self._config[CONF_HEIGHT]
        gender: Gender = self._config[CONF_GENDER]
        age = self._config[ATTR_AGE]

        metrics = BodyMetrics(self._weight, height, age, gender)

        if CONF_SENSOR_IMPEDANCE not in self._problems and self._impedance is not None:
            metrics = BodyMetricsImpedance(
                self._weight, height, age, gender, self._impedance
            )

        return metrics

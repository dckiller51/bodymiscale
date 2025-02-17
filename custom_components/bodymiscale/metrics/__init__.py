"""Metrics module."""

import logging
from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass, field
from typing import Any

from cachetools import TTLCache
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, State, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import StateType

from custom_components.bodymiscale.metrics.scale import Scale
from custom_components.bodymiscale.util import get_age

from ..const import (
    CONF_BIRTHDAY,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_SCALE,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_WEIGHT,
    CONSTRAINT_IMPEDANCE_MAX,
    CONSTRAINT_IMPEDANCE_MIN,
    CONSTRAINT_WEIGHT_MAX,
    CONSTRAINT_WEIGHT_MIN,
    PROBLEM_NONE,
    UNIT_POUNDS,
)
from ..models import Gender, Metric
from .body_score import get_body_score
from .impedance import (
    get_body_type,
    get_bone_mass,
    get_fat_mass_to_ideal_weight,
    get_fat_percentage,
    get_lbm,
    get_metabolic_age,
    get_muscle_mass,
    get_protein_percentage,
    get_water_percentage,
)
from .weight import get_bmi, get_bmr, get_visceral_fat

_LOGGER = logging.getLogger(__name__)


@dataclass
class MetricInfo:
    """Metric info."""

    depends_on: list[Metric]
    calculate: Callable[[Mapping[str, Any], Mapping[Metric, StateType]], StateType]
    decimals: int | None = None  # Round decimals before passing to the subscribers
    depended_by: list[Metric] = field(default_factory=list, init=False)


_METRIC_DEPS: dict[Metric, MetricInfo] = {
    Metric.STATUS: MetricInfo([], lambda c, s: None),
    Metric.AGE: MetricInfo([], lambda c, s: None, 0),
    Metric.WEIGHT: MetricInfo([], lambda c, s: None, 2),
    Metric.IMPEDANCE: MetricInfo([], lambda c, s: None, 0),
    # require weight
    Metric.BMI: MetricInfo([Metric.WEIGHT], get_bmi, 1),
    Metric.BMR: MetricInfo([Metric.AGE, Metric.WEIGHT], get_bmr, 0),
    Metric.VISCERAL_FAT: MetricInfo([Metric.AGE, Metric.WEIGHT], get_visceral_fat, 0),
    # require weight & impedance
    Metric.LBM: MetricInfo([Metric.AGE, Metric.WEIGHT, Metric.IMPEDANCE], get_lbm, 1),
    Metric.FAT_PERCENTAGE: MetricInfo(
        [Metric.AGE, Metric.WEIGHT, Metric.LBM], get_fat_percentage, 1
    ),
    Metric.WATER_PERCENTAGE: MetricInfo(
        [Metric.FAT_PERCENTAGE], get_water_percentage, 1
    ),
    Metric.BONE_MASS: MetricInfo([Metric.LBM], get_bone_mass, 2),
    Metric.MUSCLE_MASS: MetricInfo(
        [Metric.WEIGHT, Metric.FAT_PERCENTAGE, Metric.BONE_MASS], get_muscle_mass, 2
    ),
    Metric.METABOLIC_AGE: MetricInfo(
        [Metric.WEIGHT, Metric.AGE, Metric.IMPEDANCE], get_metabolic_age, 0
    ),
    Metric.PROTEIN_PERCENTAGE: MetricInfo(
        [Metric.WEIGHT, Metric.MUSCLE_MASS, Metric.WATER_PERCENTAGE],
        get_protein_percentage,
        1,
    ),
    Metric.FAT_MASS_2_IDEAL_WEIGHT: MetricInfo(
        [Metric.WEIGHT, Metric.FAT_PERCENTAGE, Metric.AGE],
        get_fat_mass_to_ideal_weight,
        2,
    ),
    Metric.BODY_TYPE: MetricInfo(
        [Metric.MUSCLE_MASS, Metric.FAT_PERCENTAGE, Metric.AGE],
        get_body_type,
    ),
    Metric.BODY_SCORE: MetricInfo(
        [
            Metric.BMI,
            Metric.FAT_PERCENTAGE,
            Metric.AGE,
            Metric.MUSCLE_MASS,
            Metric.WATER_PERCENTAGE,
            Metric.WEIGHT,
            Metric.BONE_MASS,
            Metric.BMR,
            Metric.VISCERAL_FAT,
            Metric.PROTEIN_PERCENTAGE,
        ],
        get_body_score,
        0,
    ),
}


def _modify_state_for_subscriber(
    metric_info: MetricInfo, state: StateType
) -> StateType:
    if isinstance(state, float) and metric_info.decimals is not None:
        state = round(state, metric_info.decimals)

    return state


class BodyScaleMetricsHandler:
    """Body scale metrics handler."""

    def __init__(
        self, hass: HomeAssistant, config: dict[str, Any], config_entry_id: str
    ):
        self._available_metrics: MutableMapping[Metric, StateType] = TTLCache(
            maxsize=len(Metric), ttl=60
        )
        self._hass = hass
        self._config: dict[str, Any] = {
            **config,
            CONF_GENDER: Gender(config[CONF_GENDER]),
        }
        self._config_entry_id = config_entry_id

        self._config[CONF_SCALE] = Scale(
            self._config[CONF_HEIGHT], self._config[CONF_GENDER]
        )

        self._subscribers: dict[Metric, list[Callable[[StateType], None]]] = {}
        self._dependencies: dict[Metric, MetricInfo] = {}
        for key, value in _METRIC_DEPS.items():
            self._dependencies[key] = value

            for dep in value.depends_on:
                info_dep = self._dependencies[dep]
                info_dep.depended_by.append(key)

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

    @property
    def config(self) -> Mapping[str, Any]:
        """Return config."""
        return self._config

    @property
    def config_entry_id(self) -> str:
        """Return config entry id."""
        return self._config_entry_id

    def subscribe(
        self, metric: Metric, callback_func: Callable[[StateType], None]
    ) -> CALLBACK_TYPE:
        """Subscribe for changes."""
        self._subscribers.setdefault(metric, [])

        self._subscribers[metric].append(callback_func)

        @callback  # type: ignore[misc]
        def remove_listener() -> None:
            """Remove subscribtion."""
            self._subscribers[metric].remove(callback_func)

        # If a state is available call subscriber function with current state.
        state = self._available_metrics.get(metric, None)
        if state is not None:
            callback_func(
                _modify_state_for_subscriber(self._dependencies[metric], state)
            )

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
            if self._is_valid(
                CONF_SENSOR_WEIGHT, value, CONSTRAINT_WEIGHT_MIN, CONSTRAINT_WEIGHT_MAX
            ):
                if new_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UNIT_POUNDS:
                    value = value * 0.45359237

                self._update_available_metric(Metric.WEIGHT, value)
        elif entity_id == self._config.get(CONF_SENSOR_IMPEDANCE, None):
            if self._is_valid(
                CONF_SENSOR_IMPEDANCE,
                value,
                CONSTRAINT_IMPEDANCE_MIN,
                CONSTRAINT_IMPEDANCE_MAX,
            ):
                self._update_available_metric(Metric.IMPEDANCE, value)
        else:
            raise HomeAssistantError(
                f"Unknown reading from sensor {entity_id}: {value}"
            )

    def _is_valid(
        self,
        name_sensor: str,
        state: StateType,
        constraint_min: int,
        constraint_max: int,
    ) -> bool:
        problem = None
        if state == STATE_UNAVAILABLE:
            problem = f"{name_sensor}_unavailable"
        elif state < constraint_min:
            problem = f"{name_sensor}_low"
        elif state > constraint_max:
            problem = f"{name_sensor}_high"

        new_statues = []
        for status in self._available_metrics.get(Metric.STATUS, "").split("_and_"):
            status = status.strip()
            if status == PROBLEM_NONE:
                continue

            if status.startswith(name_sensor):
                continue

            if status:
                new_statues.append(status)

        if problem:
            new_statues.append(problem)

        if new_statues:
            self._update_available_metric(Metric.STATUS, "_and_".join(new_statues))
            return problem is None

        self._update_available_metric(Metric.STATUS, PROBLEM_NONE)
        return True

    def _update_available_metric(self, metric: Metric, state: StateType) -> None:
        old_state = self._available_metrics.get(metric, None)
        if old_state is not None and old_state == state:
            _LOGGER.debug("No update required for %s.", metric)
            return

        self._available_metrics.setdefault(
            Metric.AGE, get_age(self._config[CONF_BIRTHDAY])
        )

        self._available_metrics[metric] = state

        metric_info = self._dependencies[metric]
        subscribers = self._subscribers.get(metric, [])
        if subscribers:
            subscriber_state = _modify_state_for_subscriber(metric_info, state)
            for subscriber in subscribers:
                subscriber(subscriber_state)

        for depended in metric_info.depended_by:
            depended_info = self._dependencies[depended]
            if all(dep in self._available_metrics for dep in depended_info.depends_on):
                value = depended_info.calculate(self._config, self._available_metrics)
                if value is not None:
                    self._update_available_metric(depended, value)

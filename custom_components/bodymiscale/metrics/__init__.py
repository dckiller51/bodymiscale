"""Metrics module."""

import logging
from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cachetools import TTLCache
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import StateType
from homeassistant.util.dt import get_time_zone

from custom_components.bodymiscale.metrics.scale import Scale
from custom_components.bodymiscale.util import get_age

from ..const import (
    CONF_BIRTHDAY,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_SCALE,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_LAST_MEASUREMENT_TIME,
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
    calculate: Callable[
        [Mapping[str, Any], Mapping[Metric, StateType | datetime]], StateType
    ]
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
    Metric.LAST_MEASUREMENT_TIME: MetricInfo([], lambda c, s: None),
}


def _modify_state_for_subscriber(
    metric_info: MetricInfo, state: StateType | datetime
) -> StateType | datetime:
    if isinstance(state, float) and metric_info.decimals is not None:
        state = round(state, metric_info.decimals)

    return state


class BodyScaleMetricsHandler:
    """Body scale metrics handler."""

    def __init__(
        self, hass: HomeAssistant, config: dict[str, Any], config_entry_id: str
    ):
        self._status: str = PROBLEM_NONE
        # La définition de type du cache revient à StateType
        self._available_metrics: MutableMapping[Metric, StateType | datetime] = (
            TTLCache(maxsize=len(Metric), ttl=60)
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

        self._subscribers: dict[
            Metric, list[Callable[[StateType | datetime], None]]
        ] = {}
        self._dependencies: dict[Metric, MetricInfo] = {}
        for key, value in _METRIC_DEPS.items():
            self._dependencies[key] = value

            for dep in value.depends_on:
                info_dep = self._dependencies[dep]
                info_dep.depended_by.append(key)

        sensors = [self._config[CONF_SENSOR_WEIGHT]]
        if CONF_SENSOR_IMPEDANCE in self._config:
            sensors.append(self._config[CONF_SENSOR_IMPEDANCE])
        if CONF_SENSOR_LAST_MEASUREMENT_TIME in self._config:
            sensors.append(self._config[CONF_SENSOR_LAST_MEASUREMENT_TIME])

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
        self, metric: Metric, callback_func: Callable[[StateType | datetime], None]
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
    def _state_changed_event(self, event: Event[EventStateChangedData]) -> None:
        """Sensor state change event."""
        self._state_changed(event.data.get("entity_id"), event.data.get("new_state"))

    @callback  # type: ignore[misc]
    def _state_changed(self, entity_id: str | None, new_state: State | None) -> None:
        """Update the sensor status."""
        if entity_id is None or new_state is None or new_state.state == STATE_UNKNOWN:
            return

        value = new_state.state
        _LOGGER.debug("Received callback from %s with value %s", entity_id, value)

        problem = None
        weight_updated_valid = False
        impedance_updated_valid = False

        if entity_id == self._config[CONF_SENSOR_WEIGHT]:
            weight_updated_valid, problem = self._process_weight(new_state)

        elif entity_id == self._config.get(CONF_SENSOR_IMPEDANCE):
            impedance_updated_valid, problem = self._process_impedance(new_state)

        elif entity_id == self._config.get(CONF_SENSOR_LAST_MEASUREMENT_TIME):
            problem = self._process_last_measurement_time(new_state)

        if problem:
            self._add_sensor_problem(entity_id, problem)

        if weight_updated_valid or impedance_updated_valid:
            self._trigger_dependent_recalculation()

    def _process_weight(self, state: State) -> tuple[bool, str | None]:
        value = state.state

        if value == STATE_UNAVAILABLE:
            self._remove_sensor_problem(CONF_SENSOR_WEIGHT)
            return False, "unavailable"

        try:
            value_float = float(value)
        except ValueError as e:
            _LOGGER.warning("Could not convert weight %s to float: %s", value, e)
            self._remove_sensor_problem(CONF_SENSOR_WEIGHT)
            return False, "invalid_format"

        if not self._is_valid(
            CONF_SENSOR_WEIGHT,
            value_float,
            CONSTRAINT_WEIGHT_MIN,
            CONSTRAINT_WEIGHT_MAX,
        ):
            return False, self._categorize_problem(
                value_float, CONSTRAINT_WEIGHT_MIN, CONSTRAINT_WEIGHT_MAX
            )

        # Convert pounds to kg if necessary
        if state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UNIT_POUNDS:
            value_float *= 0.45359237

        updated = self._update_available_metric(Metric.WEIGHT, value_float)
        if updated:
            self._remove_sensor_problem(CONF_SENSOR_WEIGHT)
        return updated, None

    def _process_impedance(self, state: State) -> tuple[bool, str | None]:
        value = state.state

        if value == STATE_UNAVAILABLE:
            self._remove_sensor_problem(CONF_SENSOR_IMPEDANCE)
            return False, "unavailable"

        try:
            value_float = float(value)
        except ValueError as e:
            _LOGGER.warning("Could not convert impedance %s to float: %s", value, e)
            self._remove_sensor_problem(CONF_SENSOR_IMPEDANCE)
            return False, "invalid_format"

        if not self._is_valid(
            CONF_SENSOR_IMPEDANCE,
            value_float,
            CONSTRAINT_IMPEDANCE_MIN,
            CONSTRAINT_IMPEDANCE_MAX,
        ):
            return False, self._categorize_problem(
                value_float, CONSTRAINT_IMPEDANCE_MIN, CONSTRAINT_IMPEDANCE_MAX
            )

        updated = self._update_available_metric(Metric.IMPEDANCE, value_float)
        if updated:
            self._remove_sensor_problem(CONF_SENSOR_IMPEDANCE)
        return updated, None

    def _process_last_measurement_time(self, state: State) -> str | None:
        value = state.state

        if value == STATE_UNAVAILABLE:
            self._remove_sensor_problem(CONF_SENSOR_LAST_MEASUREMENT_TIME)
            return "unavailable"

        if not self._is_valid(CONF_SENSOR_LAST_MEASUREMENT_TIME, value, None, None):
            self._remove_sensor_problem(CONF_SENSOR_LAST_MEASUREMENT_TIME)
            return "invalid"

        try:
            dt = datetime.fromisoformat(value)
            tz = get_time_zone(self._hass.config.time_zone)
            dt = dt.replace(tzinfo=tz)
            # CORRECTION FINALE : Stocker la chaîne de caractères
            self._update_available_metric(Metric.LAST_MEASUREMENT_TIME, dt)
            self._remove_sensor_problem(CONF_SENSOR_LAST_MEASUREMENT_TIME)
            self._trigger_dependent_recalculation()
            return None
        except ValueError:
            return "invalid_format"

    def _categorize_problem(
        self, value: float, min_val: float | None, max_val: float | None
    ) -> str:
        if min_val is not None and value < min_val:
            return "low"
        if max_val is not None and value > max_val:
            return "high"
        return "invalid"

    def _add_sensor_problem(self, entity_id: str, error_type: str) -> None:
        """Add a specific sensor problem to the status while maintaining order and without duplicates."""
        sensor_key = None
        if entity_id == self._config[CONF_SENSOR_WEIGHT]:
            sensor_key = "weight"
        elif entity_id == self._config.get(CONF_SENSOR_IMPEDANCE):
            sensor_key = "impedance"
        elif entity_id == self._config.get(CONF_SENSOR_LAST_MEASUREMENT_TIME):
            sensor_key = "last_time"

        if sensor_key:
            problem_string = f"{sensor_key}_{error_type}"
            current_status = self._status
            status_parts = [
                s.strip()
                for s in current_status.split("_and_")
                if s.strip() and s.strip() != PROBLEM_NONE
            ]

            if problem_string not in status_parts:
                status_parts.append(problem_string)

            ordered_problems = []
            weight_problems = []
            impedance_problems = []
            last_time_problems = []
            other_problems = []

            for part in sorted(list(set(status_parts))):
                if part.startswith("weight_"):
                    weight_problems.append(part)
                elif part.startswith("impedance_"):
                    impedance_problems.append(part)
                elif part.startswith("last_time_"):
                    last_time_problems.append(part)
                else:
                    other_problems.append(part)

            ordered_problems.extend(weight_problems)
            ordered_problems.extend(impedance_problems)
            ordered_problems.extend(last_time_problems)
            ordered_problems.extend(other_problems)

            final_status = "_and_".join(ordered_problems)
            self._update_available_metric(
                Metric.STATUS, final_status if final_status else PROBLEM_NONE
            )

    def _remove_sensor_problem(self, sensor_config_key: str) -> None:
        """Remove a specific sensor problem from the status."""
        sensor_key = None
        if sensor_config_key == CONF_SENSOR_WEIGHT:
            sensor_key = "weight"
        elif sensor_config_key == CONF_SENSOR_IMPEDANCE:
            sensor_key = "impedance"
        elif sensor_config_key == CONF_SENSOR_LAST_MEASUREMENT_TIME:
            sensor_key = "last_time"

        if sensor_key:
            current_status = self._status
            status_parts = [
                s.strip()
                for s in current_status.split("_and_")
                if s.strip() and not s.startswith(f"{sensor_key}_")
            ]
            final_status = "_and_".join(status_parts)
            self._update_available_metric(
                Metric.STATUS, final_status if final_status else PROBLEM_NONE
            )

    def _is_valid(
        self,
        name_sensor: str,
        state: StateType,
        constraint_min: int | None,
        constraint_max: int | None,
    ) -> bool:
        """Check if the sensor state is valid based on constraints."""
        if state == STATE_UNAVAILABLE:
            return False
        if name_sensor == CONF_SENSOR_LAST_MEASUREMENT_TIME:
            try:
                datetime.fromisoformat(str(state))
            except ValueError:
                return False
        # Only check constraints if state is not None and can be converted to float
        if constraint_min is not None or constraint_max is not None:
            if state is None:
                return False
            try:
                state_float = float(state)
            except (TypeError, ValueError):
                return False
            if constraint_min is not None and state_float < constraint_min:
                return False
            if constraint_max is not None and state_float > constraint_max:
                return False
        return True

    def _update_available_metric(
        self, metric: Metric, state: StateType | datetime
    ) -> bool:
        old_state = self._available_metrics.get(metric, None)
        if old_state is not None and old_state == state:
            _LOGGER.debug("No update required for %s.", metric)
            return False

        # Mise à jour de l'état
        self._available_metrics.setdefault(
            Metric.AGE, get_age(self._config[CONF_BIRTHDAY])
        )
        self._available_metrics[metric] = state

        # Gérer le statut si nécessaire
        if metric == Metric.STATUS:
            self._status = str(state) if self._status != state else self._status

        # Mettre à jour les abonnés de manière non redondante
        metric_info = self._dependencies[metric]
        subscribers = self._subscribers.get(metric, [])
        if subscribers:
            subscriber_state = _modify_state_for_subscriber(metric_info, state)
            for subscriber in subscribers:
                subscriber(subscriber_state)

        # Recalculer les métriques dépendantes
        metric_info = self._dependencies[metric]
        for depended in metric_info.depended_by:
            depended_info = self._dependencies[depended]
            if all(dep in self._available_metrics for dep in depended_info.depends_on):
                value = depended_info.calculate(self._config, self._available_metrics)
                if value is not None:
                    self._update_available_metric(depended, value)
        return True

    def _trigger_dependent_recalculation(self) -> None:
        """Trigger recalculation for metrics that depend on the updated metric."""
        updated_metrics = list(self._available_metrics.keys())
        for metric in updated_metrics:
            metric_info = self._dependencies.get(metric)
            if metric_info:
                for depended in metric_info.depended_by:
                    depended_info = self._dependencies.get(depended)
                    if depended_info and all(
                        dep in self._available_metrics
                        for dep in depended_info.depends_on
                    ):
                        value = depended_info.calculate(
                            self._config, self._available_metrics
                        )
                        if value is not None:
                            self._update_available_metric(depended, value)

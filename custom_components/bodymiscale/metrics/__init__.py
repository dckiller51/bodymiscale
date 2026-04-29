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
    CONF_IMPEDANCE_MODE,
    CONF_SCALE,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_IMPEDANCE_HIGH,
    CONF_SENSOR_IMPEDANCE_LOW,
    CONF_SENSOR_LAST_MEASUREMENT_TIME,
    CONF_SENSOR_WEIGHT,
    CONSTRAINT_IMPEDANCE_MAX,
    CONSTRAINT_IMPEDANCE_MIN,
    CONSTRAINT_WEIGHT_MAX,
    CONSTRAINT_WEIGHT_MIN,
    IMPEDANCE_MODE_DUAL,
    IMPEDANCE_MODE_STANDARD,
    PROBLEM_NONE,
    UNIT_POUNDS,
)
from ..models import Gender, Metric
from .body_score import get_body_score
from .impedance import (
    get_bcm,
    get_body_type,
    get_bone_mass,
    get_ecw,
    get_ecw_tbw_ratio,
    get_fat_mass_to_ideal_weight,
    get_fat_percentage,
    get_icw,
    get_lbm,
    get_metabolic_age,
    get_muscle_mass,
    get_protein_percentage,
    get_skeletal_muscle_mass,
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
    decimals: int | None = None
    depended_by: list[Metric] = field(default_factory=list, init=False)


# Dependency graph.
# Note: LBM and METABOLIC_AGE do not list IMPEDANCE in their dependencies because
# impedance availability verification is done in _recalculate_metric.
_METRIC_DEPS: dict[Metric, MetricInfo] = {
    Metric.STATUS: MetricInfo([], lambda c, s: None),
    Metric.AGE: MetricInfo([], lambda c, s: None, 0),
    Metric.WEIGHT: MetricInfo([], lambda c, s: None, 2),
    Metric.IMPEDANCE: MetricInfo([], lambda c, s: None, 0),
    Metric.IMPEDANCE_LOW: MetricInfo([], lambda c, s: None, 0),
    Metric.IMPEDANCE_HIGH: MetricInfo([], lambda c, s: None, 0),
    Metric.LAST_MEASUREMENT_TIME: MetricInfo([], lambda c, s: None),
    # Weight only
    Metric.BMI: MetricInfo([Metric.WEIGHT], get_bmi, 1),
    Metric.BMR: MetricInfo([Metric.AGE, Metric.WEIGHT], get_bmr, 0),
    Metric.VISCERAL_FAT: MetricInfo([Metric.AGE, Metric.WEIGHT], get_visceral_fat, 0),
    # Impedance required (verification in _recalculate_metric)
    Metric.LBM: MetricInfo([Metric.AGE, Metric.WEIGHT], get_lbm, 1),
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
    Metric.METABOLIC_AGE: MetricInfo([Metric.WEIGHT, Metric.AGE], get_metabolic_age, 0),
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
    # dual-frequency metrics
    # These require dual-frequency mode (IMPEDANCE_LOW + IMPEDANCE_HIGH)
    Metric.ECW: MetricInfo([Metric.IMPEDANCE_LOW, Metric.IMPEDANCE_HIGH], get_ecw, 2),
    # Metric.ICW, ECW_TBW_RATIO and BCM depend on WATER_PERCENTAGE (TBW)
    # to ensure they are calculated after TBW for the subtraction logic.
    Metric.ICW: MetricInfo([Metric.WATER_PERCENTAGE, Metric.ECW], get_icw, 2),
    Metric.ECW_TBW_RATIO: MetricInfo(
        [Metric.WATER_PERCENTAGE, Metric.ECW], get_ecw_tbw_ratio, 1
    ),
    Metric.BCM: MetricInfo([Metric.WATER_PERCENTAGE, Metric.ECW], get_bcm, 2),
    Metric.SKELETAL_MUSCLE_MASS: MetricInfo(
        [Metric.LBM, Metric.IMPEDANCE_LOW, Metric.IMPEDANCE_HIGH],
        get_skeletal_muscle_mass,
        2,
    ),
    # ── Body score ───────────────────────────────────────────────────────────
    Metric.BODY_SCORE: MetricInfo(
        [
            Metric.BMI,
            Metric.FAT_PERCENTAGE,
            Metric.AGE,
            Metric.MUSCLE_MASS,
            Metric.SKELETAL_MUSCLE_MASS,
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
    metric_info: MetricInfo, state: StateType | datetime
) -> StateType | datetime:
    """Round the state before sending to sensors."""
    if isinstance(state, (int, float)) and metric_info.decimals is not None:
        return round(float(state), metric_info.decimals)
    return state


class BodyScaleMetricsHandler:
    """Body scale metrics handler."""

    def __init__(
        self, hass: HomeAssistant, config: dict[str, Any], config_entry_id: str
    ):
        self._hass = hass
        self._config_entry_id = config_entry_id
        self._config: dict[str, Any] = {
            **config,
            CONF_GENDER: Gender(config[CONF_GENDER]),
        }
        self._config[CONF_SCALE] = Scale(
            self._config[CONF_HEIGHT], self._config[CONF_GENDER]
        )

        # Cache TTL 60s — avoids redundant recalculations
        self._available_metrics: MutableMapping[Metric, StateType | datetime] = (
            TTLCache(maxsize=len(Metric), ttl=60)
        )

        # Counter to track pending sensor restorations
        self._pending_restorations = 0

        # Flag to track if restoration is complete - ignore source sensor updates until set
        self._restoration_complete = False

        # Sensor problems: { "weight": "high", "impedance": "unavailable", ... }
        self._sensor_problems: dict[str, str] = {}

        self._subscribers: dict[
            Metric, list[Callable[[StateType | datetime], None]]
        ] = {}

        # Build the dependency graph
        self._dependencies: dict[Metric, MetricInfo] = {}
        for key, value in _METRIC_DEPS.items():
            self._dependencies[key] = value
            for dep in value.depends_on:
                self._dependencies[dep].depended_by.append(key)

        # Subscribe to sensors based on impedance mode
        impedance_mode = self._config.get(CONF_IMPEDANCE_MODE, "none")
        sensors = [self._config[CONF_SENSOR_WEIGHT]]

        if (
            impedance_mode == IMPEDANCE_MODE_STANDARD
            and CONF_SENSOR_IMPEDANCE in self._config
        ):
            sensors.append(self._config[CONF_SENSOR_IMPEDANCE])
        elif impedance_mode == IMPEDANCE_MODE_DUAL:
            if CONF_SENSOR_IMPEDANCE_LOW in self._config:
                sensors.append(self._config[CONF_SENSOR_IMPEDANCE_LOW])
            if CONF_SENSOR_IMPEDANCE_HIGH in self._config:
                sensors.append(self._config[CONF_SENSOR_IMPEDANCE_HIGH])

        if CONF_SENSOR_LAST_MEASUREMENT_TIME in self._config:
            sensors.append(self._config[CONF_SENSOR_LAST_MEASUREMENT_TIME])

        self._remove_listener: CALLBACK_TYPE | None = async_track_state_change_event(
            self._hass,
            sensors,
            self._state_changed_event,
        )

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def config(self) -> Mapping[str, Any]:
        """Return config."""
        return self._config

    @property
    def config_entry_id(self) -> str:
        """Return config entry id."""
        return self._config_entry_id

    @callback
    def unload(self) -> None:
        """Unload the handler and remove Home Assistant listeners."""
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None
        self._subscribers.clear()

    # ── Subscribe ────────────────────────────────────────────────────────────

    def subscribe(
        self, metric: Metric, callback_func: Callable[[StateType | datetime], None]
    ) -> CALLBACK_TYPE:
        """Subscribe for metric changes. Immediately sends current value if available."""
        self._subscribers.setdefault(metric, []).append(callback_func)

        @callback
        def _remove_listener() -> None:
            """Remove the subscription."""
            if callback_func in self._subscribers.get(metric, []):
                self._subscribers[metric].remove(callback_func)

        # Send current value immediately if already available
        current = self._available_metrics.get(metric)
        if current is not None:
            callback_func(
                _modify_state_for_subscriber(self._dependencies[metric], current)
            )

        return _remove_listener

    # ── Restoration ────────────────────────────────────────────────────────────

    def add_restoration_sensor(self, count: int = 1) -> None:
        """Add pending restorations for sensors that are being restored."""
        self._pending_restorations += count
        _LOGGER.debug(
            "Added %d restoration sensor(s), pending restorations: %d",
            count,
            self._pending_restorations,
        )

    def mark_restoration_complete(self) -> None:
        """Mark that a sensor has restored and check if all are done."""
        self._pending_restorations -= 1
        _LOGGER.debug(
            "Restoration step completed, pending restorations: %d",
            self._pending_restorations,
        )
        if self._pending_restorations <= 0:
            self._restoration_complete = True
            _LOGGER.debug("Restoration complete, enabling source sensor updates")

    def restore_metric(self, metric: Metric, state: StateType | datetime) -> None:
        """Seed a metric from a restored Home Assistant entity state."""
        restored_source_metrics = {
            Metric.WEIGHT,
            Metric.IMPEDANCE,
            Metric.IMPEDANCE_LOW,
            Metric.IMPEDANCE_HIGH,
            Metric.LAST_MEASUREMENT_TIME,
        }
        if metric not in restored_source_metrics:
            return

        if metric == Metric.LAST_MEASUREMENT_TIME:
            if isinstance(state, datetime):
                self._update_available_metric(metric, state)
            elif isinstance(state, str):
                try:
                    self._update_available_metric(metric, datetime.fromisoformat(state))
                except ValueError:
                    _LOGGER.debug("Ignoring restored %s value %s", metric, state)
            return

        if state is None or isinstance(state, datetime):
            _LOGGER.debug("Ignoring restored %s value %s", metric, state)
            return

        try:
            state = float(state)
        except (TypeError, ValueError):
            _LOGGER.debug("Ignoring restored %s value %s", metric, state)
            return

        self._update_available_metric(metric, state)

    # ── State change ─────────────────────────────────────────────────────────

    @callback
    def _state_changed_event(self, event: Event[EventStateChangedData]) -> None:
        self._state_changed(
            event.data.get("entity_id"),
            event.data.get("new_state"),
            event.data.get("old_state"),
        )

    @callback
    def _state_changed(
        self, entity_id: str | None, new_state: State | None, old_state: State | None
    ) -> None:
        if entity_id is None or new_state is None:
            _LOGGER.debug(
                "During source sensor state change, entity_id or new_state was None. Skipping processing."
            )
            return

        # Ignore source sensor updates until restoration is complete
        if not self._restoration_complete:
            _LOGGER.debug(
                "Ignoring update from %s until restoration is complete", entity_id
            )
            return

        raw = new_state.state

        # Sensor back to unknown → clear the problem without recalculating
        if raw == STATE_UNKNOWN:
            self._clear_sensor_problem(entity_id)
            _LOGGER.debug(
                "Sensor %s state is unknown, clearing problem and skipping processing",
                entity_id,
            )
            return

        valid = False
        problem: str | None = None

        if entity_id == self._config[CONF_SENSOR_WEIGHT]:
            valid, problem = self._process_weight(new_state, old_state)

        elif entity_id == self._config.get(CONF_SENSOR_IMPEDANCE):
            valid, problem = self._process_impedance(
                new_state, Metric.IMPEDANCE, old_state
            )

        elif entity_id == self._config.get(CONF_SENSOR_IMPEDANCE_LOW):
            valid, problem = self._process_impedance(
                new_state, Metric.IMPEDANCE_LOW, old_state
            )

        elif entity_id == self._config.get(CONF_SENSOR_IMPEDANCE_HIGH):
            valid, problem = self._process_impedance(
                new_state, Metric.IMPEDANCE_HIGH, old_state
            )

        elif entity_id == self._config.get(CONF_SENSOR_LAST_MEASUREMENT_TIME):
            problem = self._process_last_measurement_time(new_state)

        # Update global status
        if problem:
            self._set_sensor_problem(entity_id, problem)
        else:
            self._clear_sensor_problem(entity_id)

        if valid:
            self._trigger_dependent_recalculation()

    # ── Process helpers ───────────────────────────────────────────────────────

    def _process_weight(
        self, state: State, previous_state: State | None
    ) -> tuple[bool, str | None]:
        raw = state.state

        if raw == STATE_UNAVAILABLE:
            return False, "unavailable"

        try:
            val = float(raw)
        except ValueError:
            return False, "invalid_format"

        if val < CONSTRAINT_WEIGHT_MIN:
            return False, "low"
        if val > CONSTRAINT_WEIGHT_MAX:
            return False, "high"

        if state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UNIT_POUNDS:
            val *= 0.45359237

        previous_val = self._available_metrics.get(Metric.WEIGHT)
        decimals = self._dependencies[Metric.WEIGHT].decimals
        assert decimals is not None
        previous_val_changed = not isinstance(previous_val, (int, float)) or round(
            float(previous_val), decimals
        ) != round(val, decimals)
        self._update_available_metric(Metric.WEIGHT, val)

        # Fallback timestamp if no dedicated sensor
        if (
            CONF_SENSOR_LAST_MEASUREMENT_TIME not in self._config
            or self._available_metrics.get(Metric.LAST_MEASUREMENT_TIME) is None
        ):
            # Only update if this is a fresh measurement (not a restoration)
            # A fresh measurement is when the previous state was not unknown/unavailable
            # or the value changed compared to the previously (re)stored value
            # (during restart or first measurement)
            if (
                previous_state
                and previous_state.state
                not in (
                    STATE_UNKNOWN,
                    STATE_UNAVAILABLE,
                    None,
                )
                or previous_val_changed
            ):
                self._update_available_metric(
                    Metric.LAST_MEASUREMENT_TIME, state.last_changed
                )
                _LOGGER.debug(
                    "LAST_MEASUREMENT_TIME updated because previous_state was %s, previous_val was %s and val is %s",
                    previous_state.state if previous_state else None,
                    previous_val,
                    val,
                )
            else:
                _LOGGER.debug(
                    "LAST_MEASUREMENT_TIME previous state is unknown and %s is equal to %s, ignoring as assuming from restart",
                    previous_val,
                    val,
                )

        return True, None

    def _process_impedance(
        self, state: State, metric: Metric, previous_state: State | None
    ) -> tuple[bool, str | None]:
        raw = state.state

        if raw == STATE_UNAVAILABLE:
            return False, "unavailable"

        try:
            val = float(raw)
        except ValueError:
            return False, "invalid_format"

        if val < CONSTRAINT_IMPEDANCE_MIN:
            return False, "low"
        if val > CONSTRAINT_IMPEDANCE_MAX:
            return False, "high"

        previous_val = self._available_metrics.get(metric)
        decimals = self._dependencies[metric].decimals
        assert decimals is not None
        previous_val_changed = not isinstance(previous_val, (int, float)) or round(
            float(previous_val), decimals
        ) != round(val, decimals)
        self._update_available_metric(metric, val)

        # Fallback timestamp if no dedicated sensor
        if (
            CONF_SENSOR_LAST_MEASUREMENT_TIME not in self._config
            or self._available_metrics.get(Metric.LAST_MEASUREMENT_TIME) is None
        ):
            # Only update if this is a fresh measurement (not a restoration)
            # A fresh measurement is when the previous state was not unknown/unavailable
            # or the value changed compared to the previously (re)stored value
            # (during restart or first measurement)
            if (
                previous_state
                and previous_state.state
                not in (
                    STATE_UNKNOWN,
                    STATE_UNAVAILABLE,
                    None,
                )
                or previous_val_changed
            ):
                self._update_available_metric(
                    Metric.LAST_MEASUREMENT_TIME, state.last_changed
                )
                _LOGGER.debug(
                    "LAST_MEASUREMENT_TIME updated because previous_state was %s, previous_val was %s and val is %s",
                    previous_state.state if previous_state else None,
                    previous_val,
                    val,
                )
            else:
                _LOGGER.debug(
                    "LAST_MEASUREMENT_TIME previous state is unknown and %s is equal to %s, ignoring as assuming from restart",
                    previous_val,
                    val,
                )

        return True, None

    def _process_last_measurement_time(self, state: State) -> str | None:
        raw = state.state

        if raw in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return "unavailable"

        try:
            dt = datetime.fromisoformat(raw)
            tz = get_time_zone(self._hass.config.time_zone)
            dt = dt.replace(tzinfo=tz) if dt.tzinfo is None else dt.astimezone(tz)
            self._update_available_metric(Metric.LAST_MEASUREMENT_TIME, dt)
            self._trigger_dependent_recalculation()  # Seems not needed here because no metric depends on LAST_MEASUREMENT_TIME, but just in case?
            return None
        except (ValueError, TypeError) as e:
            _LOGGER.error("Invalid date format for last measurement: %s (%s)", raw, e)
            return "invalid_format"

    # ── Problem management ────────────────────────────────────────────────────

    def _entity_to_label(self, entity_id: str) -> str | None:
        """Map entity_id to a short problem label."""
        if entity_id == self._config[CONF_SENSOR_WEIGHT]:
            return "weight"
        if entity_id == self._config.get(CONF_SENSOR_IMPEDANCE):
            return "impedance"
        if entity_id == self._config.get(CONF_SENSOR_IMPEDANCE_LOW):
            return "impedance_low"
        if entity_id == self._config.get(CONF_SENSOR_IMPEDANCE_HIGH):
            return "impedance_high"
        if entity_id == self._config.get(CONF_SENSOR_LAST_MEASUREMENT_TIME):
            return "last_time"
        return None

    def _set_sensor_problem(self, entity_id: str, error: str) -> None:
        """Record a problem for a sensor and update STATUS metric."""
        label = self._entity_to_label(entity_id)
        if label is None:
            return
        self._sensor_problems[label] = error
        self._publish_status()

    def _clear_sensor_problem(self, entity_id: str) -> None:
        """Remove any recorded problem for a sensor and update STATUS metric."""
        label = self._entity_to_label(entity_id)
        if label is None:
            return
        self._sensor_problems.pop(label, None)
        self._publish_status()

    def _publish_status(self) -> None:
        """Build the status string from current problems and publish it."""
        if not self._sensor_problems:
            status = PROBLEM_NONE
        else:
            # Deterministic order: weight → impedance → last_time → others
            order = [
                "weight",
                "impedance",
                "impedance_low",
                "impedance_high",
                "last_time",
            ]
            parts = []
            for key in order:
                if key in self._sensor_problems:
                    parts.append(f"{key}_{self._sensor_problems[key]}")
            # Unexpected keys
            for key, val in self._sensor_problems.items():
                if key not in order:
                    parts.append(f"{key}_{val}")
            status = "_and_".join(parts)

        self._update_available_metric(Metric.STATUS, status)

    # ── Recalculation ─────────────────────────────────────────────────────────

    def _has_impedance(self) -> bool:
        """Return True if a valid impedance reading is available for the current mode."""
        mode = self._config.get(CONF_IMPEDANCE_MODE, "none")
        if mode == IMPEDANCE_MODE_STANDARD:
            return Metric.IMPEDANCE in self._available_metrics
        if mode == IMPEDANCE_MODE_DUAL:
            # Both frequencies must be available
            return (
                Metric.IMPEDANCE_LOW in self._available_metrics
                and Metric.IMPEDANCE_HIGH in self._available_metrics
            )
        return False

    def _recalculate_metric(self, metric: Metric) -> None:
        """Recalculate a single metric if its dependencies are met."""
        info = self._dependencies.get(metric)
        if info is None:
            return

        # LBM and METABOLIC_AGE require available impedance
        if metric in (Metric.LBM, Metric.METABOLIC_AGE):
            if not self._has_impedance():
                return
            if Metric.WEIGHT not in self._available_metrics:
                return
            # Check other dependencies (AGE)
            other_deps = [d for d in info.depends_on if d not in (Metric.IMPEDANCE,)]
            if not all(d in self._available_metrics for d in other_deps):
                return
        else:
            if not all(d in self._available_metrics for d in info.depends_on):
                return

        val = info.calculate(self._config, self._available_metrics)
        if val is not None:
            self._update_available_metric(metric, val)

    def _trigger_dependent_recalculation(self) -> None:
        """Recalculate all metrics whose dependencies are now met."""
        for metric in list(self._available_metrics.keys()):
            info = self._dependencies.get(metric)
            if info:
                for dep in info.depended_by:
                    self._recalculate_metric(dep)

    def _update_available_metric(
        self, metric: Metric, state: StateType | datetime
    ) -> None:
        """Update a metric value, notify subscribers, cascade recalculations."""
        old = self._available_metrics.get(metric)
        if old is not None and old == state:
            _LOGGER.debug("No update required for %s.", metric)
            return

        # Inject age on first call
        self._available_metrics.setdefault(
            Metric.AGE, get_age(self._config[CONF_BIRTHDAY])
        )
        self._available_metrics[metric] = state

        # Notify subscribers
        info = self._dependencies.get(metric)
        if info:
            subscribers = self._subscribers.get(metric, [])
            if subscribers:
                sub_state = _modify_state_for_subscriber(info, state)
                for sub in subscribers:
                    sub(sub_state)

            # Trigger recalculation of dependent metrics
            for dep in info.depended_by:
                self._recalculate_metric(dep)

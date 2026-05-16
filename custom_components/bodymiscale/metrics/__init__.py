"""Metrics handler for bodymiscale."""

import logging
import time
from collections.abc import Callable, Iterator, Mapping, MutableMapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

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
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt as dt_util

from ..const import (
    CONF_BIRTHDAY,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_IMPEDANCE_MODE,
    CONF_INITIAL_WEIGHT,
    CONF_PROFILE_METHOD,
    CONF_SCALE,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_IMPEDANCE_HIGH,
    CONF_SENSOR_IMPEDANCE_LOW,
    CONF_SENSOR_WEIGHT,
    CONSTRAINT_IMPEDANCE_MAX,
    CONSTRAINT_IMPEDANCE_MIN,
    CONSTRAINT_WEIGHT_MAX,
    CONSTRAINT_WEIGHT_MIN,
    IMPEDANCE_MODE_DUAL,
    IMPEDANCE_MODE_STANDARD,
    PENDING_MEASUREMENT_TIMEOUT,
    PROBLEM_NONE,
    PROFILE_METHOD_NEAREST,
    RECALCULATION_DEBOUNCE,
    UNIT_POUNDS,
)
from ..models import Gender, Metric
from ..profile import (
    NotificationCoordinator,
    NotificationFilter,
    ProfileFilter,
    build_profile_filter,
)
from ..util import get_age
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
from .scale import Scale
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


# Raw sensor readings — stored without TTL so they remain available until the
# next valid measurement. This is required by the notification flow: the user
# may confirm their identity several minutes after the scale fires, and both
# weight and impedance must still be present for BIA metrics to be calculated.
_SOURCE_METRICS: frozenset[Metric] = frozenset(
    {
        Metric.AGE,
        Metric.STATUS,
        Metric.WEIGHT,
        Metric.IMPEDANCE,
        Metric.IMPEDANCE_LOW,
        Metric.IMPEDANCE_HIGH,
        Metric.LAST_MEASUREMENT_TIME,
    }
)


class _MetricsStore(MutableMapping):
    """Unified metric store with two retention policies.

    Source metrics (weight, impedance, age, timestamp, status) are kept
    indefinitely — they are only replaced by a newer valid reading.

    Derived metrics (BMI, fat%, muscle mass, score…) expire after ``ttl``
    seconds so that stale calculated values are not served if the sensors
    go silent.
    """

    def __init__(self, ttl: float) -> None:
        self._ttl = ttl
        self._sources: dict[Metric, StateType | datetime] = {}
        # Derived metrics stored as (value, monotonic insertion timestamp).
        self._derived: dict[Metric, tuple[StateType | datetime, float]] = {}

    # ── MutableMapping interface ──────────────────────────────────────────

    def __setitem__(self, key: Metric, value: StateType | datetime) -> None:
        if key in _SOURCE_METRICS:
            self._sources[key] = value
        else:
            self._derived[key] = (value, time.monotonic())

    def __getitem__(self, key: Metric) -> StateType | datetime:
        if key in _SOURCE_METRICS:
            return self._sources[key]
        entry = self._derived.get(key)
        if entry is None:
            raise KeyError(key)
        value, ts = entry
        if time.monotonic() - ts > self._ttl:
            del self._derived[key]
            raise KeyError(key)
        return value

    def __delitem__(self, key: Metric) -> None:
        if key in _SOURCE_METRICS:
            del self._sources[key]
        else:
            del self._derived[key]

    def __iter__(self) -> Iterator[Metric]:
        self._evict_expired()
        return iter(set(self._sources) | set(self._derived))

    def __len__(self) -> int:
        self._evict_expired()
        return len(self._sources) + len(self._derived)

    def __contains__(self, key: object) -> bool:
        if key in _SOURCE_METRICS:
            return key in self._sources
        if not isinstance(key, Metric):
            return False
        entry = self._derived.get(key)
        if entry is None:
            return False
        _, ts = entry
        if time.monotonic() - ts > self._ttl:
            del self._derived[key]
            return False
        return True

    # ── Helpers ──────────────────────────────────────────────────────────

    def _evict_expired(self) -> None:
        """Remove expired derived entries (called on iteration)."""
        now = time.monotonic()
        expired = [k for k, (_, ts) in self._derived.items() if now - ts > self._ttl]
        for k in expired:
            del self._derived[k]


class BodyScaleMetricsHandler:
    """Handles metric propagation for a single body scale profile."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: dict[str, Any],
        config_entry_id: str,
    ) -> None:
        self._hass = hass
        self._config_entry_id = config_entry_id
        self._config: dict[str, Any] = {
            **config,
            CONF_GENDER: Gender(config[CONF_GENDER]),
        }
        self._config[CONF_SCALE] = Scale(
            self._config[CONF_HEIGHT], self._config[CONF_GENDER]
        )

        self._profile_filter: ProfileFilter = build_profile_filter(self._config)
        self._notification_coordinator: NotificationCoordinator | None = None

        self._pending_weight: float | None = None
        self._pending_state: State | None = None
        self._pending_impedance: dict[Metric, tuple[float, State]] = {}
        self._replaying: bool = False
        self._pending_timeout_cancel: CALLBACK_TYPE | None = None
        self._debounce_cancel: CALLBACK_TYPE | None = None
        self._settling: bool = False

        # _last_accepted_weight tracks the weight accepted in the current
        # measurement cycle. Used to validate impedance for weight-based
        # filters without relying on the stored metric (which could be from
        # a previous session and belong to a different user).
        self._last_accepted_weight: float | None = None

        self._available_metrics: MutableMapping[Metric, StateType | datetime] = (
            _MetricsStore(ttl=60)
        )

        # Sensor problems: { "weight": "high", "impedance": "unavailable", ... }
        self._sensor_problems: dict[str, str] = {}

        self._subscribers: dict[
            Metric, list[Callable[[StateType | datetime], None]]
        ] = {}

        # Build the dependency graph
        self._dependencies: dict[Metric, MetricInfo] = {
            key: MetricInfo(
                depends_on=list(value.depends_on),
                calculate=value.calculate,
                decimals=value.decimals,
            )
            for key, value in _METRIC_DEPS.items()
        }
        for key, value in self._dependencies.items():
            for dep in value.depends_on:
                self._dependencies[dep].depended_by.append(key)

        if self._config.get(CONF_PROFILE_METHOD) == PROFILE_METHOD_NEAREST:
            initial_weight = self._config.get(CONF_INITIAL_WEIGHT)
            if initial_weight is not None:
                bootstrap_weight = float(initial_weight)
                self._last_accepted_weight = bootstrap_weight
                self._update_available_metric(Metric.WEIGHT, bootstrap_weight)

        sensors = [self._config[CONF_SENSOR_WEIGHT]]

        # Subscribe to sensors based on impedance mode
        impedance_mode = self._config.get(CONF_IMPEDANCE_MODE, "none")
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

        self._remove_listener: CALLBACK_TYPE | None = async_track_state_change_event(
            self._hass,
            sensors,
            self._state_changed_event,
        )
        for sensor_id in sensors:
            state = self._hass.states.get(sensor_id)
            if state is not None:
                self._state_changed(sensor_id, state)

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def config(self) -> Mapping[str, Any]:
        """Return config."""
        return self._config

    @property
    def config_entry_id(self) -> str:
        """Return config entry id."""
        return self._config_entry_id

    @property
    def profile_filter(self) -> ProfileFilter:
        """Return the profile filter instance."""
        return self._profile_filter

    @property
    def current_weight(self) -> float | None:
        """Return the latest known weight for this profile."""
        current = self._available_metrics.get(Metric.WEIGHT)
        if not isinstance(current, (int, float)):
            return None
        return float(current)

    def set_notification_coordinator(
        self, coordinator: NotificationCoordinator
    ) -> None:
        """Inject the notification coordinator."""
        self._notification_coordinator = coordinator

    # ── Pending measurement ───────────────────────────────────────────────────

    def _cancel_pending_timeout(self) -> None:
        """Cancel the pending measurement expiry timer if armed."""
        if self._pending_timeout_cancel is not None:
            self._pending_timeout_cancel()
            self._pending_timeout_cancel = None

    @callback
    def _expire_pending_measurement(self, _now: datetime) -> None:
        """Discard the pending measurement after PENDING_MEASUREMENT_TIMEOUT seconds."""
        self._pending_timeout_cancel = None

        if self._pending_weight is None:
            return

        _LOGGER.warning(
            "Pending measurement %.2f kg expired after %ds without confirmation — discarded.",
            self._pending_weight,
            PENDING_MEASUREMENT_TIMEOUT,
        )
        self._pending_weight = None
        self._pending_state = None
        self._pending_impedance.clear()
        self._last_accepted_weight = None

    @callback
    def accept_pending_measurement(self) -> None:
        """Replay the pending measurement after the user confirms via notification."""
        if self._pending_weight is None or self._pending_state is None:
            _LOGGER.debug(
                "accept_pending_measurement: no pending measurement to replay"
            )
            return

        self._cancel_pending_timeout()

        _LOGGER.debug(
            "accept_pending_measurement: replaying %.2f kg after confirmation",
            self._pending_weight,
        )
        pending_state = self._pending_state
        self._pending_weight = None
        self._pending_state = None

        self._replaying = True
        try:
            valid, problem = self._process_weight(pending_state)
        finally:
            self._replaying = False

        if problem:
            self._set_sensor_problem(self._config[CONF_SENSOR_WEIGHT], problem)
        if valid:
            if self._pending_impedance:
                for metric, (val, _state) in self._pending_impedance.items():
                    _LOGGER.debug(
                        "accept_pending_measurement: replaying impedance %s=%.2f",
                        metric,
                        val,
                    )
                    self._update_available_metric(metric, val)
                self._pending_impedance.clear()
            self._schedule_recalculation()

    # ── Lifecycle ────────────────────────────────────────────────────────────

    @callback
    def unload(self) -> None:
        """Unload the handler."""
        if self._debounce_cancel is not None:
            self._debounce_cancel()
            self._debounce_cancel = None
        self._cancel_pending_timeout()

        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None
        self._subscribers.clear()

    # ── Subscribe ─────────────────────────────────────────────────────────────

    def subscribe(
        self, metric: Metric, callback_func: Callable[[StateType | datetime], None]
    ) -> CALLBACK_TYPE:
        """Subscribe for metric changes."""
        self._subscribers.setdefault(metric, []).append(callback_func)

        @callback
        def _remove_subscription() -> None:
            """Remove the subscription."""
            if callback_func in self._subscribers.get(metric, []):
                self._subscribers[metric].remove(callback_func)

        current = self._available_metrics.get(metric)
        if current is not None:
            callback_func(
                _modify_state_for_subscriber(self._dependencies[metric], current)
            )

        return _remove_subscription

    # ── Restoration ───────────────────────────────────────────────────────────

    def restore_metric(self, metric: Metric, state: StateType | datetime) -> None:
        """Seed a metric from a value restored by RestoreSensor / RestoreEntity."""
        restorable_metrics: frozenset[Metric] = frozenset(
            {
                Metric.WEIGHT,
                Metric.IMPEDANCE,
                Metric.IMPEDANCE_LOW,
                Metric.IMPEDANCE_HIGH,
                Metric.LAST_MEASUREMENT_TIME,
            }
        )

        if metric not in restorable_metrics:
            return

        if metric is Metric.LAST_MEASUREMENT_TIME:
            if isinstance(state, datetime):
                self._update_available_metric(metric, state)
            elif isinstance(state, str):
                try:
                    self._update_available_metric(metric, datetime.fromisoformat(state))
                except ValueError:
                    _LOGGER.debug(
                        "restore_metric: cannot parse datetime '%s' for %s",
                        state,
                        metric,
                    )
            return

        if state is None or isinstance(state, datetime):
            _LOGGER.debug(
                "restore_metric: unexpected type %s for %s — skipped",
                type(state),
                metric,
            )
            return

        try:
            val = float(state)
        except TypeError, ValueError:
            _LOGGER.debug(
                "restore_metric: cannot coerce '%s' to float for %s — skipped",
                state,
                metric,
            )
            return

        # Restore _last_accepted_weight so impedance validation works after restart
        if metric is Metric.WEIGHT:
            self._last_accepted_weight = val

        self._update_available_metric(metric, val)

    # ── State change ──────────────────────────────────────────────────────────

    @callback
    def _state_changed_event(self, event: Event[EventStateChangedData]) -> None:
        self._state_changed(
            event.data.get("entity_id"),
            event.data.get("new_state"),
        )

    @callback
    def _state_changed(self, entity_id: str | None, new_state: State | None) -> None:
        if entity_id is None or new_state is None:
            return

        raw = new_state.state

        # Sensor back to unknown → clear the problem without recalculating
        if raw == STATE_UNKNOWN:
            self._clear_sensor_problem(entity_id)
            return

        valid = False
        problem: str | None = None

        if entity_id == self._config[CONF_SENSOR_WEIGHT]:
            valid, problem = self._process_weight(new_state)

        elif entity_id == self._config.get(CONF_SENSOR_IMPEDANCE):
            valid, problem = self._process_impedance(new_state, Metric.IMPEDANCE)

        elif entity_id == self._config.get(CONF_SENSOR_IMPEDANCE_LOW):
            valid, problem = self._process_impedance(new_state, Metric.IMPEDANCE_LOW)

        elif entity_id == self._config.get(CONF_SENSOR_IMPEDANCE_HIGH):
            valid, problem = self._process_impedance(new_state, Metric.IMPEDANCE_HIGH)

        # Update global status
        if problem:
            self._set_sensor_problem(entity_id, problem)
        else:
            self._clear_sensor_problem(entity_id)

        if valid:
            self._schedule_recalculation()

    # ── Process helpers ─────────────────────────────────────────────────────

    def _process_weight(self, state: State) -> tuple[bool, str | None]:
        raw = state.state

        if raw == STATE_UNAVAILABLE:
            _LOGGER.debug("Weight sensor unavailable — ignoring (scale disconnected)")
            return False, None

        try:
            val = float(raw)
        except ValueError:
            return False, "invalid_format"

        if val < CONSTRAINT_WEIGHT_MIN:
            # Scale reset to zero — clear last accepted weight for this cycle
            self._last_accepted_weight = None
            _LOGGER.debug("Weight %.2f kg below minimum — ignoring (scale reset)", val)
            return False, None
        if val > CONSTRAINT_WEIGHT_MAX:
            return False, "high"

        if state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UNIT_POUNDS:
            val *= 0.45359237

        # ── Mode notification ─────────────────────────────────────────────────
        if self._notification_coordinator is not None and not self._replaying:
            self._cancel_pending_timeout()
            self._pending_weight = val
            self._pending_state = state
            self._pending_impedance.clear()
            self._last_accepted_weight = None

            self._pending_timeout_cancel = async_call_later(
                self._hass,
                PENDING_MEASUREMENT_TIMEOUT,
                self._expire_pending_measurement,
            )
            self._hass.async_create_task(
                self._notification_coordinator.async_notify(val)
            )
            return False, None

        if not self._profile_filter.accepts(self._hass, self._config, val):
            _LOGGER.debug("Profile filter rejected measurement: %.2f kg", val)
            return False, None

        # Weight accepted for this cycle — store for impedance validation
        self._last_accepted_weight = val
        self._update_available_metric(Metric.WEIGHT, val)

        return True, None

    def _process_impedance(
        self, state: State, metric: Metric
    ) -> tuple[bool, str | None]:
        raw = state.state

        if raw == STATE_UNAVAILABLE:
            _LOGGER.debug(
                "Impedance sensor unavailable — ignoring (scale disconnected)"
            )
            return False, None

        try:
            val = float(raw)
        except ValueError:
            return False, "invalid_format"

        if val < CONSTRAINT_IMPEDANCE_MIN:
            _LOGGER.debug("Impedance %.2f below minimum — ignoring (scale reset)", val)
            return False, None
        if val > CONSTRAINT_IMPEDANCE_MAX:
            return False, "high"

        # ── Profile filter for impedance ──────────────────────────────────────
        if isinstance(self._profile_filter, NotificationFilter):
            if not self._profile_filter.is_confirmed():
                _LOGGER.debug(
                    "Notification filter: impedance %.2f stored as pending", val
                )
                self._pending_impedance[metric] = (val, state)
                return False, None
        else:
            # Use the weight accepted in the current measurement cycle.
            # This prevents a user whose weight was rejected from inheriting
            # the impedance of another user whose weight was accepted.
            if self._last_accepted_weight is None:
                _LOGGER.debug(
                    "Profile filter: no weight accepted in current cycle "
                    "— impedance rejected"
                )
                return False, None
            if not self._profile_filter.accepts(
                self._hass, self._config, self._last_accepted_weight
            ):
                _LOGGER.debug("Profile filter rejected impedance: %.2f", val)
                return False, None

        self._update_available_metric(metric, val)

        return True, None

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
            # Deterministic order: weight → impedance → others
            order = [
                "weight",
                "impedance",
                "impedance_low",
                "impedance_high",
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

    # ── Recalculation ───────────────────────────────────────────────────────

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
        if self._settling:
            return
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
            other_deps = [d for d in info.depends_on if d is not Metric.IMPEDANCE]
            if not all(d in self._available_metrics for d in other_deps):
                return
        else:
            if not all(d in self._available_metrics for d in info.depends_on):
                return

        val = info.calculate(self._config, self._available_metrics)
        if val is not None:
            self._update_available_metric(metric, val)

    def _schedule_recalculation(self) -> None:
        """Debounce recalculation — wait for all sensors to settle.

        Resets the timer on every valid sensor update so the full
        recalculation only fires once all sensors (weight, impedance_low,
        impedance_high) have reported their values for this measurement cycle.
        """
        if self._debounce_cancel is not None:
            self._debounce_cancel()
            self._debounce_cancel = None

        self._settling = True

        self._debounce_cancel = async_call_later(
            self._hass,
            RECALCULATION_DEBOUNCE,
            self._on_debounce_elapsed,
        )

    @callback
    def _on_debounce_elapsed(self, _now: Any) -> None:
        """Fire after the debounce window — all sensors should have settled."""
        self._debounce_cancel = None
        self._settling = False
        self._update_available_metric(Metric.LAST_MEASUREMENT_TIME, dt_util.utcnow())
        self._trigger_dependent_recalculation()

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

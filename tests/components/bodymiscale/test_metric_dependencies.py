"""Every metric must declare the metrics its formula reads (#428, #449).

A formula that reads a metric without declaring it as a dependency can run
before that metric is computed. The missing value then silently becomes 0
(e.g. ECW computed as if body fat were 0 %, about 40 % too high). This test
records what each formula actually reads, for every configuration, and
checks it against the declared dependency graph.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from itertools import product
from typing import Any

import pytest
from homeassistant.core import HomeAssistant

from custom_components.bodymiscale.const import (
    ALGO_SCIENCE,
    ALGO_XIAOMI,
    ALGO_XIAOMI_HOME,
    CONF_BIRTHDAY,
    CONF_CALCULATION_MODE,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_IMPEDANCE_MODE,
    CONF_PROFILE_METHOD,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_IMPEDANCE_HIGH,
    CONF_SENSOR_IMPEDANCE_LOW,
    CONF_SENSOR_WEIGHT,
    IMPEDANCE_MODE_DUAL,
    IMPEDANCE_MODE_NONE,
    IMPEDANCE_MODE_STANDARD,
    PROFILE_METHOD_NONE,
)
from custom_components.bodymiscale.metrics import (
    _SOURCE_METRICS,
    BodyScaleMetricsHandler,
)
from custom_components.bodymiscale.models import Gender, Metric

# Impedance is checked by the handler itself before computing LBM and
# metabolic age (_can_compute), so those two may read it without declaring it.
_IMPEDANCE = {Metric.IMPEDANCE, Metric.IMPEDANCE_LOW, Metric.IMPEDANCE_HIGH}
_IMPLICIT_IMPEDANCE_READERS = {Metric.LBM, Metric.METABOLIC_AGE}

# Plausible values so every formula reaches the branches that read inputs.
_VALUES: dict[Metric, Any] = {
    Metric.WEIGHT: 79.4,
    Metric.AGE: 46,
    Metric.IMPEDANCE: 500.0,
    Metric.IMPEDANCE_LOW: 559.0,
    Metric.IMPEDANCE_HIGH: 501.0,
    Metric.BMI: 25.6,
    Metric.BMR: 1650.0,
    Metric.VISCERAL_FAT: 10.0,
    Metric.LBM: 60.2,
    Metric.FAT_PERCENTAGE: 24.2,
    Metric.WATER_PERCENTAGE: 52.3,
    Metric.BONE_MASS: 3.2,
    Metric.MUSCLE_MASS: 57.1,
    Metric.METABOLIC_AGE: 44,
    Metric.PROTEIN_PERCENTAGE: 18.9,
    Metric.ECW: 17.0,
    Metric.ICW: 26.0,
    Metric.ECW_TBW_RATIO: 39.0,
    Metric.BCM: 36.0,
    Metric.SKELETAL_MUSCLE_MASS: 30.0,
}


class _RecordingMetrics(Mapping):
    """Metrics mapping that records every key a formula reads."""

    def __init__(self, values: Mapping[Metric, Any]) -> None:
        self._values = dict(values)
        self.read: set[Metric] = set()

    def __getitem__(self, key: Metric) -> Any:
        self.read.add(key)
        return self._values[key]

    def get(self, key: Metric, default: Any = None) -> Any:
        self.read.add(key)
        return self._values.get(key, default)

    def __contains__(self, key: object) -> bool:
        if isinstance(key, Metric):
            self.read.add(key)
        return key in self._values

    def __iter__(self) -> Iterator[Metric]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)


_CONFIGS = [
    (impedance_mode, calculation_mode, gender)
    for impedance_mode, calculation_mode, gender in product(
        (IMPEDANCE_MODE_NONE, IMPEDANCE_MODE_STANDARD, IMPEDANCE_MODE_DUAL),
        (ALGO_XIAOMI, ALGO_SCIENCE, ALGO_XIAOMI_HOME),
        (Gender.MALE, Gender.FEMALE),
    )
    # Combinations the configuration flow accepts
    if (calculation_mode == ALGO_XIAOMI_HOME) == (impedance_mode == IMPEDANCE_MODE_DUAL)
    or calculation_mode == ALGO_SCIENCE
]


@pytest.mark.parametrize(
    ("impedance_mode", "calculation_mode", "gender"),
    _CONFIGS,
    ids=[f"{i}-{c}-{g.value}" for i, c, g in _CONFIGS],
)
async def test_formulas_only_read_declared_dependencies(
    hass: HomeAssistant, impedance_mode: str, calculation_mode: str, gender: Gender
) -> None:
    """No formula may read a metric that is not one of its dependencies."""
    config = {
        "name": "Deps",
        CONF_BIRTHDAY: "1980-01-01",
        CONF_GENDER: gender,
        CONF_HEIGHT: 176.0,
        CONF_CALCULATION_MODE: calculation_mode,
        CONF_IMPEDANCE_MODE: impedance_mode,
        CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
        CONF_SENSOR_WEIGHT: "sensor.deps_weight",
        CONF_SENSOR_IMPEDANCE: "sensor.deps_imp",
        CONF_SENSOR_IMPEDANCE_LOW: "sensor.deps_imp_low",
        CONF_SENSOR_IMPEDANCE_HIGH: "sensor.deps_imp_high",
    }
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="deps")
    try:
        deps = handler._dependencies

        def upstream(metric: Metric, seen: set[Metric] | None = None) -> set[Metric]:
            """Return declared dependencies, direct and indirect (all computed first)."""
            seen = set() if seen is None else seen
            direct = set(deps[metric].depends_on)
            if metric in _IMPLICIT_IMPEDANCE_READERS:
                direct |= _IMPEDANCE
            for dep in direct - seen:
                seen.add(dep)
                upstream(dep, seen)
            return seen

        undeclared: dict[str, set[str]] = {}
        for metric, info in deps.items():
            if metric in _SOURCE_METRICS:
                continue
            metrics = _RecordingMetrics(_VALUES)
            info.calculate(handler.config, metrics)
            read = metrics.read - {metric} - upstream(metric)
            if read:
                undeclared[metric.name] = {m.name for m in read}
        assert not undeclared, f"Formulas read undeclared metrics: {undeclared}"
    finally:
        handler.unload()

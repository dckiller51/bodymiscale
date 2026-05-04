"""Sensor module."""

import logging
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any, cast

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfMass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    ATTR_BCM,
    ATTR_BMI,
    ATTR_BMILABEL,
    ATTR_BMR,
    ATTR_BODY_SCORE,
    ATTR_BONES,
    ATTR_ECW_TBW_RATIO,
    ATTR_EXTRACELLULAR_WATER,
    ATTR_FAT,
    ATTR_IDEAL,
    ATTR_INTRACELLULAR_WATER,
    ATTR_LAST_MEASUREMENT_TIME,
    ATTR_LBM,
    ATTR_METABOLIC,
    ATTR_MUSCLE,
    ATTR_PROTEIN,
    ATTR_SKELETAL_MUSCLE_MASS,
    ATTR_VISCERAL,
    ATTR_WATER,
    CONF_IMPEDANCE_MODE,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_IMPEDANCE_HIGH,
    CONF_SENSOR_IMPEDANCE_LOW,
    CONF_SENSOR_WEIGHT,
    DOMAIN,
    HANDLERS,
    IMPEDANCE_MODE_DUAL,
)
from .entity import BodyScaleBaseEntity
from .metrics import BodyScaleMetricsHandler
from .models import Metric
from .util import get_bmi_label, get_ideal_weight

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sensor definitions — immutable tuples for base and conditional groups
# ---------------------------------------------------------------------------

_BASE_SENSORS: tuple[
    tuple[SensorEntityDescription, Metric, Callable | None],
    ...,
] = (
    (
        SensorEntityDescription(
            key=ATTR_BMI,
            translation_key="bmi",
            icon="mdi:human",
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=1,
        ),
        Metric.BMI,
        lambda state, _: {
            ATTR_BMILABEL: (
                get_bmi_label(float(state)) if isinstance(state, (int, float)) else None
            )
        },
    ),
    (
        SensorEntityDescription(
            key=ATTR_BMR,
            translation_key="basal_metabolism",
            suggested_display_precision=0,
            native_unit_of_measurement="kcal",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        Metric.BMR,
        None,
    ),
    (
        SensorEntityDescription(
            key=ATTR_VISCERAL,
            translation_key="visceral_fat",
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        Metric.VISCERAL_FAT,
        None,
    ),
    (
        SensorEntityDescription(
            key=CONF_SENSOR_WEIGHT,
            translation_key="weight",
            native_unit_of_measurement=UnitOfMass.KILOGRAMS,
            device_class=SensorDeviceClass.WEIGHT,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=2,
        ),
        Metric.WEIGHT,
        lambda _, config: {ATTR_IDEAL: get_ideal_weight(config)},
    ),
    (
        SensorEntityDescription(
            key=ATTR_LAST_MEASUREMENT_TIME,
            translation_key="last_measurement_time",
            device_class=SensorDeviceClass.TIMESTAMP,
        ),
        Metric.LAST_MEASUREMENT_TIME,
        None,
    ),
)

_IMPEDANCE_SENSORS: tuple[
    tuple[SensorEntityDescription, Metric, Callable | None],
    ...,
] = (
    (
        SensorEntityDescription(
            key=ATTR_LBM,
            translation_key="lean_body_mass",
            native_unit_of_measurement=UnitOfMass.KILOGRAMS,
            device_class=SensorDeviceClass.WEIGHT,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=1,
        ),
        Metric.LBM,
        None,
    ),
    (
        SensorEntityDescription(
            key=ATTR_FAT,
            translation_key="body_fat",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=1,
        ),
        Metric.FAT_PERCENTAGE,
        None,
    ),
    (
        SensorEntityDescription(
            key=ATTR_PROTEIN,
            translation_key="protein",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=1,
        ),
        Metric.PROTEIN_PERCENTAGE,
        None,
    ),
    (
        SensorEntityDescription(
            key=ATTR_WATER,
            translation_key="water",
            icon="mdi:water-percent",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=1,
        ),
        Metric.WATER_PERCENTAGE,
        None,
    ),
    (
        SensorEntityDescription(
            key=ATTR_BONES,
            translation_key="bone_mass",
            native_unit_of_measurement=UnitOfMass.KILOGRAMS,
            device_class=SensorDeviceClass.WEIGHT,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=2,
        ),
        Metric.BONE_MASS,
        None,
    ),
    (
        SensorEntityDescription(
            key=ATTR_MUSCLE,
            translation_key="muscle_mass",
            native_unit_of_measurement=UnitOfMass.KILOGRAMS,
            device_class=SensorDeviceClass.WEIGHT,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=2,
        ),
        Metric.MUSCLE_MASS,
        None,
    ),
    (
        SensorEntityDescription(
            key=ATTR_METABOLIC,
            translation_key="metabolic_age",
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        Metric.METABOLIC_AGE,
        None,
    ),
    (
        SensorEntityDescription(
            key=ATTR_BODY_SCORE,
            translation_key="body_score",
            suggested_display_precision=0,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        Metric.BODY_SCORE,
        None,
    ),
    (
        SensorEntityDescription(
            key=CONF_SENSOR_IMPEDANCE,
            translation_key="impedance",
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=0,
            icon="mdi:omega",
        ),
        Metric.IMPEDANCE,
        None,
    ),
)

_DUAL_SENSORS: tuple[
    tuple[SensorEntityDescription, Metric, Callable | None],
    ...,
] = (
    (
        SensorEntityDescription(
            key=ATTR_EXTRACELLULAR_WATER,
            translation_key="extracellular_water",
            icon="mdi:water-opacity",
            native_unit_of_measurement="L",
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=2,
        ),
        Metric.ECW,
        None,
    ),
    (
        SensorEntityDescription(
            key=ATTR_INTRACELLULAR_WATER,
            translation_key="intracellular_water",
            icon="mdi:water-circle",
            native_unit_of_measurement="L",
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=2,
        ),
        Metric.ICW,
        None,
    ),
    (
        SensorEntityDescription(
            key=ATTR_ECW_TBW_RATIO,
            translation_key="ecw_tbw_ratio",
            icon="mdi:chart-pie",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=1,
        ),
        Metric.ECW_TBW_RATIO,
        None,
    ),
    (
        SensorEntityDescription(
            key=ATTR_BCM,
            translation_key="body_cell_mass",
            icon="mdi:cellphone",
            native_unit_of_measurement=UnitOfMass.KILOGRAMS,
            device_class=SensorDeviceClass.WEIGHT,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=2,
        ),
        Metric.BCM,
        None,
    ),
    (
        SensorEntityDescription(
            key=ATTR_SKELETAL_MUSCLE_MASS,
            translation_key="skeletal_muscle_mass",
            icon="mdi:arm-flex",
            native_unit_of_measurement=UnitOfMass.KILOGRAMS,
            device_class=SensorDeviceClass.WEIGHT,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=2,
        ),
        Metric.SKELETAL_MUSCLE_MASS,
        None,
    ),
    (
        SensorEntityDescription(
            key=CONF_SENSOR_IMPEDANCE_HIGH,
            translation_key="impedance_high",
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=0,
            icon="mdi:omega",
        ),
        Metric.IMPEDANCE,
        None,
    ),
    (
        SensorEntityDescription(
            key=CONF_SENSOR_IMPEDANCE_LOW,
            translation_key="impedance_low",
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=0,
            icon="mdi:omega",
        ),
        Metric.IMPEDANCE,
        None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add entities for passed config_entry in HA."""
    handler: BodyScaleMetricsHandler = hass.data[DOMAIN][HANDLERS][
        config_entry.entry_id
    ]

    # Build sensor list from immutable definitions
    new_sensors: list[BodyScaleSensor] = [
        BodyScaleSensor(handler, description, metric, get_attributes)
        for description, metric, get_attributes in _BASE_SENSORS
    ]

    impedance_mode = handler.config.get(CONF_IMPEDANCE_MODE, "none")

    if impedance_mode != "none":
        new_sensors.extend(
            BodyScaleSensor(handler, description, metric, get_attributes)
            for description, metric, get_attributes in _IMPEDANCE_SENSORS
        )

    if impedance_mode == IMPEDANCE_MODE_DUAL:
        new_sensors.extend(
            BodyScaleSensor(handler, description, metric, get_attributes)
            for description, metric, get_attributes in _DUAL_SENSORS
        )

    async_add_entities(new_sensors)


class BodyScaleSensor(BodyScaleBaseEntity, RestoreSensor):
    """Body scale sensor with cold-start state restoration.

    Uses :class:`RestoreSensor` (HA standard API) to reload the last known
    ``native_value`` on restart. The restored value is fed back into the
    handler cache via ``restore_metric()`` so that dependent metrics are
    recalculated immediately without requiring a new physical measurement.

    This removes the need for dedicated per-user "persistent" input_number or
    template sensor helpers that were previously recommended in the README.
    """

    _attr_native_value: StateType | datetime | None = None

    def __init__(
        self,
        handler: BodyScaleMetricsHandler,
        entity_description: SensorEntityDescription,
        metric: Metric,
        get_attributes: (
            None
            | Callable[[StateType | datetime, Mapping[str, Any]], Mapping[str, Any]]
        ) = None,
    ) -> None:
        super().__init__(handler, entity_description)
        self._metric = metric
        self._get_attributes = get_attributes

    async def async_added_to_hass(self) -> None:
        """Set up event listeners and restore previous state."""
        await super().async_added_to_hass()

        # ── Cold-start restoration ────────────────────────────────────────
        # RestoreSensor stores the last sensor value in the HA recorder
        # (or in the restoration file).  We load it and push it into the
        # handler so derived metrics can be recalculated immediately.
        last_sensor_data = await self.async_get_last_sensor_data()
        if last_sensor_data is not None and last_sensor_data.native_value is not None:
            if self.entity_description.key == ATTR_LAST_MEASUREMENT_TIME and isinstance(
                last_sensor_data.native_value, str
            ):
                # Timestamp sensors may be persisted as ISO strings.
                try:
                    self._attr_native_value = datetime.fromisoformat(
                        last_sensor_data.native_value
                    )
                except ValueError:
                    self._attr_native_value = None
            else:
                # RestoreSensor may return Decimal; cast to our union type.
                self._attr_native_value = cast(
                    StateType | datetime, last_sensor_data.native_value
                )

            if self._get_attributes and self._attr_native_value is not None:
                self._attr_extra_state_attributes = dict(
                    self._get_attributes(
                        self._attr_native_value, dict(self._handler.config)
                    )
                )

            # Seed the handler cache — no lock or counter needed because
            # restore_metric() only writes to the TTL cache; the live
            # state-change listener is already active but will simply
            # overwrite with a fresher value when the next measurement arrives.
            self._handler.restore_metric(self._metric, self._attr_native_value)
            self.async_write_ha_state()

        # ── Live updates ──────────────────────────────────────────────────
        def on_value(value: StateType | datetime) -> None:
            """Handle a new sensor value and update the entity state."""
            if self.entity_description.key == ATTR_LAST_MEASUREMENT_TIME:
                if isinstance(value, datetime):
                    self._attr_native_value = value
                elif isinstance(value, str):
                    try:
                        self._attr_native_value = datetime.fromisoformat(value)
                    except ValueError:
                        self._attr_native_value = None
                else:
                    self._attr_native_value = value
            else:
                if isinstance(value, (int, float)):
                    precision = self.entity_description.suggested_display_precision
                    self._attr_native_value = round(
                        float(value), precision if precision is not None else 2
                    )
                else:
                    self._attr_native_value = value

            if self._get_attributes:
                self._attr_extra_state_attributes = dict(
                    self._get_attributes(
                        self._attr_native_value, dict(self._handler.config)
                    )
                )

            self.async_write_ha_state()

        self.async_on_remove(self._handler.subscribe(self._metric, on_value))

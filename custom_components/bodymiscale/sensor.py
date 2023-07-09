"""Sensor module."""
from collections.abc import Callable, Mapping
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import (
    ATTR_BMI,
    ATTR_BMILABEL,
    ATTR_BMR,
    ATTR_BODY_SCORE,
    ATTR_BONES,
    ATTR_FAT,
    ATTR_IDEAL,
    ATTR_LBM,
    ATTR_METABOLIC,
    ATTR_MUSCLE,
    ATTR_PROTEIN,
    ATTR_VISCERAL,
    ATTR_WATER,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_WEIGHT,
    DOMAIN,
    HANDLERS,
)
from .entity import BodyScaleBaseEntity
from .metrics import BodyScaleMetricsHandler
from .models import Metric
from .util import get_bmi_label, get_ideal_weight


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add entities for passed config_entry in HA."""
    handler: BodyScaleMetricsHandler = hass.data[DOMAIN][HANDLERS][
        config_entry.entry_id
    ]

    new_sensors = [
        BodyScaleSensor(
            handler,
            SensorEntityDescription(
                key=ATTR_BMI,
                icon="mdi:human",
            ),
            Metric.BMI,
            lambda state, _: {ATTR_BMILABEL: get_bmi_label(state)},
        ),
        BodyScaleSensor(
            handler,
            SensorEntityDescription(
                key=ATTR_BMR,
            ),
            Metric.BMR,
        ),
        BodyScaleSensor(
            handler,
            SensorEntityDescription(
                key=ATTR_VISCERAL,
            ),
            Metric.VISCERAL_FAT,
        ),
        BodyScaleSensor(
            handler,
            SensorEntityDescription(
                key=CONF_SENSOR_WEIGHT,
                icon="mdi:weight-kilogram",
                native_unit_of_measurement="kg",
            ),
            Metric.WEIGHT,
            lambda _, config: {ATTR_IDEAL: get_ideal_weight(config)},
        ),
    ]

    if CONF_SENSOR_IMPEDANCE in handler.config:
        new_sensors.extend(
            [
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_LBM,
                    ),
                    Metric.LBM,
                ),
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_FAT, native_unit_of_measurement="%"
                    ),
                    Metric.FAT_PERCENTAGE,
                ),
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_PROTEIN, native_unit_of_measurement="%"
                    ),
                    Metric.PROTEIN_PERCENTAGE,
                ),
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_WATER,
                        icon="mdi:water-percent",
                        native_unit_of_measurement="%",
                    ),
                    Metric.WATER_PERCENTAGE,
                ),
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_BONES,
                    ),
                    Metric.BONE_MASS,
                ),
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_MUSCLE,
                    ),
                    Metric.MUSCLE_MASS,
                ),
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_METABOLIC,
                    ),
                    Metric.METABOLIC_AGE,
                ),
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_BODY_SCORE,
                    ),
                    Metric.BODY_SCORE,
                ),
            ]
        )

    async_add_entities(new_sensors)


class BodyScaleSensor(BodyScaleBaseEntity, SensorEntity):  # type: ignore[misc]
    """Body scale sensor."""

    def __init__(
        self,
        handler: BodyScaleMetricsHandler,
        entity_description: SensorEntityDescription,
        metric: Metric,
        get_attributes: None
        | (Callable[[StateType, Mapping[str, Any]], Mapping[str, Any]]) = None,
    ):
        super().__init__(handler, entity_description)
        self.entity_description.state_class = SensorStateClass.MEASUREMENT
        self._metric = metric
        self._get_attributes = get_attributes

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        def on_value(value: StateType) -> None:
            self._attr_native_value = value
            if self._get_attributes:
                self._attr_extra_state_attributes = self._get_attributes(
                    self._attr_native_value, self._handler.config
                )
            self.async_write_ha_state()

        self.async_on_remove(self._handler.subscribe(self._metric, on_value))

"""Sensor module."""

import logging
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfMass
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
    CONF_SENSOR_LAST_MEASUREMENT_TIME,
    CONF_SENSOR_WEIGHT,
    DOMAIN,
    HANDLERS,
)
from .entity import BodyScaleBaseEntity
from .metrics import BodyScaleMetricsHandler
from .models import Metric
from .util import get_bmi_label, get_ideal_weight

_LOGGER = logging.getLogger(__name__)


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
                translation_key="bmi",
                icon="mdi:human",
                state_class=SensorStateClass.MEASUREMENT,
            ),
            Metric.BMI,
            lambda state, _: {
                ATTR_BMILABEL: (
                    get_bmi_label(float(state))
                    if isinstance(state, (int, float))
                    else None
                )
            },
        ),
        BodyScaleSensor(
            handler,
            SensorEntityDescription(
                key=ATTR_BMR,
                translation_key="basal_metabolism",
                suggested_display_precision=0,
                native_unit_of_measurement="kcal",
                state_class=SensorStateClass.MEASUREMENT,
            ),
            Metric.BMR,
        ),
        BodyScaleSensor(
            handler,
            SensorEntityDescription(
                key=ATTR_VISCERAL,
                translation_key="visceral_fat",
                suggested_display_precision=0,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            Metric.VISCERAL_FAT,
        ),
        BodyScaleSensor(
            handler,
            SensorEntityDescription(
                key=CONF_SENSOR_WEIGHT,
                translation_key="weight",
                native_unit_of_measurement=UnitOfMass.KILOGRAMS,
                device_class=SensorDeviceClass.WEIGHT,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            Metric.WEIGHT,
            lambda _, config: {ATTR_IDEAL: get_ideal_weight(config)},
        ),
    ]

    if CONF_SENSOR_LAST_MEASUREMENT_TIME in handler.config:
        new_sensors.append(
            BodyScaleSensor(
                handler,
                SensorEntityDescription(
                    key=CONF_SENSOR_LAST_MEASUREMENT_TIME,
                    translation_key="last_measurement_time",
                    device_class=SensorDeviceClass.TIMESTAMP,
                ),
                Metric.LAST_MEASUREMENT_TIME,
            )
        )

    if CONF_SENSOR_IMPEDANCE in handler.config:
        new_sensors.extend(
            [
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_LBM,
                        translation_key="lean_body_mass",
                        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
                        device_class=SensorDeviceClass.WEIGHT,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                    Metric.LBM,
                ),
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_FAT,
                        translation_key="body_fat",
                        native_unit_of_measurement=PERCENTAGE,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                    Metric.FAT_PERCENTAGE,
                ),
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_PROTEIN,
                        translation_key="protein",
                        native_unit_of_measurement=PERCENTAGE,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                    Metric.PROTEIN_PERCENTAGE,
                ),
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_WATER,
                        translation_key="water",
                        icon="mdi:water-percent",
                        native_unit_of_measurement=PERCENTAGE,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                    Metric.WATER_PERCENTAGE,
                ),
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_BONES,
                        translation_key="bone_mass",
                        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
                        device_class=SensorDeviceClass.WEIGHT,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                    Metric.BONE_MASS,
                ),
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_MUSCLE,
                        translation_key="muscle_mass",
                        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
                        device_class=SensorDeviceClass.WEIGHT,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                    Metric.MUSCLE_MASS,
                ),
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_METABOLIC,
                        translation_key="metabolic_age",
                        suggested_display_precision=0,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                    Metric.METABOLIC_AGE,
                ),
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_BODY_SCORE,
                        translation_key="body_score",
                        suggested_display_precision=0,
                        state_class=SensorStateClass.MEASUREMENT,
                    ),
                    Metric.BODY_SCORE,
                ),
            ]
        )

    async_add_entities(new_sensors)


class BodyScaleSensor(BodyScaleBaseEntity, SensorEntity):
    """Body scale sensor."""

    def __init__(
        self,
        handler: BodyScaleMetricsHandler,
        entity_description: SensorEntityDescription,
        metric: Metric,
        get_attributes: None | (
            Callable[[StateType | datetime, Mapping[str, Any]], Mapping[str, Any]]
        ) = None,
    ):
        super().__init__(handler, entity_description)
        self._metric = metric
        self._get_attributes = get_attributes

    _attr_native_value: StateType | datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Set up the event listeners now that hass is ready."""
        await super().async_added_to_hass()

        # Update the signature of on_value to accept a Union type
        def on_value(value: StateType | datetime) -> None:
            # Convert string to datetime object for timestamp sensors
            if self.device_class == SensorDeviceClass.TIMESTAMP and isinstance(
                value, str
            ):
                try:
                    self._attr_native_value = datetime.fromisoformat(value)
                except ValueError as e:
                    _LOGGER.error(
                        "Error converting date string to datetime object: %s", e
                    )
                    self._attr_native_value = None
            else:
                self._attr_native_value = value

            if self._get_attributes:
                # Update the attribute getter call to match its new signature
                attributes = self._get_attributes(
                    self._attr_native_value, dict(self._handler.config)
                )
                self._attr_extra_state_attributes = dict(attributes)

            self.async_write_ha_state()

        self.async_on_remove(self._handler.subscribe(self._metric, on_value))

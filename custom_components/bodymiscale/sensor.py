"""Sensor module."""

from collections.abc import Callable, Mapping
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
                translation_key="bmi",
                icon="mdi:human",
            ),
            Metric.BMI,
            lambda state, _: {ATTR_BMILABEL: get_bmi_label(state)},
        ),
        BodyScaleSensor(
            handler,
            SensorEntityDescription(
                key=ATTR_BMR,
                translation_key="basal_metabolism",
                suggested_display_precision=0,
                native_unit_of_measurement="kcal",
            ),
            Metric.BMR,
        ),
        BodyScaleSensor(
            handler,
            SensorEntityDescription(
                key=ATTR_VISCERAL,
                translation_key="visceral_fat",
                suggested_display_precision=0,
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
                        translation_key="lean_body_mass",
                    ),
                    Metric.LBM,
                ),
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_FAT,
                        translation_key="body_fat",
                        native_unit_of_measurement=PERCENTAGE,
                    ),
                    Metric.FAT_PERCENTAGE,
                ),
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_PROTEIN,
                        translation_key="protein",
                        native_unit_of_measurement=PERCENTAGE,
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
                    ),
                    Metric.MUSCLE_MASS,
                ),
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_METABOLIC,
                        translation_key="metabolic_age",
                        suggested_display_precision=0,
                    ),
                    Metric.METABOLIC_AGE,
                ),
                BodyScaleSensor(
                    handler,
                    SensorEntityDescription(
                        key=ATTR_BODY_SCORE,
                        translation_key="body_score",
                        suggested_display_precision=0,
                    ),
                    Metric.BODY_SCORE,
                ),
            ]
        )

    async_add_entities(new_sensors)


class BodyScaleSensor(BodyScaleBaseEntity, SensorEntity):  # type: ignore[misc]
    """Body scale sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        handler: BodyScaleMetricsHandler,
        entity_description: SensorEntityDescription,
        metric: Metric,
        get_attributes: None | (
            Callable[[StateType, Mapping[str, Any]], Mapping[str, Any]]
        ) = None,
    ):
        super().__init__(handler, entity_description)
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

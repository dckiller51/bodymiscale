"""Sensor module."""
from dataclasses import dataclass
from typing import Any, Callable, Union

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.bodymiscale.body_metrics import BodyMetricsImpedance
from custom_components.bodymiscale.body_score import BodyScore
from custom_components.bodymiscale.coordinator import BodyScaleCoordinator

from .const import (
    ATTR_BMI,
    ATTR_BMILABEL,
    ATTR_BMR,
    ATTR_BODY,
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
    COORDINATORS,
    DOMAIN,
)
from .entity import BodyScaleBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add entities for passed config_entry in HA."""
    coordinator: BodyScaleCoordinator = hass.data[DOMAIN][COORDINATORS][
        config_entry.entry_id
    ]

    new_sensors = [
        BodyScaleSensor(
            coordinator,
            SensorEntityDescription(
                key=ATTR_BMI,
                icon="mdi:human",
            ),
            lambda m: BodyScaleState(m.bmi, {ATTR_BMILABEL: m.bmi_label}),
        ),
        BodyScaleSensor(
            coordinator,
            SensorEntityDescription(
                key=ATTR_BMR,
            ),
            lambda m: BodyScaleState(m.bmr, {}),
        ),
        BodyScaleSensor(
            coordinator,
            SensorEntityDescription(
                key=ATTR_VISCERAL,
            ),
            lambda m: BodyScaleState(m.visceral_fat, {}),
        ),
        BodyScaleSensor(
            coordinator,
            SensorEntityDescription(
                key=CONF_SENSOR_WEIGHT,
                icon="mdi:weight-kilogram",
                native_unit_of_measurement="kg",
            ),
            lambda m: BodyScaleState(m.weight, {ATTR_IDEAL: m.ideal_weight}),
        ),
    ]

    if CONF_SENSOR_IMPEDANCE in coordinator.config:
        new_sensors.extend(
            [
                BodyScaleSensor(
                    coordinator,
                    SensorEntityDescription(
                        key=ATTR_LBM,
                    ),
                    lambda m: BodyScaleState(m.lbm_coefficient, {}),
                ),
                BodyScaleSensor(
                    coordinator,
                    SensorEntityDescription(
                        key=ATTR_FAT, native_unit_of_measurement="%"
                    ),
                    lambda m: BodyScaleState(m.fat_percentage, {}),
                ),
                BodyScaleSensor(
                    coordinator,
                    SensorEntityDescription(
                        key=ATTR_PROTEIN, native_unit_of_measurement="%"
                    ),
                    lambda m: BodyScaleState(m.protein_percentage, {}),
                ),
                BodyScaleSensor(
                    coordinator,
                    SensorEntityDescription(
                        key=ATTR_WATER,
                        icon="mdi:water-percent",
                        native_unit_of_measurement="%",
                    ),
                    lambda m: BodyScaleState(m.water_percentage, {}),
                ),
                BodyScaleSensor(
                    coordinator,
                    SensorEntityDescription(
                        key=ATTR_BONES,
                    ),
                    lambda m: BodyScaleState(m.bone_mass, {}),
                ),
                BodyScaleSensor(
                    coordinator,
                    SensorEntityDescription(
                        key=ATTR_MUSCLE,
                    ),
                    lambda m: BodyScaleState(m.muscle_mass, {}),
                ),
                BodyScaleSensor(
                    coordinator,
                    SensorEntityDescription(
                        key=ATTR_BODY,
                    ),
                    lambda m: BodyScaleState(m.body_type, {}),
                ),
                BodyScaleSensor(
                    coordinator,
                    SensorEntityDescription(
                        key=ATTR_METABOLIC,
                    ),
                    lambda m: BodyScaleState(m.metabolic_age, {}),
                ),
                BodyScaleSensor(
                    coordinator,
                    SensorEntityDescription(
                        key=ATTR_BODY_SCORE,
                    ),
                    lambda m: BodyScaleState(BodyScore(m).body_score, {}),
                ),
            ]
        )

    async_add_entities(new_sensors)


@dataclass
class BodyScaleState:
    """Body scale state object."""

    state: Union[int, float, str]
    attributes: dict[str, Any]


class BodyScaleSensor(BodyScaleBaseEntity, SensorEntity):  # type: ignore[misc]
    """Body scale sensor."""

    def __init__(
        self,
        coordinator: BodyScaleCoordinator,
        entity_description: SensorEntityDescription,
        get_state: Callable[[BodyMetricsImpedance], BodyScaleState],
    ):
        super().__init__(coordinator, entity_description)
        self.entity_description.state_class = SensorStateClass.MEASUREMENT
        self._get_state = get_state

    def _on_update(self) -> None:
        if self._coordinator.metrics:
            state = self._get_state(self._coordinator.metrics)  # type: ignore[arg-type]
            self._attr_native_value = state.state
            if state.attributes:
                self._attr_extra_state_attributes = state.attributes

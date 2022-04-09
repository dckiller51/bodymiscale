"""Support for bodymiscale."""
import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from awesomeversion import AwesomeVersion
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_NAME, CONF_SENSORS, STATE_OK, STATE_PROBLEM
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_component import EntityComponent

from custom_components.bodymiscale.coordinator import BodyScaleCoordinator

from .body_metrics import BodyMetricsImpedance
from .body_score import BodyScore
from .const import (
    ATTR_AGE,
    ATTR_BMI,
    ATTR_BMILABEL,
    ATTR_BMR,
    ATTR_BODY,
    ATTR_BODY_SCORE,
    ATTR_BONES,
    ATTR_FAT,
    ATTR_FATMASSTOGAIN,
    ATTR_FATMASSTOLOSE,
    ATTR_IDEAL,
    ATTR_LBM,
    ATTR_METABOLIC,
    ATTR_MUSCLE,
    ATTR_PROBLEM,
    ATTR_PROTEIN,
    ATTR_VISCERAL,
    ATTR_WATER,
    COMPONENT,
    CONF_BIRTHDAY,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_WEIGHT,
    COORDINATORS,
    DOMAIN,
    MIN_REQUIRED_HA_VERSION,
    PLATFORMS,
    PROBLEM_NONE,
    STARTUP_MESSAGE,
)
from .entity import BodyScaleBaseEntity

_LOGGER = logging.getLogger(__name__)

SCHEMA_SENSORS = vol.Schema(
    {
        vol.Required(CONF_SENSOR_WEIGHT): cv.entity_id,
        vol.Optional(CONF_SENSOR_IMPEDANCE): cv.entity_id,
    }
)

BODYMISCALE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SENSORS): vol.Schema(SCHEMA_SENSORS),
        vol.Required(CONF_HEIGHT): cv.positive_int,
        vol.Required("born"): cv.string,
        vol.Required(CONF_GENDER): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: {cv.string: BODYMISCALE_SCHEMA}}, extra=vol.ALLOW_EXTRA
)


def is_ha_supported() -> bool:
    """Return True, if current HA version is supported."""
    if AwesomeVersion(HA_VERSION) >= MIN_REQUIRED_HA_VERSION:
        return True

    _LOGGER.error(
        'Unsupported HA version! Please upgrade home assistant at least to "%s"',
        MIN_REQUIRED_HA_VERSION,
    )
    return False


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up component via yaml."""
    if DOMAIN in config:
        if not is_ha_supported():
            return False

        _LOGGER.warning(
            "Configuration of the bodymiscale in YAML is deprecated "
            "and will be removed future versions; Your existing "
            "configuration has been imported into the UI automatically and can be "
            "safely removed from your configuration.yaml file"
        )

        for name, conf in config[DOMAIN].items():
            conf[CONF_NAME] = name
            conf[CONF_SENSOR_WEIGHT] = conf[CONF_SENSORS][CONF_SENSOR_WEIGHT]
            if CONF_SENSOR_IMPEDANCE in conf[CONF_SENSORS]:
                conf[CONF_SENSOR_IMPEDANCE] = conf[CONF_SENSORS][CONF_SENSOR_IMPEDANCE]

            del conf[CONF_SENSORS]

            conf[CONF_BIRTHDAY] = conf.pop("born")

            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN, context={"source": SOURCE_IMPORT}, data=conf
                )
            )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up component via UI."""
    if not is_ha_supported():
        return False

    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(
            DOMAIN,
            {
                COMPONENT: EntityComponent(_LOGGER, DOMAIN, hass),
                COORDINATORS: {},
            },
        )
        _LOGGER.info(STARTUP_MESSAGE)

    coordinator = hass.data[DOMAIN][COORDINATORS][
        entry.entry_id
    ] = BodyScaleCoordinator(hass, entry.data)

    component = hass.data[DOMAIN][COMPONENT]
    await component.async_add_entities([Bodymiscale(coordinator)])

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


class Bodymiscale(BodyScaleBaseEntity):
    """Bodymiscale the well-being of a body.

    It also checks the measurements against weight, height, age,
    gender and impedance (if configured).
    """

    def __init__(self, coordinator: BodyScaleCoordinator):
        """Initialize the Bodymiscale component."""
        super().__init__(
            coordinator,
            EntityDescription(
                key="Bodymiscale", name=coordinator.config[CONF_NAME], icon="mdi:human"
            ),
        )

    def _on_update(self) -> None:
        """Perform actions on update."""
        if self._coordinator.problems == PROBLEM_NONE:
            self._attr_state = STATE_OK
        else:
            self._attr_state = STATE_PROBLEM
        self.async_write_ha_state()

    @property
    def state_attributes(self) -> dict[str, Any]:
        """Return the attributes of the entity."""
        attrib = {
            ATTR_PROBLEM: self._coordinator.problems,
            CONF_HEIGHT: self._coordinator.config[CONF_HEIGHT],
            CONF_GENDER: self._coordinator.config[CONF_GENDER].value,
            ATTR_AGE: self._coordinator.config[ATTR_AGE],
            CONF_SENSOR_WEIGHT: self._coordinator.weight,
        }

        if CONF_SENSOR_IMPEDANCE in self._coordinator.config:
            attrib[CONF_SENSOR_IMPEDANCE] = self._coordinator.impedance

        metrics = self._coordinator.metrics

        if metrics:
            attrib[ATTR_BMI] = f"{metrics.bmi:.1f}"
            attrib[ATTR_BMR] = f"{metrics.bmr:.0f}"
            attrib[ATTR_VISCERAL] = f"{metrics.visceral_fat:.0f}"
            attrib[ATTR_IDEAL] = f"{metrics.ideal_weight:.2f}"
            attrib[ATTR_BMILABEL] = metrics.bmi_label

            if isinstance(metrics, BodyMetricsImpedance):
                bodyscale = [
                    "Obese",
                    "Overweight",
                    "Thick-set",
                    "Lack-exercise",
                    "Balanced",
                    "Balanced-muscular",
                    "Skinny",
                    "Balanced-skinny",
                    "Skinny-muscular",
                ]
                attrib[ATTR_LBM] = f"{metrics.lbm_coefficient:.1f}"
                attrib[ATTR_FAT] = f"{metrics.fat_percentage:.1f}"
                attrib[ATTR_WATER] = f"{metrics.water_percentage:.1f}"
                attrib[ATTR_BONES] = f"{metrics.bone_mass:.2f}"
                attrib[ATTR_MUSCLE] = f"{metrics.muscle_mass:.2f}"
                fat_mass_to_ideal = metrics.fat_mass_to_ideal
                if fat_mass_to_ideal["type"] == "to_lose":
                    attrib[ATTR_FATMASSTOLOSE] = f"{fat_mass_to_ideal['mass']:.2f}"
                else:
                    attrib[ATTR_FATMASSTOGAIN] = f"{fat_mass_to_ideal['mass']:.2f}"
                attrib[ATTR_PROTEIN] = f"{metrics.protein_percentage:.1f}"
                attrib[ATTR_BODY] = bodyscale[metrics.body_type]
                attrib[ATTR_METABOLIC] = f"{metrics.metabolic_age:.0f}"
                body_score = BodyScore(metrics)
                attrib[ATTR_BODY_SCORE] = f"{body_score.body_score:.0f}"

        return attrib

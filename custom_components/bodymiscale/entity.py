"""Bodymiscale entity module."""
from typing import Optional

from homeassistant.const import CONF_NAME
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityDescription

from .const import DOMAIN, NAME, VERSION
from .metrics import BodyScaleMetricsHandler


class BodyScaleBaseEntity(Entity):  # type: ignore[misc]
    """Body scale base entity."""

    _attr_should_poll = False

    def __init__(
        self,
        handler: BodyScaleMetricsHandler,
        entity_description: Optional[EntityDescription] = None,
    ):
        """Initialize the entity."""
        super().__init__()
        self._handler = handler
        if entity_description:
            self.entity_description = entity_description
        elif not hasattr(self, "entity_description"):
            raise ValueError(
                '"entity_description" must be either set as class variable or passed on init!'
            )

        if not self.entity_description.key:
            raise ValueError('"entity_description.key" must be either set!')

        name = handler.config[CONF_NAME]
        self._attr_unique_id = "_".join([DOMAIN, name, self.entity_description.key])

        if self.entity_description.name:
            # Name provided, using the provided one
            if not self.entity_description.name.lower().startswith(name.lower()):
                # Entity name should start with configurated name
                self._attr_name = f"{name} {self.entity_description.name}"
        else:
            self._attr_name = f"{name} {self.entity_description.key.replace('_', ' ')}"

    @property
    def device_info(self) -> Optional[DeviceInfo]:
        """Return device specific attributes."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            name=NAME,
            sw_version=VERSION,
            identifiers={(DOMAIN, self._handler.config_entry_id)},
        )

"""Bodymiscale entity module."""

from homeassistant.const import CONF_NAME
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import UNDEFINED, Entity, EntityDescription

from .const import DOMAIN, VERSION
from .metrics import BodyScaleMetricsHandler


class BodyScaleBaseEntity(Entity):  # type: ignore[misc]
    """Body scale base entity."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        handler: BodyScaleMetricsHandler,
        entity_description: EntityDescription | None = None,
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

        if self.entity_description.name == UNDEFINED:
            # Name not provided... get it from the key
            self._attr_name = self.entity_description.key.replace("_", " ").capitalize()
        else:
            self._attr_name = (
                self._handler.config[CONF_NAME].replace("_", " ").capitalize()
            )
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            name=self._handler.config[CONF_NAME],
            sw_version=VERSION,
            identifiers={(DOMAIN, self._handler.config_entry_id)},
        )
        
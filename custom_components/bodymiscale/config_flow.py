"""Config flow to configure the bodymiscale integration."""
from __future__ import annotations

from types import MappingProxyType
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_MODE, CONF_NAME, CONF_UNIT_OF_MEASUREMENT
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import selector

from .const import (
    CONF_BIRTHDAY,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_WEIGHT,
    CONSTRAINT_HEIGHT_MAX,
    CONSTRAINT_HEIGHT_MIN,
    DOMAIN,
    MAX,
    MIN,
)
from .models import Gender


@callback  # type: ignore[misc]
def _get_schema(
    defaults: dict[str, Any] | MappingProxyType[str, Any], is_options_handler: bool
) -> vol.Schema:
    """Return bodymiscale schema."""

    schema = {
        vol.Required(
            CONF_HEIGHT, default=defaults.get(CONF_HEIGHT, vol.UNDEFINED)
        ): selector(
            {
                "number": {
                    MIN: CONSTRAINT_HEIGHT_MIN,
                    MAX: CONSTRAINT_HEIGHT_MAX,
                    CONF_UNIT_OF_MEASUREMENT: "cm",
                    CONF_MODE: "box",
                }
            }
        ),
        vol.Required(
            CONF_SENSOR_WEIGHT, default=defaults.get(CONF_SENSOR_WEIGHT, vol.UNDEFINED)
        ): selector({"entity": {"domain": "sensor"}}),
        vol.Optional(
            CONF_SENSOR_IMPEDANCE,
            default=defaults.get(CONF_SENSOR_IMPEDANCE, vol.UNDEFINED),
        ): selector({"entity": {"domain": "sensor"}}),
    }

    if not is_options_handler:
        schema = {
            vol.Required(
                CONF_NAME, default=defaults.get(CONF_NAME, vol.UNDEFINED)
            ): str,
            vol.Required(
                CONF_BIRTHDAY, default=defaults.get(CONF_BIRTHDAY, vol.UNDEFINED)
            ): selector({"date": {}}),
            vol.Required(
                CONF_GENDER, default=defaults.get(CONF_GENDER, vol.UNDEFINED)
            ): vol.In({gender: gender.value for gender in Gender}),
            **schema,
        }

    return vol.Schema(schema)


class BodyMiScaleFlowHandler(ConfigFlow, domain=DOMAIN):  # type: ignore[misc, call-arg]
    """Config flow for bodymiscale."""

    VERSION = 1

    @staticmethod
    @callback  # type: ignore[misc]
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> BodyMiScaleOptionsFlowHandler:
        """Get the options flow for this handler."""
        return BodyMiScaleOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            if user_input[CONF_HEIGHT] > CONSTRAINT_HEIGHT_MAX:
                errors[CONF_HEIGHT] = "height_limit"
            else:
                return self._create_entry(user_input)

        user_input = {}
        return self.async_show_form(
            step_id="user",
            data_schema=_get_schema(user_input, is_options_handler=False),
            errors=errors,
        )

    async def async_step_import(self, config: dict[str, Any]) -> FlowResult:
        """Handle a flow initialized by importing a config."""
        return self._create_entry(config)

    def _create_entry(self, config: dict[str, Any]) -> FlowResult:
        self._async_abort_entries_match({CONF_NAME: config[CONF_NAME]})

        return self.async_create_entry(title=config[CONF_NAME], data=config)


class BodyMiScaleOptionsFlowHandler(OptionsFlow):  # type: ignore[misc]
    """Handle Body mi scale options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize Body mi scale options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage Body mi scale options."""

        if user_input is not None:
            return self.async_create_entry(
                title=self._config_entry.title,
                data={**self._config_entry.data, **user_input},
            )

        user_input = self._config_entry.data

        return self.async_show_form(
            step_id="init",
            data_schema=_get_schema(user_input, is_options_handler=True),
        )

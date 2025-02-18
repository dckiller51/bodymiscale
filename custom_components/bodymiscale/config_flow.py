"""Config flow to configure the bodymiscale integration."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

import homeassistant.helpers.config_validation as cv
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
    CONF_IMPEDANCE_SENSOR,
    CONF_WEIGHT_SENSOR,
    CONSTRAINT_HEIGHT_MAX,
    CONSTRAINT_HEIGHT_MIN,
    DOMAIN,
    MAX,
    MIN,
)
from .models import Gender


@callback
def _get_options_schema(
    defaults: dict[str, Any] | MappingProxyType[str, Any]
) -> vol.Schema:
    """Return options schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_HEIGHT,
                description={"suggested_value": defaults.get(CONF_HEIGHT)},  # Suggested height value
            ): selector(
                {
                    "number": {
                        MIN: CONSTRAINT_HEIGHT_MIN,  # Minimum height
                        MAX: CONSTRAINT_HEIGHT_MAX,  # Maximum height
                        CONF_UNIT_OF_MEASUREMENT: "cm",  # Unit of measurement for height
                        CONF_MODE: "box",  # Input mode for height
                    }
                }
            ),
            vol.Required(
                CONF_WEIGHT_SENSOR,
                description={"suggested_value": defaults.get(CONF_WEIGHT_SENSOR)},  # Suggested weight sensor
            ): selector({"entity": {"domain": ["sensor", "input_number", "number"]}}),  # Selector for weight sensor
            vol.Optional(
                CONF_IMPEDANCE_SENSOR,
                description={"suggested_value": defaults.get(CONF_IMPEDANCE_SENSOR)},  # Suggested impedance sensor
            ): selector({"entity": {"domain": ["sensor", "input_number", "number"]}}),  # Selector for impedance sensor
        }
    )


class BodyMiScaleFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for bodymiscale."""

    VERSION = 2

    def __init__(self) -> None:
        super().__init__()
        self._data: dict[str, str] = {}

    @staticmethod
    @callback
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
            try:
                cv.date(user_input[CONF_BIRTHDAY])  # Validate the date of birth
            except vol.Invalid:
                errors[CONF_BIRTHDAY] = "invalid_date"  # Set error if date is invalid

            if not errors:  # If no errors
                self._async_abort_entries_match({CONF_NAME: user_input[CONF_NAME]})  # Abort if entry with same name exists
                self._data = user_input  # Store the user input
                return await self.async_step_options()  # Proceed to the options step
        else:
            user_input = {}  # Initialize user input

        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(  # Schema for the user step
                {
                    vol.Required(
                        CONF_NAME, default=user_input.get(CONF_NAME, vol.UNDEFINED)  # Name field
                    ): str,
                    vol.Required(
                        CONF_BIRTHDAY,
                        default=user_input.get(CONF_BIRTHDAY, vol.UNDEFINED),  # Date of birth field
                    ): selector({"text": {"type": "date"}}),  # Date selector
                    vol.Required(
                        CONF_GENDER, default=user_input.get(CONF_GENDER, vol.UNDEFINED)  # Gender field
                    ): vol.In({gender: gender.value for gender in Gender}),  # Gender selector
                }
            ),
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle step options."""
        errors = {}
        if user_input is not None:
            if user_input[CONF_HEIGHT] > CONSTRAINT_HEIGHT_MAX:  # Validate height
                errors[CONF_HEIGHT] = "height_limit"  # Set error if height is too high
            elif user_input[CONF_HEIGHT] < CONSTRAINT_HEIGHT_MIN:  # Validate height
                errors[CONF_HEIGHT] = "height_low"  # Set error if height is too low

            if not errors:  # If no errors
                return self.async_create_entry(
                    title=self._data[CONF_NAME], data=self._data, options=user_input  # Create the config entry
                )

        user_input = {}  # Initialize user input
        return self.async_show_form(
            step_id="options",
            data_schema=_get_options_schema(user_input),  # Schema for the options step
            errors=errors,
        )


class BodyMiScaleOptionsFlowHandler(OptionsFlow):
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
                data=user_input,  # Create the config entry with the options
            )

        user_input = self._config_entry.options  # Get the current options

        return self.async_show_form(
            step_id="init",
            data_schema=_get_options_schema(user_input),  # Schema for the options
        )
    
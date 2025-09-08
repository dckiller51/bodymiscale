"""Config flow to configure the bodymiscale integration."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BIRTHDAY,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_LAST_MEASUREMENT_TIME,
    CONF_SENSOR_WEIGHT,
    CONSTRAINT_HEIGHT_MAX,
    CONSTRAINT_HEIGHT_MIN,
    DOMAIN,
)
from .models import Gender


@callback  # type: ignore[misc]
def _get_options_schema(
    defaults: dict[str, Any] | MappingProxyType[str, Any],
) -> vol.Schema:
    """Return options schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_HEIGHT,
                description=(
                    {"suggested_value": defaults[CONF_HEIGHT]}
                    if CONF_HEIGHT in defaults
                    else None
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=CONSTRAINT_HEIGHT_MIN,
                    max=CONSTRAINT_HEIGHT_MAX,
                    unit_of_measurement="cm",
                )
            ),
            vol.Required(
                CONF_SENSOR_WEIGHT,
                description=(
                    {"suggested_value": defaults[CONF_SENSOR_WEIGHT]}
                    if CONF_SENSOR_WEIGHT in defaults
                    else None
                ),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["sensor", "input_number", "number"]
                )
            ),
            vol.Optional(
                CONF_SENSOR_IMPEDANCE,
                description=(
                    {"suggested_value": defaults[CONF_SENSOR_IMPEDANCE]}
                    if CONF_SENSOR_IMPEDANCE in defaults
                    else None
                ),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["sensor", "input_number", "number"]
                )
            ),
            vol.Optional(
                CONF_SENSOR_LAST_MEASUREMENT_TIME,
                description=(
                    {"suggested_value": defaults[CONF_SENSOR_LAST_MEASUREMENT_TIME]}
                    if CONF_SENSOR_LAST_MEASUREMENT_TIME in defaults
                    else None
                ),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_datetime"])
            ),
        }
    )


class BodyMiScaleFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for bodymiscale."""

    VERSION = 2

    def __init__(self) -> None:
        super().__init__()
        self._data: dict[str, str] = {}

    @staticmethod
    @callback  # type: ignore[misc]
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> BodyMiScaleOptionsFlowHandler:
        """Get the options flow for this handler."""
        return BodyMiScaleOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                cv.date(user_input[CONF_BIRTHDAY])
            except vol.Invalid:
                errors[CONF_BIRTHDAY] = "invalid_date"

            if not errors:
                self._async_abort_entries_match({CONF_NAME: user_input[CONF_NAME]})
                self._data = user_input
                return await self.async_step_options()

        user_input = user_input or {}
        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME, default=user_input.get(CONF_NAME, vol.UNDEFINED)
                    ): str,
                    vol.Required(
                        CONF_BIRTHDAY,
                        default=user_input.get(CONF_BIRTHDAY, vol.UNDEFINED),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.DATE)
                    ),
                    vol.Required(
                        CONF_GENDER, default=user_input.get(CONF_GENDER, vol.UNDEFINED)
                    ): vol.In({gender: gender.value for gender in Gender}),
                }
            ),
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle step options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input[CONF_HEIGHT] > CONSTRAINT_HEIGHT_MAX:
                errors[CONF_HEIGHT] = "height_limit"
            elif user_input[CONF_HEIGHT] < CONSTRAINT_HEIGHT_MIN:
                errors[CONF_HEIGHT] = "height_low"

            return self.async_create_entry(
                title=self._data[CONF_NAME],
                data=self._data,
                options=user_input,
            )

        user_input = user_input or {}
        return self.async_show_form(
            step_id="options",
            data_schema=_get_options_schema(user_input),
            errors=errors,
        )


class BodyMiScaleOptionsFlowHandler(OptionsFlow):  # type: ignore[misc, call-arg]
    """Handle Body mi scale options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize Body mi scale options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage Body mi scale options."""

        if user_input is not None:
            return self.async_create_entry(data=user_input)

        # Convert MappingProxyType en dict
        user_input = dict(self._config_entry.options)

        return self.async_show_form(
            step_id="init",
            data_schema=_get_options_schema(user_input),
        )

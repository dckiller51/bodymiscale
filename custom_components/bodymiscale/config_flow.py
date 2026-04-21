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
    CALCULATION_MODE_OPTIONS,
    CONF_BIRTHDAY,
    CONF_CALCULATION_MODE,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_IMPEDANCE_MODE,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_IMPEDANCE_HIGH,
    CONF_SENSOR_IMPEDANCE_LOW,
    CONF_SENSOR_LAST_MEASUREMENT_TIME,
    CONF_SENSOR_WEIGHT,
    CONSTRAINT_HEIGHT_MAX,
    CONSTRAINT_HEIGHT_MIN,
    DOMAIN,
    IMPEDANCE_MODE_DUAL,
    IMPEDANCE_MODE_NONE,
    IMPEDANCE_MODE_OPTIONS,
    IMPEDANCE_MODE_STANDARD,
)
from .models import Gender


@callback
def _get_main_options_schema(
    defaults: dict[str, Any] | MappingProxyType[str, Any],
) -> vol.Schema:
    """Return the main options schema (page 1: height, calculation mode, impedance mode, weight, last measurement)."""
    return vol.Schema(
        {
            vol.Required(
                CONF_HEIGHT,
                description={"suggested_value": defaults.get(CONF_HEIGHT)},
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=CONSTRAINT_HEIGHT_MIN,
                    max=CONSTRAINT_HEIGHT_MAX,
                    unit_of_measurement="cm",
                )
            ),
            vol.Required(
                CONF_CALCULATION_MODE,
                default=defaults.get(CONF_CALCULATION_MODE, "xiaomi"),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=CALCULATION_MODE_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="calculation_mode",
                )
            ),
            vol.Required(
                CONF_SENSOR_WEIGHT,
                description={"suggested_value": defaults.get(CONF_SENSOR_WEIGHT)},
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["sensor", "input_number", "number"]
                )
            ),
            vol.Optional(
                CONF_SENSOR_LAST_MEASUREMENT_TIME,
                description={
                    "suggested_value": defaults.get(CONF_SENSOR_LAST_MEASUREMENT_TIME)
                },
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_datetime"])
            ),
            vol.Required(
                CONF_IMPEDANCE_MODE,
                default=defaults.get(CONF_IMPEDANCE_MODE, IMPEDANCE_MODE_NONE),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=IMPEDANCE_MODE_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="impedance_mode",
                )
            ),
        }
    )


def _get_impedance_schema(mode: str, defaults: dict[str, Any]) -> vol.Schema:
    """Return the impedance sensor schema for the selected mode (page 2)."""
    fields: dict = {}

    if mode == IMPEDANCE_MODE_STANDARD:
        fields[
            vol.Required(
                CONF_SENSOR_IMPEDANCE,
                description={"suggested_value": defaults.get(CONF_SENSOR_IMPEDANCE)},
            )
        ] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number", "number"])
        )

    elif mode == IMPEDANCE_MODE_DUAL:
        fields[
            vol.Required(
                CONF_SENSOR_IMPEDANCE_LOW,
                description={
                    "suggested_value": defaults.get(CONF_SENSOR_IMPEDANCE_LOW)
                },
            )
        ] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number", "number"])
        )
        fields[
            vol.Required(
                CONF_SENSOR_IMPEDANCE_HIGH,
                description={
                    "suggested_value": defaults.get(CONF_SENSOR_IMPEDANCE_HIGH)
                },
            )
        ] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number", "number"])
        )

    return vol.Schema(fields)


class BodyMiScaleFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for bodymiscale."""

    VERSION = 3

    def __init__(self) -> None:
        """Initialize BodyMiScaleFlowHandler."""
        super().__init__()
        self._data: dict[str, Any] = {}

    @staticmethod
    @callback
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

        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_BIRTHDAY): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.DATE)
                    ),
                    vol.Required(CONF_GENDER): vol.In(
                        {gender: gender.value for gender in Gender}
                    ),
                }
            ),
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the main options step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input[CONF_HEIGHT] > CONSTRAINT_HEIGHT_MAX:
                errors[CONF_HEIGHT] = "height_limit"
            elif user_input[CONF_HEIGHT] < CONSTRAINT_HEIGHT_MIN:
                errors[CONF_HEIGHT] = "height_low"

            if not errors:
                self._data.update(user_input)
                if user_input[CONF_IMPEDANCE_MODE] == IMPEDANCE_MODE_NONE:
                    return self.async_create_entry(
                        title=self._data[CONF_NAME],
                        data=self._data,
                        options=self._data,
                    )
                return await self.async_step_impedance()

        return self.async_show_form(
            step_id="options",
            errors=errors,
            data_schema=_get_main_options_schema(self._data),
        )

    async def async_step_impedance(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the impedance sensors step."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(
                title=self._data[CONF_NAME],
                data=self._data,
                options=self._data,
            )

        mode = self._data.get(CONF_IMPEDANCE_MODE, IMPEDANCE_MODE_NONE)
        return self.async_show_form(
            step_id="impedance",
            data_schema=_get_impedance_schema(mode, self._data),
        )


class BodyMiScaleOptionsFlowHandler(OptionsFlow):
    """Options flow for bodymiscale."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize BodyMiScaleOptionsFlowHandler."""
        self._config_entry = config_entry
        self._data = dict(config_entry.options)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the main options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input[CONF_HEIGHT] > CONSTRAINT_HEIGHT_MAX:
                errors[CONF_HEIGHT] = "height_limit"
            elif user_input[CONF_HEIGHT] < CONSTRAINT_HEIGHT_MIN:
                errors[CONF_HEIGHT] = "height_low"

            if not errors:
                self._data.update(user_input)
                if user_input[CONF_IMPEDANCE_MODE] == IMPEDANCE_MODE_NONE:
                    # Clean up orphaned impedance keys
                    for k in [
                        CONF_SENSOR_IMPEDANCE,
                        CONF_SENSOR_IMPEDANCE_LOW,
                        CONF_SENSOR_IMPEDANCE_HIGH,
                    ]:
                        self._data.pop(k, None)
                    return self.async_create_entry(data=self._data)
                return await self.async_step_impedance()

        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=_get_main_options_schema(self._data),
        )

    async def async_step_impedance(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the impedance sensor options."""
        if user_input is not None:
            mode = self._data.get(CONF_IMPEDANCE_MODE)
            # Clean up keys from the previous mode
            if mode == IMPEDANCE_MODE_STANDARD:
                self._data.pop(CONF_SENSOR_IMPEDANCE_LOW, None)
                self._data.pop(CONF_SENSOR_IMPEDANCE_HIGH, None)
            elif mode == IMPEDANCE_MODE_DUAL:
                self._data.pop(CONF_SENSOR_IMPEDANCE, None)
            self._data.update(user_input)
            return self.async_create_entry(data=self._data)

        mode = self._data.get(CONF_IMPEDANCE_MODE, IMPEDANCE_MODE_NONE)
        return self.async_show_form(
            step_id="impedance",
            data_schema=_get_impedance_schema(mode, self._data),
        )

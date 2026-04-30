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
    CONF_HANDLE_USER_DETERMINATION,
    CONF_HEIGHT,
    CONF_IMPEDANCE_MODE,
    CONF_PROFILE_ID,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_IMPEDANCE_HIGH,
    CONF_SENSOR_IMPEDANCE_LOW,
    CONF_SENSOR_LAST_MEASUREMENT_TIME,
    CONF_SENSOR_PROFILE_ID,
    CONF_SENSOR_WEIGHT,
    CONF_WEIGHT_RANGE_MAX,
    CONF_WEIGHT_RANGE_MIN,
    CONSTRAINT_HEIGHT_MAX,
    CONSTRAINT_HEIGHT_MIN,
    CONSTRAINT_PROFILE_ID_MAX,
    CONSTRAINT_PROFILE_ID_MIN,
    CONSTRAINT_WEIGHT_MAX,
    CONSTRAINT_WEIGHT_MIN,
    DOMAIN,
    IMPEDANCE_MODE_DUAL,
    IMPEDANCE_MODE_NONE,
    IMPEDANCE_MODE_OPTIONS,
    IMPEDANCE_MODE_STANDARD,
)
from .models import Gender

USER_DETERMINATION_KEYS = (
    CONF_SENSOR_PROFILE_ID,
    CONF_PROFILE_ID,
    CONF_WEIGHT_RANGE_MIN,
    CONF_WEIGHT_RANGE_MAX,
)


def _has_value(value: Any) -> bool:
    """Return True if a flow value should be treated as configured."""
    return value is not None and value != ""


def _has_complete_user_determination(
    defaults: dict[str, Any] | MappingProxyType[str, Any],
) -> bool:
    """Return True if either user determination method is fully configured."""
    return (
        _has_value(defaults.get(CONF_SENSOR_PROFILE_ID))
        and _has_value(defaults.get(CONF_PROFILE_ID))
    ) or (
        _has_value(defaults.get(CONF_WEIGHT_RANGE_MIN))
        and _has_value(defaults.get(CONF_WEIGHT_RANGE_MAX))
    )


def _clear_user_determination(data: dict[str, Any]) -> None:
    """Remove all saved user determination fields."""
    for key in USER_DETERMINATION_KEYS:
        data.pop(key, None)


def _clean_empty_user_determination(data: dict[str, Any]) -> dict[str, Any]:
    """Remove empty optional user determination fields from submitted data."""
    return {key: value for key, value in data.items() if _has_value(value)}


@callback
def _get_main_options_schema(
    defaults: dict[str, Any] | MappingProxyType[str, Any],
    include_height: bool = False,
) -> vol.Schema:
    """Return the main options schema."""
    fields: dict = {}

    if include_height:
        fields[
            vol.Required(
                CONF_HEIGHT,
                description={"suggested_value": defaults.get(CONF_HEIGHT)},
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                min=CONSTRAINT_HEIGHT_MIN,
                max=CONSTRAINT_HEIGHT_MAX,
                unit_of_measurement="cm",
            )
        )

    fields.update(
        {
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
            vol.Required(
                CONF_HANDLE_USER_DETERMINATION,
                default=_has_complete_user_determination(defaults),
            ): selector.BooleanSelector(),
        }
    )

    return vol.Schema(fields)


def _get_profile_schema() -> vol.Schema:
    """Return the profile schema for a new entry."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_BIRTHDAY): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.DATE)
            ),
            vol.Required(CONF_GENDER): vol.In(
                {gender: gender.value for gender in Gender}
            ),
            vol.Required(CONF_HEIGHT): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=CONSTRAINT_HEIGHT_MIN,
                    max=CONSTRAINT_HEIGHT_MAX,
                    unit_of_measurement="cm",
                )
            ),
        }
    )


def _validate_height(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate height if present in the submitted form."""
    errors: dict[str, str] = {}
    if CONF_HEIGHT not in user_input:
        return errors

    if user_input[CONF_HEIGHT] > CONSTRAINT_HEIGHT_MAX:
        errors[CONF_HEIGHT] = "height_limit"
    elif user_input[CONF_HEIGHT] < CONSTRAINT_HEIGHT_MIN:
        errors[CONF_HEIGHT] = "height_low"

    return errors


def _get_user_determination_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Return the optional user determination schema."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_SENSOR_PROFILE_ID,
                description={"suggested_value": defaults.get(CONF_SENSOR_PROFILE_ID)},
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["sensor", "input_number", "number"]
                )
            ),
            vol.Optional(
                CONF_PROFILE_ID,
                description={"suggested_value": defaults.get(CONF_PROFILE_ID)},
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=CONSTRAINT_PROFILE_ID_MIN,
                    max=CONSTRAINT_PROFILE_ID_MAX,
                )
            ),
            vol.Optional(
                CONF_WEIGHT_RANGE_MIN,
                description={"suggested_value": defaults.get(CONF_WEIGHT_RANGE_MIN)},
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=CONSTRAINT_WEIGHT_MIN,
                    max=CONSTRAINT_WEIGHT_MAX,
                    unit_of_measurement="kg",
                )
            ),
            vol.Optional(
                CONF_WEIGHT_RANGE_MAX,
                description={"suggested_value": defaults.get(CONF_WEIGHT_RANGE_MAX)},
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=CONSTRAINT_WEIGHT_MIN,
                    max=CONSTRAINT_WEIGHT_MAX,
                    unit_of_measurement="kg",
                )
            ),
        }
    )


def _validate_user_determination(user_input: dict[str, Any]) -> dict[str, str]:
    """Validate the user determination page."""
    errors: dict[str, str] = {}
    profile_sensor_configured = _has_value(user_input.get(CONF_SENSOR_PROFILE_ID))
    profile_id_configured = _has_value(user_input.get(CONF_PROFILE_ID))
    range_min_configured = _has_value(user_input.get(CONF_WEIGHT_RANGE_MIN))
    range_max_configured = _has_value(user_input.get(CONF_WEIGHT_RANGE_MAX))

    profile_complete = profile_sensor_configured and profile_id_configured
    range_complete = range_min_configured and range_max_configured

    if profile_sensor_configured != profile_id_configured:
        errors["base"] = "profile_id_incomplete"
    elif range_min_configured != range_max_configured:
        errors["base"] = "weight_range_incomplete"
    elif not profile_complete and not range_complete:
        errors["base"] = "user_determination_required"
    elif range_complete and (
        user_input[CONF_WEIGHT_RANGE_MIN] >= user_input[CONF_WEIGHT_RANGE_MAX]
    ):
        errors[CONF_WEIGHT_RANGE_MAX] = "weight_range_invalid"

    return errors


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
        self._handle_user_determination = False

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

            errors.update(_validate_height(user_input))

            if not errors:
                self._async_abort_entries_match({CONF_NAME: user_input[CONF_NAME]})
                self._data = user_input
                return await self.async_step_options()

        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=_get_profile_schema(),
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the main options step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not errors:
                self._handle_user_determination = user_input.pop(
                    CONF_HANDLE_USER_DETERMINATION
                )
                self._data.update(user_input)

                if not self._handle_user_determination:
                    _clear_user_determination(self._data)
                return await self._async_step_after_options()

        return self.async_show_form(
            step_id="options",
            errors=errors,
            data_schema=_get_main_options_schema(self._data),
        )

    async def async_step_user_determination(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle optional user determination settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input = _clean_empty_user_determination(user_input)
            errors = _validate_user_determination(user_input)

            if not errors:
                _clear_user_determination(self._data)
                self._data.update(user_input)
                return self.async_create_entry(
                    title=self._data[CONF_NAME],
                    data=self._data,
                    options=self._data,
                )

        return self.async_show_form(
            step_id="user_determination",
            errors=errors,
            data_schema=_get_user_determination_schema(self._data),
        )

    async def async_step_impedance(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the impedance sensors step."""
        if user_input is not None:
            self._data.update(user_input)
            if self._handle_user_determination:
                return await self.async_step_user_determination()
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

    async def _async_step_after_options(self) -> ConfigFlowResult:
        """Continue to impedance, user determination, or create the entry."""
        if self._data[CONF_IMPEDANCE_MODE] != IMPEDANCE_MODE_NONE:
            return await self.async_step_impedance()

        if self._handle_user_determination:
            return await self.async_step_user_determination()

        return self.async_create_entry(
            title=self._data[CONF_NAME],
            data=self._data,
            options=self._data,
        )


class BodyMiScaleOptionsFlowHandler(OptionsFlow):
    """Options flow for bodymiscale."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize BodyMiScaleOptionsFlowHandler."""
        self._config_entry = config_entry
        self._data = dict(config_entry.options)
        self._handle_user_determination = _has_complete_user_determination(self._data)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the main options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = _validate_height(user_input)

            if not errors:
                self._handle_user_determination = user_input.pop(
                    CONF_HANDLE_USER_DETERMINATION
                )
                self._data.update(user_input)

                if not self._handle_user_determination:
                    _clear_user_determination(self._data)
                return await self._async_step_after_options()

        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=_get_main_options_schema(self._data, include_height=True),
        )

    async def async_step_user_determination(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage optional user determination settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input = _clean_empty_user_determination(user_input)
            errors = _validate_user_determination(user_input)

            if not errors:
                _clear_user_determination(self._data)
                self._data.update(user_input)
                return self.async_create_entry(data=self._data)

        return self.async_show_form(
            step_id="user_determination",
            errors=errors,
            data_schema=_get_user_determination_schema(self._data),
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
            if self._handle_user_determination:
                return await self.async_step_user_determination()
            return self.async_create_entry(data=self._data)

        mode = self._data.get(CONF_IMPEDANCE_MODE, IMPEDANCE_MODE_NONE)
        return self.async_show_form(
            step_id="impedance",
            data_schema=_get_impedance_schema(mode, self._data),
        )

    async def _async_step_after_options(self) -> ConfigFlowResult:
        """Continue to impedance, user determination, or create the entry."""
        if self._data[CONF_IMPEDANCE_MODE] != IMPEDANCE_MODE_NONE:
            return await self.async_step_impedance()

        for key in [
            CONF_SENSOR_IMPEDANCE,
            CONF_SENSOR_IMPEDANCE_LOW,
            CONF_SENSOR_IMPEDANCE_HIGH,
        ]:
            self._data.pop(key, None)

        if self._handle_user_determination:
            return await self.async_step_user_determination()

        return self.async_create_entry(data=self._data)

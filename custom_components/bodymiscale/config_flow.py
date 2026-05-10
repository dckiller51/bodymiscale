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
from homeassistant.util import slugify

from .const import (
    CALCULATION_MODE_OPTIONS,
    CONF_BIRTHDAY,
    CONF_CALCULATION_MODE,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_IMPEDANCE_MODE,
    CONF_INITIAL_WEIGHT,
    CONF_NEAREST_TOLERANCE,
    CONF_NOTIFY_DEVICE_ID,
    CONF_NOTIFY_WEIGHT_MAX,
    CONF_NOTIFY_WEIGHT_MIN,
    CONF_PROFILE_ID,
    CONF_PROFILE_METHOD,
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_IMPEDANCE_HIGH,
    CONF_SENSOR_IMPEDANCE_LOW,
    CONF_SENSOR_PROFILE_ID,
    CONF_SENSOR_WEIGHT,
    CONF_WEIGHT_MAX,
    CONF_WEIGHT_MIN,
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
    PROFILE_METHOD_ID,
    PROFILE_METHOD_NEAREST,
    PROFILE_METHOD_NONE,
    PROFILE_METHOD_NOTIFY,
    PROFILE_METHOD_OPTIONS,
    PROFILE_METHOD_WEIGHT,
)
from .models import Gender

# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


@callback
def _get_user_schema(
    defaults: dict[str, Any] | MappingProxyType[str, Any],
) -> vol.Schema:
    """Step 1 (config only): identity — name, birthday, gender."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME)): str,
            vol.Required(
                CONF_BIRTHDAY,
                description={"suggested_value": defaults.get(CONF_BIRTHDAY)},
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.DATE)
            ),
            vol.Required(
                CONF_GENDER,
                default=defaults.get(CONF_GENDER),
            ): vol.In({gender: gender.value for gender in Gender}),
        }
    )


@callback
def _get_modes_schema(
    defaults: dict[str, Any] | MappingProxyType[str, Any],
) -> vol.Schema:
    """Step 2: height, calculation mode, impedance mode, profile method."""
    return vol.Schema(
        {
            vol.Required(
                CONF_HEIGHT,
                description={"suggested_value": defaults.get(CONF_HEIGHT)},
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=0,
                    max=500,
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
                CONF_PROFILE_METHOD,
                default=defaults.get(CONF_PROFILE_METHOD, PROFILE_METHOD_NONE),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=PROFILE_METHOD_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="profile_method",
                )
            ),
        }
    )


def _get_sensors_schema(
    impedance_mode: str,
    profile_method: str,
    defaults: dict[str, Any],
) -> vol.Schema:
    """Step 3: sensor selectors — dynamic based on impedance & profile modes."""
    fields: dict = {
        vol.Required(
            CONF_SENSOR_WEIGHT,
            description={"suggested_value": defaults.get(CONF_SENSOR_WEIGHT)},
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number", "number"])
        ),
    }

    if impedance_mode == IMPEDANCE_MODE_STANDARD:
        fields[
            vol.Required(
                CONF_SENSOR_IMPEDANCE,
                description={"suggested_value": defaults.get(CONF_SENSOR_IMPEDANCE)},
            )
        ] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number", "number"])
        )

    elif impedance_mode == IMPEDANCE_MODE_DUAL:
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

    if profile_method == PROFILE_METHOD_ID:
        fields[
            vol.Required(
                CONF_SENSOR_PROFILE_ID,
                description={"suggested_value": defaults.get(CONF_SENSOR_PROFILE_ID)},
            )
        ] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["sensor", "input_number", "number"])
        )

    return vol.Schema(fields)


def _get_profile_schema(method: str, defaults: dict[str, Any]) -> vol.Schema | None:
    """Step 4 (conditional): profile-specific configuration."""
    if method == PROFILE_METHOD_NONE:
        return None

    if method == PROFILE_METHOD_ID:
        return vol.Schema(
            {
                vol.Required(
                    CONF_PROFILE_ID,
                    description={"suggested_value": defaults.get(CONF_PROFILE_ID)},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode=selector.NumberSelectorMode.BOX,
                        min=CONSTRAINT_PROFILE_ID_MIN,
                        max=CONSTRAINT_PROFILE_ID_MAX,
                        step=1,
                    )
                ),
            }
        )

    if method == PROFILE_METHOD_WEIGHT:
        return vol.Schema(
            {
                vol.Required(
                    CONF_WEIGHT_MIN,
                    description={"suggested_value": defaults.get(CONF_WEIGHT_MIN)},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode=selector.NumberSelectorMode.BOX,
                        min=0,
                        max=999,
                        step=0.01,
                        unit_of_measurement="kg",
                    )
                ),
                vol.Required(
                    CONF_WEIGHT_MAX,
                    description={"suggested_value": defaults.get(CONF_WEIGHT_MAX)},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode=selector.NumberSelectorMode.BOX,
                        min=0,
                        max=999,
                        step=0.01,
                        unit_of_measurement="kg",
                    )
                ),
            }
        )

    if method == PROFILE_METHOD_NEAREST:
        return vol.Schema(
            {
                vol.Required(
                    CONF_INITIAL_WEIGHT,
                    description={"suggested_value": defaults.get(CONF_INITIAL_WEIGHT)},
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode=selector.NumberSelectorMode.BOX,
                        min=CONSTRAINT_WEIGHT_MIN,
                        max=CONSTRAINT_WEIGHT_MAX,
                        step=0.1,
                        unit_of_measurement="kg",
                    )
                ),
                vol.Required(
                    CONF_NEAREST_TOLERANCE,
                    description={
                        "suggested_value": defaults.get(CONF_NEAREST_TOLERANCE, 5)
                    },
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode=selector.NumberSelectorMode.BOX,
                        min=0,
                        max=99,
                        step=1,
                        unit_of_measurement="kg",
                    )
                ),
            }
        )

    if method == PROFILE_METHOD_NOTIFY:
        return vol.Schema(
            {
                vol.Required(
                    CONF_NOTIFY_DEVICE_ID,
                    description={
                        "suggested_value": defaults.get(CONF_NOTIFY_DEVICE_ID)
                    },
                ): selector.DeviceSelector(
                    selector.DeviceSelectorConfig(integration="mobile_app")
                ),
                vol.Optional(
                    CONF_NOTIFY_WEIGHT_MIN,
                    description={
                        "suggested_value": defaults.get(CONF_NOTIFY_WEIGHT_MIN)
                    },
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode=selector.NumberSelectorMode.BOX,
                        min=0,
                        max=999,
                        step=0.1,
                        unit_of_measurement="kg",
                    )
                ),
                vol.Optional(
                    CONF_NOTIFY_WEIGHT_MAX,
                    description={
                        "suggested_value": defaults.get(CONF_NOTIFY_WEIGHT_MAX)
                    },
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode=selector.NumberSelectorMode.BOX,
                        min=0,
                        max=999,
                        step=0.1,
                        unit_of_measurement="kg",
                    )
                ),
            }
        )

    return None


def _validate_weight_range(
    weight_min: float,
    weight_max: float,
    existing_ranges: list[tuple[float, float]],
) -> str | None:
    """Validate the weight range and detect overlaps with existing entries."""
    if weight_min >= weight_max:
        return "weight_range_invalid"

    for r_min, r_max in existing_ranges:
        if weight_min < r_max and r_min < weight_max:
            return "weight_range_overlap"

    return None


# Keys that belong exclusively to each profile method.
_METHOD_KEYS: dict[str, list[str]] = {
    PROFILE_METHOD_ID: [CONF_SENSOR_PROFILE_ID, CONF_PROFILE_ID],
    PROFILE_METHOD_WEIGHT: [CONF_WEIGHT_MIN, CONF_WEIGHT_MAX],
    PROFILE_METHOD_NEAREST: [CONF_INITIAL_WEIGHT, CONF_NEAREST_TOLERANCE],
    PROFILE_METHOD_NOTIFY: [
        CONF_NOTIFY_DEVICE_ID,
        CONF_NOTIFY_WEIGHT_MIN,
        CONF_NOTIFY_WEIGHT_MAX,
    ],
    PROFILE_METHOD_NONE: [],
}

_IMPEDANCE_KEYS: dict[str, list[str]] = {
    IMPEDANCE_MODE_STANDARD: [CONF_SENSOR_IMPEDANCE],
    IMPEDANCE_MODE_DUAL: [CONF_SENSOR_IMPEDANCE_LOW, CONF_SENSOR_IMPEDANCE_HIGH],
    IMPEDANCE_MODE_NONE: [],
}


def _purge_other_method_keys(data: dict, keep_method: str) -> None:
    """Remove config keys that belong to profile methods other than *keep_method*."""
    for method, keys in _METHOD_KEYS.items():
        if method != keep_method:
            for key in keys:
                data.pop(key, None)


def _purge_impedance_keys(data: dict, keep_mode: str) -> None:
    """Remove config keys that belong to impedance modes other than *keep_mode*."""
    for mode, keys in _IMPEDANCE_KEYS.items():
        if mode != keep_mode:
            for key in keys:
                data.pop(key, None)


# ---------------------------------------------------------------------------
# Config flow
# ---------------------------------------------------------------------------


class BodyMiScaleFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for bodymiscale."""

    VERSION = 4

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

    # ── Step 1: identity (name, birthday, gender) ─────────────────────────

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
                name_input = user_input[CONF_NAME].strip()
                name_slug = slugify(name_input)

                existing_slugs = [
                    slugify(entry.data.get(CONF_NAME, ""))
                    for entry in self._async_current_entries(include_ignore=False)
                ]

                if name_slug in existing_slugs:
                    errors[CONF_NAME] = "name_already_used"

            if not errors:
                await self.async_set_unique_id(name_slug)
                self._abort_if_unique_id_configured()

                self._data = {**user_input, CONF_NAME: name_input}
                return await self.async_step_modes()

        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=_get_user_schema(self._data),
        )

    # ── Step 2: modes (height, calc, impedance, profile) ──────────────────

    async def async_step_modes(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the async_step_modes step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            h = user_input[CONF_HEIGHT]
            if h > CONSTRAINT_HEIGHT_MAX:
                errors[CONF_HEIGHT] = "height_limit"
            elif h < CONSTRAINT_HEIGHT_MIN:
                errors[CONF_HEIGHT] = "height_low"

            if not errors:
                self._data.update(user_input)
                profile_method = user_input.get(
                    CONF_PROFILE_METHOD, PROFILE_METHOD_NONE
                )
                _purge_other_method_keys(self._data, profile_method)
                impedance_mode = user_input.get(
                    CONF_IMPEDANCE_MODE, IMPEDANCE_MODE_NONE
                )
                _purge_impedance_keys(self._data, impedance_mode)
                return await self.async_step_sensors()

        return self.async_show_form(
            step_id="modes",
            errors=errors,
            data_schema=_get_modes_schema(self._data),
        )

    # ── Step 3: sensors (weight, impedance, profile sensor) ───────────────

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle sensors selection step."""
        if user_input is not None:
            self._data.update(user_input)
            profile_method = self._data.get(CONF_PROFILE_METHOD, PROFILE_METHOD_NONE)
            if profile_method != PROFILE_METHOD_NONE:
                return await self.async_step_profile()
            return self._create_entry()

        impedance_mode = self._data.get(CONF_IMPEDANCE_MODE, IMPEDANCE_MODE_NONE)
        profile_method = self._data.get(CONF_PROFILE_METHOD, PROFILE_METHOD_NONE)
        return self.async_show_form(
            step_id="sensors",
            data_schema=_get_sensors_schema(impedance_mode, profile_method, self._data),
        )

    # ── Step 4: profile-specific configuration ────────────────────────────

    async def async_step_profile(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle profile configuration step."""
        errors: dict[str, str] = {}
        method = self._data.get(CONF_PROFILE_METHOD, PROFILE_METHOD_NONE)
        schema = _get_profile_schema(method, self._data)

        if schema is None:
            return self._create_entry()

        if user_input is not None:
            if method == PROFILE_METHOD_WEIGHT:
                w_min = user_input.get(CONF_WEIGHT_MIN)
                w_max = user_input.get(CONF_WEIGHT_MAX)
                if w_min is None or w_max is None:
                    errors["base"] = "weight_range_invalid"
                else:
                    if float(w_min) < CONSTRAINT_WEIGHT_MIN:
                        errors[CONF_WEIGHT_MIN] = "weight_low"
                    elif float(w_min) > CONSTRAINT_WEIGHT_MAX:
                        errors[CONF_WEIGHT_MIN] = "weight_limit"
                    if float(w_max) < CONSTRAINT_WEIGHT_MIN:
                        errors[CONF_WEIGHT_MAX] = "weight_low"
                    elif float(w_max) > CONSTRAINT_WEIGHT_MAX:
                        errors[CONF_WEIGHT_MAX] = "weight_limit"
                    if not errors:
                        existing = self._get_existing_weight_ranges()
                        err = _validate_weight_range(
                            float(w_min), float(w_max), existing
                        )
                        if err:
                            errors["base"] = err

            elif method == PROFILE_METHOD_NEAREST:
                w = user_input.get(CONF_INITIAL_WEIGHT)
                tolerance = user_input.get(CONF_NEAREST_TOLERANCE)
                if w is None:
                    errors[CONF_INITIAL_WEIGHT] = "weight_range_invalid"
                else:
                    try:
                        value = float(w)
                        if value < CONSTRAINT_WEIGHT_MIN:
                            errors[CONF_INITIAL_WEIGHT] = "weight_low"
                        elif value > CONSTRAINT_WEIGHT_MAX:
                            errors[CONF_INITIAL_WEIGHT] = "weight_limit"
                    except TypeError, ValueError:
                        errors[CONF_INITIAL_WEIGHT] = "weight_range_invalid"
                if tolerance is None:
                    errors[CONF_NEAREST_TOLERANCE] = "weight_range_invalid"
                else:
                    try:
                        tol_value = float(tolerance)
                        if tol_value < 0:
                            errors[CONF_NEAREST_TOLERANCE] = "weight_low"
                        elif tol_value > 99:
                            errors[CONF_NEAREST_TOLERANCE] = "weight_limit"
                    except TypeError, ValueError:
                        errors[CONF_NEAREST_TOLERANCE] = "weight_range_invalid"

            elif method == PROFILE_METHOD_NOTIFY:
                w_min = user_input.get(CONF_NOTIFY_WEIGHT_MIN)
                w_max = user_input.get(CONF_NOTIFY_WEIGHT_MAX)
                if w_min is not None:
                    if float(w_min) < CONSTRAINT_WEIGHT_MIN:
                        errors[CONF_NOTIFY_WEIGHT_MIN] = "weight_low"
                    elif float(w_min) > CONSTRAINT_WEIGHT_MAX:
                        errors[CONF_NOTIFY_WEIGHT_MIN] = "weight_limit"
                if w_max is not None:
                    if float(w_max) < CONSTRAINT_WEIGHT_MIN:
                        errors[CONF_NOTIFY_WEIGHT_MAX] = "weight_low"
                    elif float(w_max) > CONSTRAINT_WEIGHT_MAX:
                        errors[CONF_NOTIFY_WEIGHT_MAX] = "weight_limit"
                if (
                    not errors
                    and w_min is not None
                    and w_max is not None
                    and float(w_min) >= float(w_max)
                ):
                    errors["base"] = "weight_range_invalid"

            if not errors:
                self._data.update(user_input)
                return self._create_entry()

        return self.async_show_form(
            step_id="profile",
            errors=errors,
            data_schema=schema,
        )

    # ── Helpers ───────────────────────────────────────────────────────────

    def _create_entry(self) -> ConfigFlowResult:
        """Create the config entry."""
        return self.async_create_entry(
            title=self._data[CONF_NAME],
            data=self._data,
            options=self._data,
        )

    def _get_existing_weight_ranges(self) -> list[tuple[float, float]]:
        """Return weight ranges already configured in other entries."""
        ranges = []
        for entry in self._async_current_entries():
            opts = dict(entry.data) | dict(entry.options)
            if opts.get(CONF_PROFILE_METHOD) == PROFILE_METHOD_WEIGHT:
                w_min = opts.get(CONF_WEIGHT_MIN)
                w_max = opts.get(CONF_WEIGHT_MAX)
                if w_min is not None and w_max is not None:
                    ranges.append((float(w_min), float(w_max)))
        return ranges


# ---------------------------------------------------------------------------
# Options flow (reconfiguration — no name/birthday/gender)
# ---------------------------------------------------------------------------


class BodyMiScaleOptionsFlowHandler(OptionsFlow):
    """Options flow for bodymiscale."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry
        self._data = dict(config_entry.data) | dict(config_entry.options)
        # Silently purge last_measurement_time — managed internally since 2026.5.0
        self._data.pop("last_measurement_time", None)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle options flow init step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            h = user_input[CONF_HEIGHT]
            if h > CONSTRAINT_HEIGHT_MAX:
                errors[CONF_HEIGHT] = "height_limit"
            elif h < CONSTRAINT_HEIGHT_MIN:
                errors[CONF_HEIGHT] = "height_low"

            if not errors:
                self._data.update(user_input)
                profile_method = user_input.get(
                    CONF_PROFILE_METHOD, PROFILE_METHOD_NONE
                )
                _purge_other_method_keys(self._data, profile_method)
                impedance_mode = user_input.get(
                    CONF_IMPEDANCE_MODE, IMPEDANCE_MODE_NONE
                )
                _purge_impedance_keys(self._data, impedance_mode)
                return await self.async_step_sensors()

        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=_get_modes_schema(self._data),
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle sensors selection step."""
        if user_input is not None:
            self._data.update(user_input)
            profile_method = self._data.get(CONF_PROFILE_METHOD, PROFILE_METHOD_NONE)
            if profile_method != PROFILE_METHOD_NONE:
                return await self.async_step_profile()
            return self.async_create_entry(data=self._data)

        impedance_mode = self._data.get(CONF_IMPEDANCE_MODE, IMPEDANCE_MODE_NONE)
        profile_method = self._data.get(CONF_PROFILE_METHOD, PROFILE_METHOD_NONE)
        return self.async_show_form(
            step_id="sensors",
            data_schema=_get_sensors_schema(impedance_mode, profile_method, self._data),
        )

    async def async_step_profile(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle profile configuration step."""
        errors: dict[str, str] = {}
        method = self._data.get(CONF_PROFILE_METHOD, PROFILE_METHOD_NONE)
        schema = _get_profile_schema(method, self._data)

        if schema is None:
            return self.async_create_entry(data=self._data)

        if user_input is not None:
            if method == PROFILE_METHOD_WEIGHT:
                w_min = user_input.get(CONF_WEIGHT_MIN)
                w_max = user_input.get(CONF_WEIGHT_MAX)
                if w_min is None or w_max is None:
                    errors["base"] = "weight_range_invalid"
                else:
                    if float(w_min) < CONSTRAINT_WEIGHT_MIN:
                        errors[CONF_WEIGHT_MIN] = "weight_low"
                    elif float(w_min) > CONSTRAINT_WEIGHT_MAX:
                        errors[CONF_WEIGHT_MIN] = "weight_limit"
                    if float(w_max) < CONSTRAINT_WEIGHT_MIN:
                        errors[CONF_WEIGHT_MAX] = "weight_low"
                    elif float(w_max) > CONSTRAINT_WEIGHT_MAX:
                        errors[CONF_WEIGHT_MAX] = "weight_limit"
                    if not errors:
                        existing = self._get_other_weight_ranges()
                        err = _validate_weight_range(
                            float(w_min), float(w_max), existing
                        )
                        if err:
                            errors["base"] = err

            elif method == PROFILE_METHOD_NEAREST:
                w = user_input.get(CONF_INITIAL_WEIGHT)
                tolerance = user_input.get(CONF_NEAREST_TOLERANCE)
                if w is None:
                    errors[CONF_INITIAL_WEIGHT] = "weight_range_invalid"
                else:
                    try:
                        value = float(w)
                        if value < CONSTRAINT_WEIGHT_MIN:
                            errors[CONF_INITIAL_WEIGHT] = "weight_low"
                        elif value > CONSTRAINT_WEIGHT_MAX:
                            errors[CONF_INITIAL_WEIGHT] = "weight_limit"
                    except TypeError, ValueError:
                        errors[CONF_INITIAL_WEIGHT] = "weight_range_invalid"
                if tolerance is None:
                    errors[CONF_NEAREST_TOLERANCE] = "weight_range_invalid"
                else:
                    try:
                        tol_value = float(tolerance)
                        if tol_value < 0:
                            errors[CONF_NEAREST_TOLERANCE] = "weight_low"
                        elif tol_value > 99:
                            errors[CONF_NEAREST_TOLERANCE] = "weight_limit"
                    except TypeError, ValueError:
                        errors[CONF_NEAREST_TOLERANCE] = "weight_range_invalid"

            elif method == PROFILE_METHOD_NOTIFY:
                w_min = user_input.get(CONF_NOTIFY_WEIGHT_MIN)
                w_max = user_input.get(CONF_NOTIFY_WEIGHT_MAX)
                if w_min is not None:
                    if float(w_min) < CONSTRAINT_WEIGHT_MIN:
                        errors[CONF_NOTIFY_WEIGHT_MIN] = "weight_low"
                    elif float(w_min) > CONSTRAINT_WEIGHT_MAX:
                        errors[CONF_NOTIFY_WEIGHT_MIN] = "weight_limit"
                if w_max is not None:
                    if float(w_max) < CONSTRAINT_WEIGHT_MIN:
                        errors[CONF_NOTIFY_WEIGHT_MAX] = "weight_low"
                    elif float(w_max) > CONSTRAINT_WEIGHT_MAX:
                        errors[CONF_NOTIFY_WEIGHT_MAX] = "weight_limit"
                if (
                    not errors
                    and w_min is not None
                    and w_max is not None
                    and float(w_min) >= float(w_max)
                ):
                    errors["base"] = "weight_range_invalid"

            if not errors:
                self._data.update(user_input)
                return self.async_create_entry(data=self._data)

        return self.async_show_form(
            step_id="profile",
            errors=errors,
            data_schema=schema,
        )

    def _get_other_weight_ranges(self) -> list[tuple[float, float]]:
        """Return weight ranges from other entries."""
        current_id = self._config_entry.entry_id
        ranges = []
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.entry_id == current_id:
                continue
            opts = dict(entry.data) | dict(entry.options)
            if opts.get(CONF_PROFILE_METHOD) == PROFILE_METHOD_WEIGHT:
                w_min = opts.get(CONF_WEIGHT_MIN)
                w_max = opts.get(CONF_WEIGHT_MAX)
                if w_min is not None and w_max is not None:
                    ranges.append((float(w_min), float(w_max)))
        return ranges

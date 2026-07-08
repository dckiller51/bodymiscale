"""Tests for the bodymiscale config flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bodymiscale.const import (
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
    DOMAIN,
    IMPEDANCE_MODE_DUAL,
    IMPEDANCE_MODE_NONE,
    IMPEDANCE_MODE_STANDARD,
    PROFILE_METHOD_ID,
    PROFILE_METHOD_NEAREST,
    PROFILE_METHOD_NONE,
    PROFILE_METHOD_NOTIFY,
    PROFILE_METHOD_WEIGHT,
)
from custom_components.bodymiscale.models import Gender

# ---------------------------------------------------------------------------
# Shared step data helpers
# ---------------------------------------------------------------------------

USER_STEP = {
    "name": "Alice",
    CONF_BIRTHDAY: "1990-01-15",
    CONF_GENDER: Gender.FEMALE,
}

MODES_STEP_NONE = {
    CONF_HEIGHT: 165.0,
    CONF_CALCULATION_MODE: "xiaomi",
    CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
    CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
}

SENSORS_STEP_NONE = {
    CONF_SENSOR_WEIGHT: "sensor.weight",
}


# ===========================================================================
# Config Flow — happy paths
# ===========================================================================


async def test_flow_user_step_shows_form(hass: HomeAssistant) -> None:
    """Step 'user' must show a form when called without input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_flow_full_no_impedance_no_profile(hass: HomeAssistant) -> None:
    """Complete flow: impedance=none, profile_method=none → CREATE_ENTRY."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Step 1 - user
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_STEP
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "modes"

    # Step 2 - modes
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], MODES_STEP_NONE
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sensors"

    # Step 3 - sensors
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], SENSORS_STEP_NONE
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Alice"
    assert result["data"][CONF_SENSOR_WEIGHT] == "sensor.weight"


async def test_flow_with_standard_impedance(hass: HomeAssistant) -> None:
    """Complete flow: impedance=standard adds one impedance sensor field."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_STEP
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HEIGHT: 175.0,
            CONF_CALCULATION_MODE: "science",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_STANDARD,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
        },
    )
    assert result["step_id"] == "sensors"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SENSOR_WEIGHT: "sensor.weight",
            CONF_SENSOR_IMPEDANCE: "sensor.impedance",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SENSOR_IMPEDANCE] == "sensor.impedance"


async def test_flow_with_dual_impedance(hass: HomeAssistant) -> None:
    """Complete flow: impedance=dual adds two impedance sensor fields."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_STEP
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HEIGHT: 175.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_DUAL,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
        },
    )
    assert result["step_id"] == "sensors"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SENSOR_WEIGHT: "sensor.weight",
            CONF_SENSOR_IMPEDANCE_LOW: "sensor.impedance_low",
            CONF_SENSOR_IMPEDANCE_HIGH: "sensor.impedance_high",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SENSOR_IMPEDANCE_LOW] == "sensor.impedance_low"
    assert result["data"][CONF_SENSOR_IMPEDANCE_HIGH] == "sensor.impedance_high"


async def test_flow_profile_method_id(hass: HomeAssistant) -> None:
    """Complete flow: profile_method=id → step 'profile' with profile_id."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_STEP
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HEIGHT: 165.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_ID,
        },
    )
    assert result["step_id"] == "sensors"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SENSOR_WEIGHT: "sensor.weight",
            CONF_SENSOR_PROFILE_ID: "sensor.profile_id",
        },
    )
    assert result["step_id"] == "profile"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PROFILE_ID: 1.0},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PROFILE_ID] == 1.0


async def test_flow_profile_method_weight(hass: HomeAssistant) -> None:
    """Complete flow: profile_method=weight → step 'profile' with weight range."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_STEP
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HEIGHT: 165.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_WEIGHT,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], SENSORS_STEP_NONE
    )
    assert result["step_id"] == "profile"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_WEIGHT_MIN: 50.0, CONF_WEIGHT_MAX: 80.0},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_WEIGHT_MIN] == 50.0
    assert result["data"][CONF_WEIGHT_MAX] == 80.0


async def test_flow_profile_method_nearest(hass: HomeAssistant) -> None:
    """Complete flow: profile_method=nearest → step 'profile' with initial weight and tolerance."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_STEP
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HEIGHT: 165.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NEAREST,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], SENSORS_STEP_NONE
    )
    assert result["step_id"] == "profile"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_INITIAL_WEIGHT: 72.5, CONF_NEAREST_TOLERANCE: 5.0},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_INITIAL_WEIGHT] == 72.5
    assert result["data"][CONF_NEAREST_TOLERANCE] == 5.0


async def test_flow_profile_method_notify(hass: HomeAssistant) -> None:
    """Complete flow: profile_method=notify → step 'profile' with device + optional weight."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_STEP
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HEIGHT: 165.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NOTIFY,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], SENSORS_STEP_NONE
    )
    assert result["step_id"] == "profile"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NOTIFY_DEVICE_ID: "device_abc123",
            CONF_NOTIFY_WEIGHT_MIN: 50.0,
            CONF_NOTIFY_WEIGHT_MAX: 80.0,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_NOTIFY_DEVICE_ID] == "device_abc123"


# ===========================================================================
# Config Flow — step 1 (user) validation errors
# ===========================================================================


async def test_flow_user_invalid_date(hass: HomeAssistant) -> None:
    """Invalid birthday date → error 'invalid_date' on CONF_BIRTHDAY."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Alice",
            CONF_BIRTHDAY: "not-a-date",
            CONF_GENDER: Gender.FEMALE,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"][CONF_BIRTHDAY] == "invalid_date"


async def test_flow_user_duplicate_name(hass: HomeAssistant) -> None:
    """Duplicate name (same slug) → error 'name_already_used'."""
    # Create a first entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Alice",
        unique_id="alice",
        data={"name": "Alice"},
        version=4,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Alice",  # same slug
            CONF_BIRTHDAY: "1990-01-15",
            CONF_GENDER: Gender.FEMALE,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"]["name"] == "name_already_used"


# ===========================================================================
# Config Flow — step 2 (modes) validation errors
# ===========================================================================


async def test_flow_modes_height_too_high(hass: HomeAssistant) -> None:
    """Height above max → error 'height_limit'."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_STEP
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HEIGHT: 300.0,  # way above max
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "modes"
    assert result["errors"][CONF_HEIGHT] == "height_limit"


async def test_flow_modes_height_too_low(hass: HomeAssistant) -> None:
    """Height below min → error 'height_low'."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_STEP
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HEIGHT: 0.1,  # below min
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "modes"
    assert result["errors"][CONF_HEIGHT] == "height_low"


# ===========================================================================
# Config Flow — step 4 (profile) validation errors
# ===========================================================================


async def _reach_profile_step(hass: HomeAssistant, profile_method: str) -> dict:
    """Run steps 1-3 and return the result at the profile step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_STEP
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HEIGHT: 165.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: profile_method,
        },
    )
    sensors = {CONF_SENSOR_WEIGHT: "sensor.weight"}
    if profile_method == PROFILE_METHOD_ID:
        sensors[CONF_SENSOR_PROFILE_ID] = "sensor.profile_id"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], sensors)
    assert result["step_id"] == "profile"
    return result


async def test_flow_profile_weight_min_too_low(hass: HomeAssistant) -> None:
    """Weight min below constraint → error 'weight_low'."""
    result = await _reach_profile_step(hass, PROFILE_METHOD_WEIGHT)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_WEIGHT_MIN: 0.0, CONF_WEIGHT_MAX: 80.0},
    )
    assert result["type"] == FlowResultType.FORM
    assert CONF_WEIGHT_MIN in result["errors"] or "base" in result["errors"]


async def test_flow_profile_weight_range_invalid(hass: HomeAssistant) -> None:
    """Weight min >= weight max → error 'weight_range_invalid'."""
    result = await _reach_profile_step(hass, PROFILE_METHOD_WEIGHT)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_WEIGHT_MIN: 80.0, CONF_WEIGHT_MAX: 50.0},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"].get("base") == "weight_range_invalid"


async def test_flow_profile_weight_range_overlap(hass: HomeAssistant) -> None:
    """Overlapping weight range with existing entry → error 'weight_range_overlap'."""
    # Create an existing entry that uses 50-80 kg
    existing = MockConfigEntry(
        domain=DOMAIN,
        title="Bob",
        unique_id="bob",
        data={
            "name": "Bob",
            CONF_BIRTHDAY: "1985-06-20",
            CONF_GENDER: Gender.MALE,
            CONF_HEIGHT: 180.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_WEIGHT,
            CONF_SENSOR_WEIGHT: "sensor.weight",
            CONF_WEIGHT_MIN: 50.0,
            CONF_WEIGHT_MAX: 80.0,
        },
        options={
            CONF_PROFILE_METHOD: PROFILE_METHOD_WEIGHT,
            CONF_WEIGHT_MIN: 50.0,
            CONF_WEIGHT_MAX: 80.0,
        },
        version=4,
    )
    existing.add_to_hass(hass)

    result = await _reach_profile_step(hass, PROFILE_METHOD_WEIGHT)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_WEIGHT_MIN: 60.0, CONF_WEIGHT_MAX: 90.0},  # overlaps 50-80
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"].get("base") == "weight_range_overlap"


async def test_flow_profile_notify_weight_min_too_high(hass: HomeAssistant) -> None:
    """Notify weight_min above constraint → error 'weight_limit'."""
    result = await _reach_profile_step(hass, PROFILE_METHOD_NOTIFY)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NOTIFY_DEVICE_ID: "device_abc",
            CONF_NOTIFY_WEIGHT_MIN: 250.0,
            CONF_NOTIFY_WEIGHT_MAX: 80.0,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"].get(CONF_NOTIFY_WEIGHT_MIN) == "weight_limit"


async def test_flow_profile_notify_weight_range_invalid(hass: HomeAssistant) -> None:
    """Notify weight_min >= weight_max → error 'weight_range_invalid'."""
    result = await _reach_profile_step(hass, PROFILE_METHOD_NOTIFY)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NOTIFY_DEVICE_ID: "device_abc",
            CONF_NOTIFY_WEIGHT_MIN: 80.0,
            CONF_NOTIFY_WEIGHT_MAX: 50.0,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"].get("base") == "weight_range_invalid"


# ===========================================================================
# Options Flow — happy paths
# ===========================================================================


async def test_options_flow_shows_init_form(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Options flow init step must show a form."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_full_no_profile(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Options flow: change height, keep profile_method=none → CREATE_ENTRY."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_HEIGHT: 170.0,
            CONF_CALCULATION_MODE: "science",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
        },
    )
    assert result["step_id"] == "sensors"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_SENSOR_WEIGHT: "sensor.weight_new"},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HEIGHT] == 170.0
    assert result["data"][CONF_SENSOR_WEIGHT] == "sensor.weight_new"


async def test_options_flow_switch_to_weight_profile(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Options flow: switch to profile_method=weight → profile step."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_HEIGHT: 165.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_WEIGHT,
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_SENSOR_WEIGHT: "sensor.weight"},
    )
    assert result["step_id"] == "profile"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_WEIGHT_MIN: 55.0, CONF_WEIGHT_MAX: 75.0},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_WEIGHT_MIN] == 55.0


async def test_options_flow_with_standard_impedance(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Options flow: switch to impedance=standard."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_HEIGHT: 165.0,
            CONF_CALCULATION_MODE: "science",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_STANDARD,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SENSOR_WEIGHT: "sensor.weight",
            CONF_SENSOR_IMPEDANCE: "sensor.impedance",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SENSOR_IMPEDANCE] == "sensor.impedance"


# ===========================================================================
# Options Flow — validation errors
# ===========================================================================


async def test_options_flow_height_too_high(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Options flow: height too high → error 'height_limit'."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_HEIGHT: 300.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"][CONF_HEIGHT] == "height_limit"


async def test_options_flow_profile_weight_range_invalid(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Options flow profile step: weight_min >= weight_max → error."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_HEIGHT: 165.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_WEIGHT,
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_SENSOR_WEIGHT: "sensor.weight"},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_WEIGHT_MIN: 80.0, CONF_WEIGHT_MAX: 50.0},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"].get("base") == "weight_range_invalid"


# ===========================================================================
# _get_profile_schema — direct unit tests (unreachable-in-practice branches)
# ===========================================================================


def test_get_profile_schema_none_method_returns_none() -> None:
    """PROFILE_METHOD_NONE must yield no schema at all."""
    from custom_components.bodymiscale.config_flow import _get_profile_schema

    assert _get_profile_schema(PROFILE_METHOD_NONE, {}) is None


def test_get_profile_schema_unknown_method_returns_none() -> None:
    """An unrecognized method must fall through to None (defensive branch)."""
    from custom_components.bodymiscale.config_flow import _get_profile_schema

    assert _get_profile_schema("not_a_real_method", {}) is None


# ===========================================================================
# _validate_nearest — direct unit tests
# ===========================================================================


def test_validate_nearest_missing_weight() -> None:
    """A missing initial weight must set 'weight_range_invalid'."""
    from custom_components.bodymiscale.config_flow import _validate_nearest

    errors: dict[str, str] = {}
    _validate_nearest({CONF_NEAREST_TOLERANCE: 5}, errors)
    assert errors[CONF_INITIAL_WEIGHT] == "weight_range_invalid"


def test_validate_nearest_weight_too_low() -> None:
    """An initial weight below the constraint must set 'weight_low'."""
    from custom_components.bodymiscale.config_flow import _validate_nearest

    errors: dict[str, str] = {}
    _validate_nearest({CONF_INITIAL_WEIGHT: 0.0, CONF_NEAREST_TOLERANCE: 5}, errors)
    assert errors[CONF_INITIAL_WEIGHT] == "weight_low"


def test_validate_nearest_weight_too_high() -> None:
    """An initial weight above the constraint must set 'weight_limit'."""
    from custom_components.bodymiscale.config_flow import _validate_nearest

    errors: dict[str, str] = {}
    _validate_nearest({CONF_INITIAL_WEIGHT: 5000.0, CONF_NEAREST_TOLERANCE: 5}, errors)
    assert errors[CONF_INITIAL_WEIGHT] == "weight_limit"


def test_validate_nearest_weight_not_a_number() -> None:
    """A non-numeric initial weight must set 'weight_range_invalid'."""
    from custom_components.bodymiscale.config_flow import _validate_nearest

    errors: dict[str, str] = {}
    _validate_nearest(
        {CONF_INITIAL_WEIGHT: "not-a-number", CONF_NEAREST_TOLERANCE: 5}, errors
    )
    assert errors[CONF_INITIAL_WEIGHT] == "weight_range_invalid"


def test_validate_nearest_missing_tolerance() -> None:
    """A missing tolerance must set 'weight_range_invalid'."""
    from custom_components.bodymiscale.config_flow import _validate_nearest

    errors: dict[str, str] = {}
    _validate_nearest({CONF_INITIAL_WEIGHT: 65.0}, errors)
    assert errors[CONF_NEAREST_TOLERANCE] == "weight_range_invalid"


def test_validate_nearest_tolerance_too_low() -> None:
    """A negative tolerance must set 'weight_low'."""
    from custom_components.bodymiscale.config_flow import _validate_nearest

    errors: dict[str, str] = {}
    _validate_nearest({CONF_INITIAL_WEIGHT: 65.0, CONF_NEAREST_TOLERANCE: -1}, errors)
    assert errors[CONF_NEAREST_TOLERANCE] == "weight_low"


def test_validate_nearest_tolerance_too_high() -> None:
    """A tolerance above 99 must set 'weight_limit'."""
    from custom_components.bodymiscale.config_flow import _validate_nearest

    errors: dict[str, str] = {}
    _validate_nearest({CONF_INITIAL_WEIGHT: 65.0, CONF_NEAREST_TOLERANCE: 150}, errors)
    assert errors[CONF_NEAREST_TOLERANCE] == "weight_limit"


def test_validate_nearest_tolerance_not_a_number() -> None:
    """A non-numeric tolerance must set 'weight_range_invalid'."""
    from custom_components.bodymiscale.config_flow import _validate_nearest

    errors: dict[str, str] = {}
    _validate_nearest(
        {CONF_INITIAL_WEIGHT: 65.0, CONF_NEAREST_TOLERANCE: "nope"}, errors
    )
    assert errors[CONF_NEAREST_TOLERANCE] == "weight_range_invalid"


# ===========================================================================
# _validate_weight — direct unit tests
# ===========================================================================


def test_validate_weight_missing_min_or_max() -> None:
    """A missing weight_min or weight_max must set 'base' and stop early."""
    from custom_components.bodymiscale.config_flow import _validate_weight

    errors: dict[str, str] = {}
    _validate_weight({CONF_WEIGHT_MAX: 80.0}, errors, [])
    assert errors["base"] == "weight_range_invalid"


def test_validate_weight_min_too_high() -> None:
    """A weight_min above the constraint must set 'weight_limit'."""
    from custom_components.bodymiscale.config_flow import _validate_weight

    errors: dict[str, str] = {}
    _validate_weight({CONF_WEIGHT_MIN: 5000.0, CONF_WEIGHT_MAX: 5001.0}, errors, [])
    assert errors[CONF_WEIGHT_MIN] == "weight_limit"


def test_validate_weight_max_too_low() -> None:
    """A weight_max below the constraint must set 'weight_low'."""
    from custom_components.bodymiscale.config_flow import _validate_weight

    errors: dict[str, str] = {}
    _validate_weight({CONF_WEIGHT_MIN: -5.0, CONF_WEIGHT_MAX: 0.0}, errors, [])
    assert errors[CONF_WEIGHT_MAX] == "weight_low"


def test_validate_weight_max_too_high() -> None:
    """A weight_max above the constraint must set 'weight_limit'."""
    from custom_components.bodymiscale.config_flow import _validate_weight

    errors: dict[str, str] = {}
    _validate_weight({CONF_WEIGHT_MIN: 50.0, CONF_WEIGHT_MAX: 5000.0}, errors, [])
    assert errors[CONF_WEIGHT_MAX] == "weight_limit"


# ===========================================================================
# _validate_notify — direct unit tests
# ===========================================================================


def test_validate_notify_weight_min_too_low() -> None:
    """A notify weight_min below the constraint must set 'weight_low'."""
    from custom_components.bodymiscale.config_flow import _validate_notify

    errors: dict[str, str] = {}
    _validate_notify({CONF_NOTIFY_WEIGHT_MIN: -5.0}, errors)
    assert errors[CONF_NOTIFY_WEIGHT_MIN] == "weight_low"


def test_validate_notify_weight_max_too_low() -> None:
    """A notify weight_max below the constraint must set 'weight_low'."""
    from custom_components.bodymiscale.config_flow import _validate_notify

    errors: dict[str, str] = {}
    _validate_notify({CONF_NOTIFY_WEIGHT_MAX: -5.0}, errors)
    assert errors[CONF_NOTIFY_WEIGHT_MAX] == "weight_low"


def test_validate_notify_weight_max_too_high() -> None:
    """A notify weight_max above the constraint must set 'weight_limit'."""
    from custom_components.bodymiscale.config_flow import _validate_notify

    errors: dict[str, str] = {}
    _validate_notify({CONF_NOTIFY_WEIGHT_MAX: 5000.0}, errors)
    assert errors[CONF_NOTIFY_WEIGHT_MAX] == "weight_limit"


# ===========================================================================
# Config Flow — defensive "schema is None" branch at the profile step
# ===========================================================================


async def test_flow_profile_step_schema_none_creates_entry_directly(
    hass: HomeAssistant,
) -> None:
    """If _get_profile_schema unexpectedly returns None, entry is created directly."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_STEP
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HEIGHT: 165.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_ID,
        },
    )
    with patch(
        "custom_components.bodymiscale.config_flow._get_profile_schema",
        return_value=None,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_SENSOR_WEIGHT: "sensor.weight",
                CONF_SENSOR_PROFILE_ID: "sensor.profile_id",
            },
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY


# ===========================================================================
# Options Flow — additional branch coverage
# ===========================================================================


async def test_options_flow_height_too_low(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Options flow: height too low → error 'height_low'."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_HEIGHT: 0.1,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"][CONF_HEIGHT] == "height_low"


async def _reach_options_profile_step(
    hass: HomeAssistant, entry: MockConfigEntry, profile_method: str
) -> dict:
    """Run the options flow up to the profile step."""
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_HEIGHT: 165.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: profile_method,
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_SENSOR_WEIGHT: "sensor.weight"},
    )
    assert result["step_id"] == "profile"
    return result


async def test_options_flow_profile_nearest_weight_too_low(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Options flow profile step (NEAREST): weight below constraint → error."""
    result = await _reach_options_profile_step(
        hass, mock_config_entry, PROFILE_METHOD_NEAREST
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_INITIAL_WEIGHT: 0.0, CONF_NEAREST_TOLERANCE: 5},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"].get(CONF_INITIAL_WEIGHT) == "weight_low"


async def test_options_flow_profile_notify_weight_min_too_high(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Options flow profile step (NOTIFY): weight_min above constraint → error."""
    result = await _reach_options_profile_step(
        hass, mock_config_entry, PROFILE_METHOD_NOTIFY
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NOTIFY_DEVICE_ID: "device_abc",
            CONF_NOTIFY_WEIGHT_MIN: 250.0,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"].get(CONF_NOTIFY_WEIGHT_MIN) == "weight_limit"


async def test_options_flow_profile_step_schema_none_creates_entry_directly(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """If _get_profile_schema unexpectedly returns None, entry is created directly."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_HEIGHT: 165.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_ID,
        },
    )
    with patch(
        "custom_components.bodymiscale.config_flow._get_profile_schema",
        return_value=None,
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_SENSOR_WEIGHT: "sensor.weight",
                CONF_SENSOR_PROFILE_ID: "sensor.profile_id",
            },
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_options_flow_get_other_weight_ranges_detects_overlap(
    hass: HomeAssistant,
) -> None:
    """_get_other_weight_ranges must include other entries and flag overlap."""
    other = MockConfigEntry(
        domain=DOMAIN,
        title="Bob",
        unique_id="bob",
        data={
            "name": "Bob",
            CONF_BIRTHDAY: "1985-06-20",
            CONF_GENDER: Gender.MALE,
            CONF_HEIGHT: 180.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_WEIGHT,
            CONF_SENSOR_WEIGHT: "sensor.weight_bob",
            CONF_WEIGHT_MIN: 50.0,
            CONF_WEIGHT_MAX: 80.0,
        },
        options={
            CONF_PROFILE_METHOD: PROFILE_METHOD_WEIGHT,
            CONF_WEIGHT_MIN: 50.0,
            CONF_WEIGHT_MAX: 80.0,
        },
        version=4,
    )
    other.add_to_hass(hass)

    mine = MockConfigEntry(
        domain=DOMAIN,
        title="Alice",
        unique_id="alice",
        data={
            "name": "Alice",
            CONF_BIRTHDAY: "1990-01-15",
            CONF_GENDER: Gender.FEMALE,
            CONF_HEIGHT: 165.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
            CONF_SENSOR_WEIGHT: "sensor.weight_alice",
        },
        options={},
        version=4,
    )

    result = await _reach_options_profile_step(hass, mine, PROFILE_METHOD_WEIGHT)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_WEIGHT_MIN: 60.0, CONF_WEIGHT_MAX: 90.0},  # overlaps Bob's 50-80
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"].get("base") == "weight_range_overlap"


async def test_options_flow_get_other_weight_ranges_excludes_self(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The entry being edited must not be counted against itself for overlap."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        data={
            **mock_config_entry.data,
            CONF_PROFILE_METHOD: PROFILE_METHOD_WEIGHT,
            CONF_WEIGHT_MIN: 60.0,
            CONF_WEIGHT_MAX: 90.0,
        },
    )

    result = await _reach_options_profile_step(
        hass, mock_config_entry, PROFILE_METHOD_WEIGHT
    )
    # Same range as the entry's own pre-existing data — must NOT self-overlap.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_WEIGHT_MIN: 60.0, CONF_WEIGHT_MAX: 90.0},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY

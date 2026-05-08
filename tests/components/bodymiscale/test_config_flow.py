"""Tests for the bodymiscale config flow."""

from __future__ import annotations

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

"""Fixtures for bodymiscale tests."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bodymiscale.const import (
    CONF_BIRTHDAY,
    CONF_CALCULATION_MODE,
    CONF_GENDER,
    CONF_HEIGHT,
    CONF_IMPEDANCE_MODE,
    CONF_PROFILE_METHOD,
    CONF_SENSOR_WEIGHT,
    DOMAIN,
    IMPEDANCE_MODE_NONE,
    PROFILE_METHOD_NONE,
)
from custom_components.bodymiscale.models import Gender


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry (profile_method=none, impedance=none)."""
    return MockConfigEntry(
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
            CONF_SENSOR_WEIGHT: "sensor.weight",
        },
        options={
            "name": "Alice",
            CONF_BIRTHDAY: "1990-01-15",
            CONF_GENDER: Gender.FEMALE,
            CONF_HEIGHT: 165.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
            CONF_SENSOR_WEIGHT: "sensor.weight",
        },
        version=4,
    )

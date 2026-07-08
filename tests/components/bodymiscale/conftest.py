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
    CONF_SENSOR_IMPEDANCE,
    CONF_SENSOR_IMPEDANCE_HIGH,
    CONF_SENSOR_IMPEDANCE_LOW,
    CONF_SENSOR_WEIGHT,
    DOMAIN,
    IMPEDANCE_MODE_DUAL,
    IMPEDANCE_MODE_NONE,
    IMPEDANCE_MODE_STANDARD,
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


@pytest.fixture
def mock_config_entry_standard_impedance() -> MockConfigEntry:
    """Return a mock config entry with impedance_mode=standard."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Bob",
        unique_id="bob",
        data={
            "name": "Bob",
            CONF_BIRTHDAY: "1985-06-20",
            CONF_GENDER: Gender.MALE,
            CONF_HEIGHT: 180.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_STANDARD,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
            CONF_SENSOR_WEIGHT: "sensor.weight",
        },
        options={
            "name": "Bob",
            CONF_BIRTHDAY: "1985-06-20",
            CONF_GENDER: Gender.MALE,
            CONF_HEIGHT: 180.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_STANDARD,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
            CONF_SENSOR_WEIGHT: "sensor.weight",
            CONF_SENSOR_IMPEDANCE: "sensor.impedance",
        },
        version=4,
    )


@pytest.fixture
def mock_config_entry_dual_impedance() -> MockConfigEntry:
    """Return a mock config entry with impedance_mode=dual."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Carol",
        unique_id="carol",
        data={
            "name": "Carol",
            CONF_BIRTHDAY: "1992-03-10",
            CONF_GENDER: Gender.FEMALE,
            CONF_HEIGHT: 170.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_DUAL,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
            CONF_SENSOR_WEIGHT: "sensor.weight",
        },
        options={
            "name": "Carol",
            CONF_BIRTHDAY: "1992-03-10",
            CONF_GENDER: Gender.FEMALE,
            CONF_HEIGHT: 170.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_DUAL,
            CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
            CONF_SENSOR_WEIGHT: "sensor.weight",
            CONF_SENSOR_IMPEDANCE_LOW: "sensor.impedance_low",
            CONF_SENSOR_IMPEDANCE_HIGH: "sensor.impedance_high",
        },
        version=4,
    )


@pytest.fixture
def mock_config_entry_v1() -> MockConfigEntry:
    """Return a v1 config entry (pre-migration layout: everything in data)."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Dave",
        unique_id="dave",
        data={
            CONF_BIRTHDAY: "1988-11-02",
            CONF_GENDER: Gender.MALE,
            CONF_HEIGHT: 175.0,
            CONF_SENSOR_WEIGHT: "sensor.weight",
        },
        options={
            "name": "Dave",
        },
        version=1,
    )


@pytest.fixture
def mock_config_entry_v2() -> MockConfigEntry:
    """Return a v2 config entry with a standard impedance sensor configured."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Erin",
        unique_id="erin",
        data={
            "name": "Erin",
            CONF_BIRTHDAY: "1995-07-30",
            CONF_GENDER: Gender.FEMALE,
            CONF_SENSOR_IMPEDANCE: "sensor.impedance",
        },
        options={
            CONF_HEIGHT: 160.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_SENSOR_WEIGHT: "sensor.weight",
        },
        version=2,
    )


@pytest.fixture
def mock_config_entry_v3() -> MockConfigEntry:
    """Return a v3 config entry missing the profile method option."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Frank",
        unique_id="frank",
        data={
            "name": "Frank",
            CONF_BIRTHDAY: "1975-04-18",
            CONF_GENDER: Gender.MALE,
        },
        options={
            CONF_HEIGHT: 178.0,
            CONF_CALCULATION_MODE: "xiaomi",
            CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_NONE,
            CONF_SENSOR_WEIGHT: "sensor.weight",
        },
        version=3,
    )

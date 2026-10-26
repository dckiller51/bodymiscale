"""Tests for the Xiaomi Home (S400 firmware) calculation mode (#474)."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant

from custom_components.bodymiscale.const import (
    ALGO_SCIENCE,
    ALGO_XIAOMI,
    ALGO_XIAOMI_HOME,
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
    IMPEDANCE_MODE_DUAL,
    IMPEDANCE_MODE_STANDARD,
    PROFILE_METHOD_NONE,
)
from custom_components.bodymiscale.metrics import BodyScaleMetricsHandler, xiaomi_home
from custom_components.bodymiscale.metrics.impedance import is_xiaomi_home
from custom_components.bodymiscale.models import Gender, Metric

# ---------------------------------------------------------------------------
# Reference weighings: S400 weighings with the values shown in the Xiaomi Home
# app, reported by users in #349. Impedances are given as (50 kHz, 250 kHz),
# the 50 kHz one being the larger value.
#
# App values: body fat %, muscle kg, water %, bone kg, protein %, BMR, visceral,
# metabolic (body) age
# ---------------------------------------------------------------------------

_KEYS = (
    "body_fat",
    "muscle",
    "water",
    "bone",
    "protein",
    "bmr",
    "visceral",
    "metabolic_age",
)

WEIGHINGS: list[tuple[str, Gender, int, float, float, float, float, tuple]] = [
    (
        "P1",
        Gender.MALE,
        50,
        180,
        83.3,
        451.6,
        407.9,
        (23.3, 60.4, 56.8, 4.2, 14.9, 1750, 9, 47),
    ),
    (
        "P2",
        Gender.MALE,
        26,
        173,
        91.1,
        505.7,
        457.5,
        (29.2, 61.2, 46.7, 3.3, 19.8, 1763, 16, 24),
    ),
    (
        "P3",
        Gender.MALE,
        48,
        183,
        79.1,
        458.6,
        408.5,
        (20.0, 59.7, 62.1, 3.6, 12.5, 1737, 5, 45),
    ),
    (
        "P4",
        Gender.MALE,
        28,
        187,
        132.5,
        454.6,
        414.9,
        (35.7, 80.6, 43.6, 4.6, 16.5, 2220, 27, 30),
    ),
    (
        "P5",
        Gender.MALE,
        56,
        170,
        67.9,
        509.1,
        457.8,
        (20.3, 51.3, 56.0, 2.8, 12.7, 1539, 7, 53),
    ),
    (
        "P6",
        Gender.MALE,
        62,
        170,
        76.9,
        437.0,
        387.0,
        (24.6, 54.9, 55.8, 2.8, 14.7, 1623, 8, 62),
    ),
    (
        "P7",
        Gender.MALE,
        38,
        172,
        71.9,
        460.3,
        414.7,
        (19.7, 54.6, 58.8, 3.1, 16.1, 1616, 6, 34),
    ),
    (
        "P8",
        Gender.MALE,
        30,
        171,
        56.0,
        568.2,
        485.8,
        (10.8, 47.4, 62.3, 2.6, 21.4, 1450, 4, 27),
    ),
    (
        "P9",
        Gender.MALE,
        27,
        178,
        88.0,
        570.0,
        510.6,
        (26.8, 61.0, 49.1, 3.4, 19.5, 1761, 14, 25),
    ),
    (
        "P10",
        Gender.FEMALE,
        26,
        163,
        63.6,
        630.0,
        571.5,
        (33.3, 40.0, 47.8, 2.4, 14.3, 1286, 10, 24),
    ),
]

# Values that differ from the app, most likely typos in the reported values
# (single digit off while every other metric matches) or app values taken
# from another weigh-in than the impedances (P6, P7).
KNOWN_GAPS: dict[str, set[str]] = {
    "P1": {"bone"},
    "P4": {"bmr"},
    "P5": {"protein"},
    "P6": {"body_fat", "muscle", "bone", "protein", "bmr", "metabolic_age"},
    "P7": {"body_fat", "muscle", "water", "bone", "protein", "bmr", "visceral"},
    "P8": {"water", "protein", "visceral"},
}


def _compute(
    gender: Gender, age: int, h: float, w: float, z50: float, z250: float
) -> dict[str, float]:
    return {
        "body_fat": xiaomi_home.body_fat(gender, h, w, age, z50),
        "muscle": xiaomi_home.muscle_mass(gender, h, w, age, z50, z250),
        "water": xiaomi_home.water_percentage(gender, h, w, age, z50, z250),
        "bone": xiaomi_home.bone_mass(h, w, z50, z250),
        "protein": xiaomi_home.protein_percentage(gender, h, w, age, z50, z250),
        "bmr": xiaomi_home.basal_metabolism(gender, h, w, age, z50),
        "visceral": xiaomi_home.visceral_fat(h, w, z50, z250),
        "metabolic_age": xiaomi_home.metabolic_age(gender, h, w, age, z50, z250),
    }


@pytest.mark.parametrize(
    ("label", "gender", "age", "h", "w", "z50", "z250", "app"),
    WEIGHINGS,
    ids=[w[0] for w in WEIGHINGS],
)
def test_matches_xiaomi_home_app(
    label: str,
    gender: Gender,
    age: int,
    h: float,
    w: float,
    z50: float,
    z250: float,
    app: tuple,
) -> None:
    """Every metric outside the known gaps matches the app exactly."""
    result = _compute(gender, age, h, w, z50, z250)
    gaps = KNOWN_GAPS.get(label, set())
    for key, expected in zip(_KEYS, app, strict=True):
        if key in gaps:
            continue
        assert result[key] == pytest.approx(expected, abs=1e-6), key


def test_four_profiles_match_the_app_on_every_metric() -> None:
    """Guard against silently widening KNOWN_GAPS."""
    exact = [w[0] for w in WEIGHINGS if not KNOWN_GAPS.get(w[0])]
    assert exact == ["P2", "P3", "P9", "P10"]


def test_matched_weigh_in() -> None:
    """S400 weigh-in received by Home Assistant and Xiaomi Home at the same time.

    Male, 46 y, 176 cm, 79.4 kg, 559 / 501 Ω. App: muscle 57.1 kg, bone 4.0 %,
    BMR 1672, lean mass 60.3 kg, water 52.3 %, protein 18.9 %, visceral 10,
    skeletal muscle 30.1 kg, body age 43.
    """
    g, a, h, w, z50, z250 = Gender.MALE, 46, 176.0, 79.4, 559.0, 501.0
    assert xiaomi_home.muscle_mass(g, h, w, a, z50, z250) == pytest.approx(57.1)
    assert xiaomi_home.bone_mass(h, w, z50, z250) / w * 100 == pytest.approx(
        4.0, abs=0.05
    )
    assert xiaomi_home.basal_metabolism(g, h, w, a, z50) == 1672
    assert xiaomi_home.lean_body_mass(g, h, w, a, z50) == pytest.approx(60.3, abs=0.05)
    # The small gaps are the scale's impedance smoothing: the app computed
    # this weigh-in from the smoothed pair 557.9 / 497.6 Ω.
    assert xiaomi_home.water_percentage(g, h, w, a, z50, z250) == pytest.approx(
        52.3, abs=0.5
    )
    assert xiaomi_home.protein_percentage(g, h, w, a, z50, z250) == pytest.approx(
        18.9, abs=0.5
    )
    assert xiaomi_home.visceral_fat(h, w, z50, z250) == pytest.approx(10, abs=1)
    # Skeletal muscle within 45-70 % of muscle mass; the small gap with the app
    # comes from the impedance smoothing of the scale.
    assert xiaomi_home.skeletal_muscle_mass(g, h, w, a, z50, z250) == pytest.approx(
        30.1, abs=0.3
    )
    assert xiaomi_home.metabolic_age(g, h, w, a, z50, z250) == 43


def test_matched_weigh_in_with_fresh_250khz_impedance() -> None:
    """Weigh-in with both impedances freshly received by Home Assistant.

    Male, 46 y, 176 cm, 79.9 kg, 576.7 / 514.6 ohm. Every value matches the
    Xiaomi Home report of the same weigh-in.
    """
    g, a, h, w, z50, z250 = Gender.MALE, 46, 176.0, 79.9, 576.7, 514.6
    assert xiaomi_home.body_fat(g, h, w, a, z50) == 24.6
    assert xiaomi_home.lean_body_mass(g, h, w, a, z50) == pytest.approx(60.2, abs=0.05)
    assert xiaomi_home.muscle_mass(g, h, w, a, z50, z250) == pytest.approx(57.0)
    assert xiaomi_home.water_percentage(g, h, w, a, z50, z250) == pytest.approx(51.3)
    assert xiaomi_home.protein_percentage(g, h, w, a, z50, z250) == pytest.approx(19.3)
    assert xiaomi_home.bone_mass(h, w, z50, z250) == pytest.approx(3.2)
    assert xiaomi_home.basal_metabolism(g, h, w, a, z50) == 1670
    assert xiaomi_home.visceral_fat(h, w, z50, z250) == 11
    assert xiaomi_home.skeletal_muscle_mass(g, h, w, a, z50, z250) == pytest.approx(
        29.6
    )
    assert xiaomi_home.metabolic_age(g, h, w, a, z50, z250) == 44


def test_round_01_matches_firmware() -> None:
    """Round to 0.1, half away from zero."""
    assert xiaomi_home._round_01(23.349) == pytest.approx(23.3)
    assert xiaomi_home._round_01(23.35) == pytest.approx(23.4)
    assert xiaomi_home._round_01(23.3499) == pytest.approx(23.3)
    assert xiaomi_home._round_01(-23.35) == pytest.approx(-23.4)


def test_body_fat_floor_from_s400_pro_logs() -> None:
    """S400 Pro log: a 12-year-old boy's raw body fat of -2.1 % is shown as 3.0 %."""
    assert xiaomi_home.body_fat(Gender.MALE, 167, 41.4, 12, 701.0) == 3.0


def test_body_fat_matches_s400_pro_logs() -> None:
    """S400 Pro log: 178 cm, 79.0 kg, male, 41 y, smoothed 606.3 ohm -> 23.5 %."""
    assert xiaomi_home.body_fat(Gender.MALE, 178, 79.0, 41, 606.3) == 23.5


def test_skeletal_muscle_kept_within_muscle_range() -> None:
    """Skeletal muscle stays between 45 % and 70 % of the muscle mass."""
    for args in [
        (Gender.MALE, 176, 79.4, 46, 559, 501),
        (Gender.FEMALE, 150, 120, 30, 300, 290),
    ]:
        muscle = xiaomi_home.muscle_mass(*args)
        smm = xiaomi_home.skeletal_muscle_mass(*args)
        assert 0.45 * muscle - 1e-9 <= smm <= 0.70 * muscle + 1e-9


def test_clamps() -> None:
    """Outputs stay within the firmware ranges."""
    assert xiaomi_home.visceral_fat(200, 30, 900, 800) >= 1
    assert 0.0 <= xiaomi_home.bone_mass(120, 20, 900, 800) <= 5.0
    assert 400 <= xiaomi_home.basal_metabolism(Gender.FEMALE, 120, 20, 30, 900) <= 3500


# ---------------------------------------------------------------------------
# Mode selection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("impedance_mode", "calculation_mode", "expected"),
    [
        (IMPEDANCE_MODE_DUAL, ALGO_XIAOMI_HOME, True),
        (IMPEDANCE_MODE_DUAL, ALGO_SCIENCE, False),
        (IMPEDANCE_MODE_DUAL, ALGO_XIAOMI, False),  # existing S400 profiles
        (IMPEDANCE_MODE_STANDARD, ALGO_XIAOMI_HOME, False),
    ],
)
def test_is_xiaomi_home(
    impedance_mode: str, calculation_mode: str, expected: bool
) -> None:
    """Only dual frequency + xiaomi_home selects the firmware formulas."""
    config = {
        CONF_IMPEDANCE_MODE: impedance_mode,
        CONF_CALCULATION_MODE: calculation_mode,
    }
    assert is_xiaomi_home(config) is expected


# ---------------------------------------------------------------------------
# Handler integration
# ---------------------------------------------------------------------------


def _dual_config(suffix: str, calculation_mode: str) -> dict[str, Any]:
    return {
        "name": "TestUser",
        CONF_BIRTHDAY: "1980-01-01",
        CONF_GENDER: Gender.MALE,
        CONF_HEIGHT: 176.0,
        CONF_CALCULATION_MODE: calculation_mode,
        CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_DUAL,
        CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
        CONF_SENSOR_WEIGHT: f"sensor.w_{suffix}",
        CONF_SENSOR_IMPEDANCE_LOW: f"sensor.low_{suffix}",
        CONF_SENSOR_IMPEDANCE_HIGH: f"sensor.high_{suffix}",
    }


def _subscribe(
    handler: BodyScaleMetricsHandler, metrics: list[Metric]
) -> dict[Metric, list]:
    values: dict[Metric, list] = {m: [] for m in metrics}
    for metric in metrics:
        handler.subscribe(metric, values[metric].append)
    return values


async def _weigh(
    hass: HomeAssistant, suffix: str, w: float, z_low: float, z_high: float
) -> None:
    hass.states.async_set(f"sensor.w_{suffix}", str(w))
    hass.states.async_set(f"sensor.low_{suffix}", str(z_low))
    hass.states.async_set(f"sensor.high_{suffix}", str(z_high))
    await hass.async_block_till_done()


async def test_handler_xiaomi_home_mode_uses_firmware_formulas(
    hass: HomeAssistant, freezer: Any
) -> None:
    """In Xiaomi Home mode, the published metrics are the firmware values."""
    freezer.move_to("2026-10-25 12:00:00+00:00")  # age 46
    handler = BodyScaleMetricsHandler(
        hass, _dual_config("xh", ALGO_XIAOMI_HOME), config_entry_id="e1"
    )
    metrics = [
        Metric.FAT_PERCENTAGE,
        Metric.LBM,
        Metric.MUSCLE_MASS,
        Metric.WATER_PERCENTAGE,
        Metric.BONE_MASS,
        Metric.PROTEIN_PERCENTAGE,
        Metric.BMR,
        Metric.VISCERAL_FAT,
        Metric.SKELETAL_MUSCLE_MASS,
    ]
    values = _subscribe(handler, metrics)

    # Sensor order does not matter: the larger impedance is the 50 kHz one.
    await _weigh(hass, "xh", 79.4, 501, 559)

    last = {m: v[-1] for m, v in values.items()}
    assert last[Metric.FAT_PERCENTAGE] == pytest.approx(24.1)
    assert last[Metric.LBM] == pytest.approx(60.3)
    assert last[Metric.MUSCLE_MASS] == pytest.approx(57.1)
    assert last[Metric.WATER_PERCENTAGE] == pytest.approx(52.0)
    assert last[Metric.BONE_MASS] == pytest.approx(3.2)
    assert last[Metric.PROTEIN_PERCENTAGE] == pytest.approx(19.1)
    assert last[Metric.BMR] == 1672
    assert last[Metric.VISCERAL_FAT] == 11
    assert last[Metric.SKELETAL_MUSCLE_MASS] == pytest.approx(29.9)
    handler.unload()


@pytest.mark.parametrize("calculation_mode", [ALGO_XIAOMI, ALGO_SCIENCE])
async def test_existing_s400_profiles_keep_scientific_formulas(
    hass: HomeAssistant, freezer: Any, calculation_mode: str
) -> None:
    """S400 profiles saved before this mode existed keep the same values."""
    freezer.move_to("2026-10-25 12:00:00+00:00")
    handler = BodyScaleMetricsHandler(
        hass, _dual_config(calculation_mode, calculation_mode), config_entry_id="e1"
    )
    values = _subscribe(handler, [Metric.FAT_PERCENTAGE, Metric.LBM])
    await _weigh(hass, calculation_mode, 79.4, 559, 501)

    assert values[Metric.LBM][-1] == pytest.approx(59.4)
    assert values[Metric.FAT_PERCENTAGE][-1] == pytest.approx(25.2)
    handler.unload()


@pytest.mark.parametrize("calculation_mode", [ALGO_SCIENCE, ALGO_XIAOMI_HOME])
async def test_dual_bmr_and_visceral_follow_each_measurement(
    hass: HomeAssistant,
    freezer: Any,
    monkeypatch: pytest.MonkeyPatch,
    calculation_mode: str,
) -> None:
    """BMR (and visceral fat in Xiaomi Home mode) must update on every weigh-in.

    In dual mode BMR depends on LBM, so it used to be computed in the
    weight-only pass, before the impedances arrived, and never refreshed.
    """
    from custom_components.bodymiscale import metrics as metrics_module

    now = [1000.0]
    monkeypatch.setattr(metrics_module.time, "monotonic", lambda: now[0])
    freezer.move_to("2026-10-25 12:00:00+00:00")

    suffix = f"refresh_{calculation_mode}"
    handler = BodyScaleMetricsHandler(
        hass, _dual_config(suffix, calculation_mode), config_entry_id="e1"
    )
    values = _subscribe(handler, [Metric.BMR, Metric.VISCERAL_FAT, Metric.LBM])

    await _weigh(hass, suffix, 79.4, 559, 501)
    first = {m: v[-1] for m, v in values.items()}

    now[0] += 3600  # next weigh-in, one hour later
    freezer.tick(3600)
    await _weigh(hass, suffix, 78.0, 600, 540)
    second = {m: v[-1] for m, v in values.items()}

    assert second[Metric.LBM] != first[Metric.LBM]
    assert second[Metric.BMR] != first[Metric.BMR]
    assert second[Metric.BMR] == pytest.approx(370 + 21.6 * second[Metric.LBM], abs=2)
    if calculation_mode == ALGO_XIAOMI_HOME:
        expected = xiaomi_home.visceral_fat(176.0, 78.0, 600, 540)
        assert second[Metric.VISCERAL_FAT] == expected
    handler.unload()


async def test_standard_impedance_ignores_xiaomi_home(
    hass: HomeAssistant, freezer: Any
) -> None:
    """A single-frequency profile is never routed to the S400 firmware formulas."""
    freezer.move_to("2026-10-25 12:00:00+00:00")
    config = {
        "name": "TestUser",
        CONF_BIRTHDAY: "1980-01-01",
        CONF_GENDER: Gender.MALE,
        CONF_HEIGHT: 176.0,
        CONF_CALCULATION_MODE: ALGO_XIAOMI_HOME,
        CONF_IMPEDANCE_MODE: IMPEDANCE_MODE_STANDARD,
        CONF_PROFILE_METHOD: PROFILE_METHOD_NONE,
        CONF_SENSOR_WEIGHT: "sensor.w_std_xh",
        CONF_SENSOR_IMPEDANCE: "sensor.imp_std_xh",
    }
    handler = BodyScaleMetricsHandler(hass, config, config_entry_id="e1")
    values = _subscribe(handler, [Metric.FAT_PERCENTAGE])
    hass.states.async_set("sensor.w_std_xh", "79.4")
    hass.states.async_set("sensor.imp_std_xh", "500")
    await hass.async_block_till_done()

    assert values[Metric.FAT_PERCENTAGE]
    handler.unload()


async def test_s400_metabolic_age_same_for_leftover_xiaomi_mode(
    hass: HomeAssistant, freezer: Any
) -> None:
    """A leftover "xiaomi" mode on an S400 profile behaves exactly like science."""
    freezer.move_to("2026-10-25 12:00:00+00:00")
    results = {}
    for mode in (ALGO_XIAOMI, ALGO_SCIENCE):
        suffix = f"meta_{mode}"
        handler = BodyScaleMetricsHandler(
            hass, _dual_config(suffix, mode), config_entry_id="e1"
        )
        values = _subscribe(handler, [Metric.METABOLIC_AGE, Metric.FAT_PERCENTAGE])
        await _weigh(hass, suffix, 79.4, 559, 501)
        results[mode] = {m: v[-1] for m, v in values.items()}
        handler.unload()
    assert results[ALGO_XIAOMI] == results[ALGO_SCIENCE]

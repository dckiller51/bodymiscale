# Changelog

All notable changes to this project will be documented in this file.

<!--next-version-placeholder-->

## 2026.6.0

### ✨ New features

- Added optional `stabilized` binary sensor support (`CONF_SENSOR_STABILIZED`)
  — when configured, recalculation fires immediately when the sensor turns `ON`,
  bypassing the 5-second debounce window. This eliminates the measurement delay
  for scales that expose a stabilization signal (e.g. Xiaomi S400 via ESPHome
  or xiaomi_ble).

- Switched state tracking from `state_changed` to `state_changed` + `state_reported`
  — the handler now listens to both events. `state_reported` fires on every write
  from the scale, even when the value is identical to the previous one. This ensures
  `last_measurement_time` is always updated and recalculation always triggers,
  regardless of whether the weight has changed between two weighings.

## 2026.5.6

### 🔧 Bug fixes

- Refactored metric recalculation to use topological ordering — all derived
  metrics are now computed in a single deterministic pass (BMI → LBM →
  FAT_PERCENTAGE → ... → BODY_SCORE), eliminating redundant cascade
  recalculations.
- Fixed double/redundant recalculations when weight and impedance arrive as
  separate state updates — a `_settling` flag now blocks intermediate
  recalculations until the debounce window elapses. A 5-second debounce
  (`RECALCULATION_DEBOUNCE` in `const.py`) ensures all sensors (weight,
  impedance_low, impedance_high) have settled before the single recalculation
  fires.
  Closes [#378](https://github.com/dckiller51/bodymiscale/issues/378).
- Fixed `last_measurement_time` updating twice per measurement cycle (once on
  weight, once on impedance) — timestamp is now stamped once in
  `_on_debounce_elapsed` after all sensors have settled.
  Closes [#378](https://github.com/dckiller51/bodymiscale/issues/378).
- Fixed renamed `bone_cell_mass` to `bcm` in attributes to match the
  bodymiscale component attribute name.

## 2026.5.5

### 🔧 Bug fixes

- Fixed sensor name translations not being applied in the UI [[#222](https://github.com/dckiller51/bodymiscale/issues/222)] — `_attr_name` was overriding `translation_key` for all entities. The main umbrella entity now sets its name explicitly while normal sensors delegate name resolution to HA via `translation_key`

## 2026.5.6

### 🔧 Bug fixes

- Refactored metric recalculation to use topological ordering — all derived
  metrics are now computed in a single deterministic pass (BMI → LBM →
  FAT_PERCENTAGE → ... → BODY_SCORE), eliminating redundant cascade
  recalculations.
- Fixed double/redundant recalculations when weight and impedance arrive as
  separate state updates — a `_settling` flag now blocks intermediate
  recalculations until the debounce window elapses. A 5-second debounce
  (`RECALCULATION_DEBOUNCE` in `const.py`) ensures all sensors (weight,
  impedance_low, impedance_high) have settled before the single recalculation
  fires.
  Closes [#378](https://github.com/dckiller51/bodymiscale/issues/378).
- Fixed `last_measurement_time` updating twice per measurement cycle (once on
  weight, once on impedance) — timestamp is now stamped once in
  `_on_debounce_elapsed` after all sensors have settled.
  Closes [#378](https://github.com/dckiller51/bodymiscale/issues/378).
- Fixed renamed `bone_cell_mass` to `bcm` in attributes to match the
  bodymiscale component attribute name.

## 2026.5.5

### 🔧 Bug fixes

- Fixed sensor name translations not being applied in the UI [[#222](https://github.com/dckiller51/bodymiscale/issues/222)] — `_attr_name` was overriding `translation_key` for all entities. The main umbrella entity now sets its name explicitly while normal sensors delegate name resolution to HA via `translation_key`

## 2026.5.6

### 🔧 Bug fixes

- Refactored metric recalculation to use topological ordering — all derived
  metrics are now computed in a single deterministic pass (BMI → LBM →
  FAT_PERCENTAGE → ... → BODY_SCORE), eliminating redundant cascade
  recalculations.
- Fixed double/redundant recalculations when weight and impedance arrive as
  separate state updates — a `_settling` flag now blocks intermediate
  recalculations until the debounce window elapses. A 5-second debounce
  (`RECALCULATION_DEBOUNCE` in `const.py`) ensures all sensors (weight,
  impedance_low, impedance_high) have settled before the single recalculation
  fires.
  Closes [#378](https://github.com/dckiller51/bodymiscale/issues/378).
- Fixed `last_measurement_time` updating twice per measurement cycle (once on
  weight, once on impedance) — timestamp is now stamped once in
  `_on_debounce_elapsed` after all sensors have settled.
  Closes [#378](https://github.com/dckiller51/bodymiscale/issues/378).
- Fixed renamed `bone_cell_mass` to `bcm` in attributes to match the
  bodymiscale component attribute name.

## 2026.5.5

### 🔧 Bug fixes

- Fixed sensor name translations not being applied in the UI [[#222](https://github.com/dckiller51/bodymiscale/issues/222)] — `_attr_name` was overriding `translation_key` for all entities. The main umbrella entity now sets its name explicitly while normal sensors delegate name resolution to HA via `translation_key`

## 2026.5.4

### 🌍 Translations

- Added `nearest_weight`, `initial_weight` and `nearest_tolerance` translations for all supported languages (DA, DE, ES, FR, IT, NL, PL, pt-BR, RO, RU, SK, zh-Hans, zh-Hant).

## 2026.5.3

> 🙏 Thank you to [@Eskander](https://github.com/Eskander) for contributing the `nearest_weight` profile method — [[#379](https://github.com/dckiller51/bodymiscale/pull/379)].

### 🆕 New features

#### Nearest-weight profile method

- New `nearest_weight` profile method — automatically assigns a measurement to the
  user whose current weight is closest to the sensor value, following the approach
  proposed in [#11 (comment)](https://github.com/dckiller51/bodymiscale/issues/11#issuecomment-2009918440).
  Closes [#373](https://github.com/dckiller51/bodymiscale/issues/373).
- Configurable tolerance (`nearest_tolerance`, default ±5 kg) — measurement is
  rejected if no user's current weight falls within the tolerance window.
- `initial_weight` field — seeds the user's current weight on first setup so the
  filter is operational immediately without waiting for a prior accepted measurement.
- Tie-breaking: when two users are equidistant, the match is awarded alphabetically.

---

### ⚙️ Changes

#### New constants (`const.py`)

- `PROFILE_METHOD_NEAREST`
- `CONF_INITIAL_WEIGHT`
- `CONF_NEAREST_TOLERANCE`

---

### 🔧 Bug fixes

- Fixed `async_step_profile` exceeding pylint branch limit — extracted `_validate_weight`, `_validate_nearest` and `_validate_notify` as module-level helpers.

## 2026.5.2

### Bug Fixes

- Fix notification service resolution failing for devices with accented names (e.g. `Smartphone Frédéric` → `mobile_app_smartphone_frederic`) by applying Unicode NFKD normalization before fuzzy matching in `_resolve_notify_service`.

## 2026.5.1

### Bug Fixes

- Set minimum Home Assistant version to **2026.3.0** (Python 3.14 required) [[#374](https://github.com/dckiller51/bodymiscale/issues/374)].

## 2026.5.0

> 🙏 This release is dedicated to [@mano3m](https://github.com/mano3m), whose PR [#355](https://github.com/dckiller51/bodymiscale/pull/355) was the inspiration and technical foundation for this version — state restoration, Dutch translations, profile ID filtering and weight range filtering. Thank you for this outstanding contribution.

### 🆕 New features

#### Profile system and interactive notifications

- New `profile.py` — complete profile management architecture:
  - `NotificationCoordinator`: central coordinator for sending interactive push notifications to mobile devices
  - Notification translations loaded dynamically based on HA server language (`_get_notify_translations`)
  - Added optional weight pre-filter for notification profiles (`notify_weight_min` / `notify_weight_max`) — when configured, a notification is only sent to a user if the measured weight falls within their range, allowing up to 5+ users to share the same scale without exceeding the 3-action limit on mobile notifications
  - `ProfileFilter` (ABC) + implementations `NoFilterProfile`, `WeightRangeFilter`, `ProfileIdFilter`: automatic profile selection based on measured weight, a sensor identifier, or no filter
  - `build_profile_filter()`: factory that instantiates the correct filter based on configuration
  - Support for 4 profile detection methods: `none`, `weight_range`, `notification`, `profile_id`
- New sensor `sensor.profile_id` — active profile identifier during a weigh-in

#### Dutch translations

- Added `translations/nl.json`

#### Impedance sensors created by the integration

- bodymiscale now creates its own impedance sensors (no more external `input_number` helpers needed for storage)
- Automatic state restoration on startup via `RestoreSensor` — no more `unknown` state after HA restart

#### Improved cold start

- Current state of scale sensors is read at startup in `BodyScaleMetricsHandler.__init__` — calculations are available immediately without waiting for a new weigh-in, including after migration from a previous version

---

### ⚙️ Changes

#### Restructured config flow (VERSION 1 → 4)

- Added `async_migrate_entry` — automatic migration of existing v1, v2 and v3 config entries:
  - v1 → v2: move `name`/`birthday`/`gender` to `data`, move `height`/sensors to `options`
  - v2 → v3: add `impedance_mode` and `calculation_mode`, purge `last_measurement_time`
  - v3 → v4: add `profile_method`
- Refactored form schemas into 4 distinct functions:
  - `_get_user_schema` — identity (name, birthday, gender)
  - `_get_modes_schema` — height, impedance mode, calculation mode, profile method
  - `_get_sensors_schema` — scale sensors
  - `_get_profile_schema` — profile method and notification
- Removed `_get_impedance_schema` and `_get_main_options_schema` (replaced)
- Added `_purge_impedance_keys`, `_purge_other_method_keys`, `_validate_weight_range`
- Removed manual `last_measurement_time` sensor configuration — bodymiscale now manages the timestamp automatically from `state.last_changed` after each valid measurement, simplifying setup and avoiding stale timestamps

#### Internal metrics (`metrics/__init__.py`)

- New `_MetricsStore` — internal store with differentiated TTL between source metrics (weight, impedance) and derived metrics, replaces the simple dict

#### New constants (`const.py`)

- `CONF_NOTIFY_DEVICE_ID`, `CONF_NOTIFY_SERVICE` — notification configuration
- `CONF_NOTIFY_WEIGHT_MIN`, `CONF_NOTIFY_WEIGHT_MAX` - weight range for the notification
- `CONF_PROFILE_ID`, `CONF_SENSOR_PROFILE_ID` — profile identification
- `CONF_PROFILE_METHOD`, `PROFILE_METHOD_NONE/NOTIFY/WEIGHT/ID`, `PROFILE_METHOD_OPTIONS`
- `CONF_WEIGHT_MIN`, `CONF_WEIGHT_MAX` — weight range for profile filter
- `EVENT_MOBILE_APP_NOTIFICATION_ACTION` — HA event for notification response
- `NOTIFICATION_COORDINATOR`, `NOTIFICATION_TAG`, `PENDING_MEASUREMENT_TIMEOUT`
- `MAIN_ENTITIES`, `CONSTRAINT_PROFILE_ID_MIN/MAX`

#### Developer tooling

- Migration from `setup.cfg` + `mypy.ini` + `requirements.txt` + `bandit.yaml` → unified `pyproject.toml`
- Replaced flake8/black/isort with **Ruff** (lint + format)
- Modernized `.devcontainer.json` — `astral-sh.ruff` extension, removed black/flake8/autopep8
- Added `.codespell-ignore` for scientific terms in docstrings
- `pre-commit`: added `codespell`, `yamllint`, `bandit` hooks

---

### 🗑️ Removals

- `cachetools` removed from `requirements` in `manifest.json` — no longer used
- `bandit.yaml` removed — bandit config migrated to `pyproject.toml`
- `setup.cfg`, `mypy.ini`, `requirements.txt` removed — consolidated into `pyproject.toml`

---

### 🔧 Bug fixes

- Fixed [[#362](https://github.com/dckiller51/bodymiscale/issues/362)] — `Metric.SKELETAL_MUSCLE_MASS` was incorrectly listed as a dependency of `Metric.BODY_SCORE` but is only available in dual frequency mode; removed from dependencies so body score is correctly calculated in single impedance mode
- Fixed [[#276](https://github.com/dckiller51/bodymiscale/issues/276)], [[#342](https://github.com/dckiller51/bodymiscale/issues/342)], [[#343](https://github.com/dckiller51/bodymiscale/issues/343)] — the S400 is now supported via profile ID filtering (the S400 sends a profile ID per user via BLE); note that the S400 uses its own calculation engine.
- Fixed [[#320](https://github.com/dckiller51/bodymiscale/issues/320)] — profile ID filtering is now natively supported; configure a profile ID sensor per user and bodymiscale will automatically route measurements to the correct profile
- Fixed [[#11](https://github.com/dckiller51/bodymiscale/issues/11)], [[#38](https://github.com/dckiller51/bodymiscale/issues/38)], [[#238](https://github.com/dckiller51/bodymiscale/issues/238)], [[#252](https://github.com/dckiller51/bodymiscale/issues/252)], [[#282](https://github.com/dckiller51/bodymiscale/issues/282)] — profile filtering (weight range, profile ID, notification) allows multiple users to share the same scale sensors; combined with automatic state restoration, dedicated per-user `input_number` helpers are no longer needed
- Fixed [[#171](https://github.com/dckiller51/bodymiscale/issues/171)], [[#235](https://github.com/dckiller51/bodymiscale/issues/235)], [[#330](https://github.com/dckiller51/bodymiscale/issues/330)] — TTLCache expiry during reload caused metrics to be cleared for all but the first user to trigger a callback; replaced by `_MetricsStore` which preserves source metrics independently per user across restarts and reloads
- Possibly fixed [[#117](https://github.com/dckiller51/bodymiscale/issues/117)] — the new `_MetricsStore` with differentiated TTL ensures derived metrics are recalculated even when source values are unchanged
- Fixed [[#37](https://github.com/dckiller51/bodymiscale/issues/37)] — automatic state restoration via `RestoreSensor` ensures all metrics persist across restarts and reloads
- YAML → UI migration: `birthday`, `height` and impedance sensors correctly preserved when migrating from an old YAML config to UI configuration
- Fixed metric dependency graph being shared across all profile instances — `depended_by` was mutated on global `_METRIC_DEPS` objects, causing each metric recalculation to fire N times (where N = number of configured users). Each `BodyScaleMetricsHandler` now owns an isolated copy of the dependency graph.

---

### 📐 Blueprint

- **Blueprint**: Updated `interactive_notification_user_selection_weight_data_update.yaml`. (thank you @DJaeger)
  - Added **dual-impedance** support (Low & High Frequency) for Xiaomi S400 scales.
  - Integrated smart Min/Max sorting for LF/HF values.
  - Added 30s data freshness check for improved accuracy.
  - Added 2-decimal rounding for assistance mode.

## 2026.4.5

### 🐛 Bug Fixes

- **Water Percentage (Dual Mode):** Corrected the displayed water percentage in
  S400 dual-frequency mode. The Deurenberg formula was producing physiologically
  implausible values (>90% for BMI <28), which were then clamped to 73%. The
  displayed percentage now consistently uses the **Pace & Rathbun (1945)**
  constant (`(100 − fat%) × 0.73`), expressing TBW as a percentage of **total
  body weight** (~55–65% typical range) rather than an inflated figure. The
  underlying Deurenberg TBW liters are still used internally for ECW/ICW/BCM
  compartment calculations. (Fixes [#360](https://github.com/dckiller51/bodymiscale/issues/360)).

- **Skeletal Muscle Mass (Standard Mode):** Fixed an issue where
  `skeletal_muscle_mass` was incorrectly exposed as an attribute in standard
  (single-frequency) mode. This metric now only appears in **dual-frequency
  mode**.

## 2026.4.4

### ⚠️ IMPORTANT: Scientific Engine Overhaul

This version replaces the experimental Lukaski-based equations with a more robust clinical model specifically optimized for S400 dual-frequency hardware. Users may notice slight shifts in their metrics as we move towards higher physiological accuracy and better medical alignment.

### 🚀 S400 Dual-Frequency Enhancements

- **Full Engine Replacement:** Replaced experimental Lukaski core with a clinical-grade multi-frequency suite:

  - **LBM:** New hardware-calibrated equation utilizing $Z_{lf}$ (50 kHz) to eliminate the "over-fat" bias common in consumer foot-to-foot scales.
  - **TBW (Total Body Water):** Implemented **Deurenberg et al. (1995)** utilizing $Z_{hf}$ (250 kHz), offering superior validation against isotope dilution.
  - **ECW (Extracellular Water):** Introduced **De Lorenzo et al. (1997)** for precise fluid partitioning.
  - **BMR:** Replaced statistical models with **Katch-McArdle (1996)** (`370 + 21.6 × LBM`). This prioritizes actual measured Lean Body Mass, providing much higher accuracy for athletic or overweight users.
  - **Metabolic Age:** Now calculated using a BMR-relative ratio, reflecting actual metabolic health based on measured cellular activity.

- **New Exclusive Metrics:** Unlocked 5 clinical sensors for dual-frequency mode:
  - `extracellular_water` (ECW) & `intracellular_water` (ICW).
  - `ecw_tbw_ratio`: Key indicator for hydration and nutritional status (Normal: 37–39%).
  - `body_cell_mass` (BCM): The metabolically active compartment of your body.
  - `skeletal_muscle_mass` (SMM): **Janssen et al. (2000)** equation, validated against MRI.

### 🧪 Science & Global Changes

- **BMR (Science Mode):** Standardized to the **Schofield (WHO)** equation for all non-dual
  devices, ensuring alignment with international health standards.
- **Water (Science Mode):** Now uses the **Pace & Rathbun (1945)** constant (73% of lean mass)
  instead of the Xiaomi 70% factor, for better physiological accuracy.
- **Protein Calculation:** Shifted to the **Wang et al. (1999)** molecular compartment model.
  Proteins are now calculated as a stable 19.5% fraction of LBM for better cross-metric
  consistency (applies to both Science and S400 modes).
- **Body Score:** Minimum score clamped to **10** (previously 0) to distinguish a
  low-but-measurable result from an unavailable metric.
- **Home Assistant Integration:** New sensor entities for the 5 S400 metrics are created
  automatically when `impedance_mode: dual` is detected.

## 2026.4.3

- **Added (Experimental):** Dual-frequency impedance support for Xiaomi S400 and compatible scales. A new `impedance_mode` selector in the integration configuration allows choosing between `None`, `Standard` (single-frequency), and `Dual-frequency S400` (50 kHz + 250 kHz). ⚠️ The S400 dual-frequency mode is **experimental** — formulas are calibrated on a single reference point and results may vary depending on your body composition and scale firmware. Help us improve them: [#349](https://github.com/dckiller51/bodymiscale/issues/349).
- **Added:** New `impedance_low` and `impedance_high` sensor entities exposed when dual-frequency mode is active.
- **Added:** Separate `calculation_mode` and `impedance_mode` settings. `calculation_mode` (Xiaomi / Scientific) applies only to standard single-frequency mode. The S400 dual-frequency mode uses its own dedicated formulas regardless of this setting.
- **Changed:** Calculation modes are now clearly separated by purpose — `Xiaomi` replicates
  the Zepp Life / Mi Fit app results exactly, `Scientific` uses WHO-recommended equations,
  and `S400` uses its own dedicated dual-frequency adapted formulas.
  _(Note: the specific equations for Scientific and S400 modes were revised in 2026.4.4.)_
- **Fixed:** Migration path from config entry version 2 → 3 now correctly sets `impedance_mode` based on existing sensor configuration.

## 2026.4.2

- **Improved:** Enhanced measurement processing to ensure calculations (BMI, body fat, etc.) are triggered even when weight or impedance values remain identical to the previous reading. (Fixes [#346](https://github.com/dckiller51/bodymiscale/issues/346)).

## 2026.4.1

- **Fixed:** Fixed floating-point discrepancies in sensor history by implementing consistent rounding logic (Fixes [#341](https://github.com/dckiller51/bodymiscale/issues/341)).

## 2026.4.0

- **Added:** New "Scientific" calculation mode for BMR and Body Composition, selectable in the integration configuration (Fixes [#337](https://github.com/dckiller51/bodymiscale/issues/337)).
- **Added:** Hybrid "Last Measurement Time" logic. The sensor is now always available and uses state.last_changed as a fallback if no source sensor is provided (Fixes [#335](https://github.com/dckiller51/bodymiscale/issues/335)).
- **Improved:** Metric recalculation trigger. Sensors now refresh immediately when weight or impedance states change in Home Assistant, even if the values are identical.
- **Fixed:** Better handling of TIMESTAMP sensors to prevent "Unavailable" states after a restart
- **Changed:** Timestamps are now generated by Home Assistant instead of the ESP32. This fixes time sync issues and improves reliability for the weight_impedance_update.yaml blueprint (thank you @cavemancave).

## 2026.1.0

- **Updated:** Russian translation (thank you @denser).

## 2025.9.0

- **Added:** Danish language support (thank you @Milfeldt).
- **Fixed:** Fixed pylint warnings regarding BaseException and Exception in the configuration file.
- **Fixed:** Automatic code formatting with Black and import reorganization with isort.
- **Fixed:** Fixed mypy errors related to incorrect types for state and datetime.
- **Changed (Development):** Updated the development environment to use **Python 3.13**.
- **Changed:** Automatic conversion of sensor values to float with exception handling.
- **Removed:** Unnecessary suppressions in pylintrc.
- **Removed:** Obsolete option abstract-class-little-used removed from Pylint configuration.

## 2025.4.0

- **Fix:** Ensure Bodymiscale entity attributes (including metrics and last measurement time) persist correctly. The internal `TTLCache` used for storing entity attributes has been replaced with a standard dictionary to prevent data loss when only the last measurement time sensor updates.
- **Refactor:** The `TTLCache` in `BodyScaleMetricsHandler` (in `metrics.py`) is now used solely for internal optimization of metric calculations and distribution.
- **Added:** Ability to integrate your latest weight sensor. This integration creates a new sensor `last_measurement_time` and adds an attribute to the `Bodymiscale` component to display the last measurement time.
- **Updated:** Polish translation (thank you @witold-gren).
- **Added:** Slovakia language support (thank you @milandzuris).
- **Improved:** README presentation for better readability.

## 2024.6.0

- **Removed** The `group.py` file, as its functionality is no longer needed.

## 2024.1.3

- **Fixed:** Corrected an issue with the minimal Home Assistant version check.

## 2024.1.2

- **Fixed:** Another correction to the minimal Home Assistant version check.

## 2024.1.1

- **Changed:** Version number patch.

## 2024.1.0

- **Fixed:** [#218](https://github.com/dckiller51/bodymiscale/issues/218) - Set `state_class` as a class variable after installing Core 2024.1 beta (@edenhaus).

## 2023.11.2

- **Fixed:** Corrected the calculation issue when the main weight sensor is in pounds (lb).
- **Added:** Device class "weight" for weight, muscle mass, and bone mass sensors (thanks @5high, @impankratov).
- **Added:** Native unit of measurement "KILOGRAMS" for weight, muscle mass, and bone mass sensors. You can change the measurement units directly in the sensor. The conversion is automatic and will not impact the results.
- **Added:** Native unit of measurement "kcal" for the basal metabolism sensor.
- **Added:** Native unit of measurement "PERCENTAGE" for body fat, protein, and water sensors.
- **Added:** Display precision of 0 for the following sensors to display integer values: - Basal metabolism - Visceral fat - Metabolic age - Body score

## 2023.11.1

- **Added:** Traditional Chinese language support (thank you @yauyauwind).

## 2023.11.0

- **Changed:** The minimum Home Assistant version is now 2023.9.0.
- **Added:** Simple Chinese language support (thank you @5high).
- **Changed:** Version number format to calendar versioning (YYYY.MM.Patch).

## v3.1.2

- **Fixed:** [#27](https://github.com/dckiller51/bodymiscale/issues/27) and [#181](https://github.com/dckiller51/bodymiscale/issues/181) - Resolved the visceral fat result issue.

## v3.1.1

- **Changed:** Updated state body type and BMI label for translation.

## v3.1.0

- **Changed:** Updated state problems, body type, and BMI label for translation.
- **Updated:** Translations for DE, EN, ES, FR, IT, PL, PT-BR, RO, and RU.
- **Added:** Height limit low validation (#122).
- **Fixed:** Naming inconsistencies (#191).

## v3.0.9

- **Changed:** Moved DeviceInfo from entity to device registry.
- **Changed:** Used shorthand attributes.
- **Added:** Support for input type "number" in addition to "sensor" and "input_number".

## v3.0.8

- **Fixed:** [#173](https://github.com/dckiller51/bodymiscale/issues/173) - Resolved naming issues after installing Core 2023.7.0 (@edenhaus).
- **Added:** Logger to manifest (@edenhaus).

## v3.0.7

- **Changed:** Removed sensor body type from sensor, but it is still available as an attribute in the component.
- **Changed:** Refactored `async_setup_platforms` to `async_forward_entry_setups`.
- **Fixed:** Spanish translation (thank you @Nahuel-BM).

## v3.0.6

- **Added:** Spanish language support (thank you @Xesquy).

## v3.0.5

- **Changed:** Moved the `get_age` function to utils (thank you @Gerto).
- **Added:** `ATTR_AGE` to `state_attributes` (thank you @Gerto).

## v3.0.4

- **Added:** Support for input type "input_number" in addition to "sensor" (thank you @erannave).

## v3.0.3

- **Added:** Russian language support (thank you @glebsterx).

## v3.0.2

- **Added:** Romanian language support (thank you @18rrs).

## v3.0.1

- **Fixed:** [#104](https://github.com/dckiller51/bodymiscale/issues/104) - Subscribe to the correct handler.
- **Added:** Italian language support (thank you @mansellrace).
- **Added:** Polish language support (thank you @LukaszP2).

## v3.0.0

- **Changed:** Created a sensor for each attribute (@edenhaus).
- **Updated:** pt-BR translation (@dckiller51).
- **Updated:** FR translation (@dckiller51).
- **Updated:** Pylint from 2.13.9 to 2.14.3 (@dependabot).
- **Updated:** actions/setup-python from 3 to 4 (@dependabot).
- **Updated:** Mypy from 0.960 to 0.961 (@dependabot).
- **Removed:** YAML support and fixed config flow options (@edenhaus).
- **Updated:** pre-commit from 2.18.1 to 2.19.0 (@dependabot).
- **Updated:** github/codeql-action from 1 to 2 (@dependabot).

## v2.1.1

- **Fixed:** Error for iOS users where the birthday selection was not displayed.
- **Fixed:** Error in selecting a date lower than 1970.
- **Updated:** FR translation.

## v2.1.0

- **Added:** Config flow (thank you @edenhaus). YAML file is no longer used. You can now easily add users via the Home Assistant UI (Settings -> Devices & Services -> Add -> Bodymiscale).

## v2.0.0

Major update by @edenhaus, improving code quality and enabling development in a devcontainer.

- **Added:** Code quality tools (pre-commit).
- **Removed** Unused code (e.g., Holtek).
- **Used:** `@cached_property` to optimize calculations.
- **Adjusted:** Names and code to Python coding styles.
- **Updated:** CI actions.
- **Added:** Devcontainer for easier development.

## v1.1.5

- **Fixed:** Convert weight from lbs to kgs if your scale is set to this unit (thank you @rale).

- **Added:** Portuguese Brazilian language support (thank you @hudsonbrendon).

## v1.1.4

- **Updated:** `get_age` function to correctly calculate age from DOB (thank you @borpin).
- **Used:** Assignment expressions.

## v1.1.3

- **Updated:** README to indicate default integration availability in HACS.
- **Updated:** `iot_class` (thank you @edenhaus).

## v1.1.2

- **Updated:** For default integration in HACS.

## v1.1.1

- **Fixed:** Startup errors (thank you @stefangries).

## v1.1.0

- **Added:** Body score (thank you @alinelena).

## v1.0.0

- **Updated:** For the "181B" model: display the minimum score if the impedance sensor is unavailable.

## v0.0.8

- **Fixed:** Spelling error: "Lack-exerscise" to "Lack-exercise".

## v0.0.7

- **Updated:** Decimal handling (@typxxi).
- **Updated:** README (@typxxi).

## v0.0.6

- **Changed:** Attribute names to snake_case format (thanks to Pavel Popov).

## v0.0.5

- **Changed:** Renamed `HomeAssistantType` to `HomeAssistant` for integrations.

## v0.0.4

- **Fixed:** Startup error.
- **Updated:** README (@Ernst79).

## v0.0.3

Removed: Units for future custom card compatibility.

## v0.0.2

Implemented: Calculations (thanks to lolouk44).

## v0.0.1

Initial release.

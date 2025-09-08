# Changelog

All notable changes to this project will be documented in this file.

<!--next-version-placeholder-->

## 2025.9.0

- **Added:** Danish language support (thank you @Milfeldt).
- **Fixed:** Fixed pylint warnings regarding BaseException and Exception in the configuration file.
- **Fixed:** Automatic code formatting with Black and import reorganization with isort.
- **Fixed:** Fixed mypy errors related to incorrect types for state and datetime.
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

Fixed:\*\* Convert weight from lbs to kgs if your scale is set to this unit (thank you @rale).

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

Fixed:\*\* Startup errors (thank you @stefangries).

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

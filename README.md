# Bodymiscale

[![GH-release](https://img.shields.io/github/v/release/dckiller51/bodymiscale.svg?style=flat-square)](https://github.com/dckiller51/bodymiscale/releases)
[![GH-downloads](https://img.shields.io/github/downloads/dckiller51/bodymiscale/total?style=flat-square)](https://github.com/dckiller51/bodymiscale/releases)
[![GH-last-commit](https://img.shields.io/github/last-commit/dckiller51/bodymiscale.svg?style=flat-square)](https://github.com/dckiller51/bodymiscale/commits/main)
[![GH-code-size](https://img.shields.io/github/languages/code-size/dckiller51/bodymiscale.svg?color=red&style=flat-square)](https://github.com/dckiller51/bodymiscale)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=flat-square)](https://github.com/hacs)

## Track your body composition closely with Bodymiscale

With this Home Assistant integration, track your body composition closely using data from your weight sensor. You will get detailed information for accurate tracking.

## How it works

Bodymiscale retrieves data from your existing weight sensor (and optionally, your impedance sensor) in Home Assistant. It then calculates various body composition metrics using standard formulas. These calculations are performed locally within Home Assistant.

Here's a breakdown of the process:

1. **Data Input:** Bodymiscale relies on data provided by your configured weight sensor. This can be:

   - A `sensor` entity that's already integrated with Home Assistant.
   - An `input_number` entity that's already integrated with Home Assistant.

2. **Optional Impedance Data:** If you have configured an impedance sensor, Bodymiscale will also use this data to calculate more advanced metrics.

3. **Calculations:** Bodymiscale uses standard, scientifically recognized formulas to derive various metrics like BMI, basal metabolism, body fat percentage, and others.

4. **Output:** The calculated metrics are then made available as new `sensor` entities within Home Assistant. You can then use these sensors in your Lovelace dashboards, automations, or any other Home Assistant feature.

**Key Considerations:**

- **Accuracy:** The accuracy of the calculated metrics depends heavily on the accuracy of your weight and (if used) impedance measurements. Ensure your sensors are calibrated and providing reliable data.
- **No External Services:** Bodymiscale performs all calculations locally within your Home Assistant instance. No data is sent to external services or the internet.

**Example:**

Let's say you've configured a weight sensor called `sensor.my_weight`. When you add the Bodymiscale integration, it will:

1. Read the current value of `sensor.my_weight`.
2. Use this value (along with other information like age and gender you provided during configuration) to calculate your BMI, BMR, etc.
3. Create new sensors like `sensor.myname_bmi`, `sensor.myname_bmr`, etc., containing these calculated values.

## Prerequisites

Before installing Bodymiscale, ensure you have the following:

1. **A user-dedicated weight sensor in Home Assistant:** There is no relationship between Bodymiscale and a specific connected scale. Bodymiscale works with any weight sensor integrated into Home Assistant. This can be:

   - A user-dedicated `sensor` entity. **Warning:** Using a sensor directly from a scale can lead to complications.
   - An `input_number` entity offers a robust solution for recording your weight measurements in Home Assistant, with the crucial advantage of data persistence even after a system restart.

   **Important:** It is mandatory that each Bodymiscale user has their own dedicated weight sensor. This must be persistent, meaning that when you restart Home Assistant, the data is still available. Indeed, Bodymiscale retrieves the sensor value at the time of its initialization, which will distort the calculation data with an unavailable or zero sensor.

2. **Home Assistant installed.**

**(Optional) User-dedicated impedance sensor:**

If you plan to use an impedance sensor for more advanced metrics (lean body mass, body fat mass, etc.), make sure you also have a dedicated impedance sensor configured in Home Assistant. The same recommendation applies: each user should have their own dedicated impedance sensor for best results.

**(Optional) Last weigh-in sensor dedicated to the user:**

If you plan to integrate your own last weigh-in sensor, make sure a dedicated sensor is properly configured in Home Assistant. The same recommendation applies: each user should have their own last weigh-in sensor for optimal results.

## Generated data

Bodymiscale calculates the following data:

| Data             | Description                                                           | Impedance sensor required |
| ---------------- | --------------------------------------------------------------------- | ------------------------- |
| Weight           | Measured weight                                                       | No                        |
| Height           | User height                                                           | No                        |
| Age              | User age                                                              | No                        |
| BMI              | Body Mass Index                                                       | No                        |
| Basal Metabolism | Number of calories your body burns at rest                            | No                        |
| Visceral Fat     | Estimation of fat around organs                                       | No                        |
| Ideal Weight     | Recommended weight based on your height and age                       | No                        |
| BMI Category     | BMI category (e.g., "Underweight", "Normal", "Overweight", "Obesity") | No                        |
| Lean Body Mass   | Body mass without fat                                                 | Yes                       |
| Body Fat Mass    | Body fat mass                                                         | Yes                       |
| Water            | Percentage of water in the body                                       | Yes                       |
| Bone Mass        | Bone mass                                                             | Yes                       |
| Muscle Mass      | Muscle mass                                                           | Yes                       |
| Ideal Fat Mass   | Recommended body fat range                                            | Yes                       |
| Protein          | Percentage of protein in the body                                     | Yes                       |
| Body Type        | Body type classification                                              | Yes                       |

## Installation

### Via HACS

1. Open HACS in Home Assistant.
2. Go to the "Integrations" tab.
3. Search for "Bodymiscale".
4. Click "Install".

### Manual

1. Download the latest version archive from the [releases page](https://github.com/dckiller51/bodymiscale/releases).
2. Unzip the archive.
3. Copy the _entire_ `custom_components/bodymiscale` folder into your `config/custom_components` folder in Home Assistant. The final path should be `/config/custom_components/bodymiscale`.
4. Restart Home Assistant.

## Configuration

1. Open Home Assistant and go to "Settings" -> "Devices & Services" -> "Add Integration".
2. Search for "Bodymiscale".
3. **Personalize your integration:**
   - **First Name (or other identifier):** Enter your first name or another identifier. **Important:** This identifier will determine the name of your Bodymiscale component in Home Assistant, as well as the names of all sensors created by it. Choose a clear and relevant name.
   - **Date of Birth:** Enter your date of birth in YYYY-MM-DD format.
   - **Gender:** Select your gender (Male/Female).
4. **Select your weight sensor:** Choose the existing weight sensor in Home Assistant (e.g., a `sensor`, or an `input_number`).
   - **Important Recommendation:** It is **strongly recommended** that each Bodymiscale user has their own dedicated weight sensor. Using a shared weight sensor (e.g., one directly linked to a scale) can cause issues when Home Assistant restarts. This is because Bodymiscale retrieves the sensor's value upon initialization, which can skew calculations if multiple users weigh themselves successively on the same scale before the restart.
5. **Impedance sensor (optional):** If you have an impedance sensor, select it here. This sensor is required to calculate some advanced metrics (lean body mass, body fat mass, etc.).
   - **Recommendation:** As with the weight sensor, it is best for each user to have their own dedicated impedance sensor to avoid issues during restarts.
6. **Last measurement time sensor (optional):**
   If you have a last weigh-in sensor, select it here (e.g., a `sensor`, or an `input_datetime`). This sensor is used to record the date and time of the most recent measurement.
   Recommendation: Just like the weight and impedance sensors, it is strongly recommended that each user has their own dedicated last weigh-in sensor to prevent conflicts or errors during Home Assistant restarts.
7. Click "Save".

**Explanation of choices:**

- **First Name/Identifier:** This field is important because it allows you to personalize the integration and avoid conflicts if multiple people use Bodymiscale in your home. The name you choose will be used to name the entities created by the integration (e.g., `sensor.firstname_weight`, `sensor.firstname_bmi`, etc.).
- **Date of Birth and Gender:** This information is needed to calculate some metrics, such as basal metabolism.

**Tips:**

- If you do not have an impedance sensor, some metrics will not be unavailable. You can still use Bodymiscale to get basic information (weight, BMI, etc.).

## FAQ

- **Why are some values missing?** You must have an impedance sensor configured for Bodymiscale to calculate lean body mass, body fat mass, etc.
- **How accurate is the data?** Bodymiscale uses standard formulas, but the accuracy of measurements depends on your scale and its configuration.

## Helps create weight, impedance and/or last weighing data persistently

For a detailed configuration to integrate data persistence and multi-user management, please refer to the [example_config](example_config/) folder.

This folder contains example configurations for generating weight, impedance, and last weighing sensors, using both ESPHome and Home Assistant.

### Configuration Examples in the example_config Folder

The [example_config](example_config/) folder contains the following example configuration files:

- **`esphome_configuration.yaml`**: Complete ESPHome configuration to generate sensors directly from the Xiaomi Mi Scale.
- **`weight_impedance_update.yaml`**: Home Assistant configuration to generate sensors via the ESPHome integration or BLE Monitor.
- **`interactive_notification_user_selection_weight_data_update.yaml`**: Example automation created from the blueprint for user selection and weight data update via interactive notification.

Please consult the configuration files within the [example_config](example_config/) folder for detailed information on generating weight, impedance, and last weighing sensors.

## Useful links

- [Lovelace Card for Bodymiscale](https://github.com/dckiller51/lovelace-body-miscale-card)
- [ESPHome for Xiaomi Mi Scale](https://esphome.io/components/sensor/xiaomi_miscale.html)
- [BLE Monitor for Xiaomi Mi Scale](https://github.com/custom-components/ble_monitor)

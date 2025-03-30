# ESPHome Configurations for Xiaomi Mi Scale with Multi-User Management

This project provides two example ESPHome configurations to integrate a Xiaomi Mi Scale into Home Assistant, with a focus on multi-user management and data persistence.

## Example 1: Complete Management by ESPHome

* **File:** `esphome_configuration.yaml`
* **Description:** This example demonstrates how to configure ESPHome to manage all sensors (weight, impedance, last weighing time) directly. ESPHome is responsible for data persistence and associating measurements with users based on weight ranges.
* **Advantages:**
  * Autonomy: ESPHome handles all logic, reducing the load on Home Assistant.
  * Data Persistence: Data is retained even after an ESPHome restart.
* **Usage:** Ideal for users who want a robust and self-contained solution.

## Example 2: ESPHome or BLE Monitor + Home Assistant (User Management by HA)

* **Files:**
  * `esphome_base_configuration.yaml`: Basic ESPHome configuration to provide raw data to Home Assistant.
  * `weight_impedance_update.yaml`: Home Assistant configuration to manage user logic.
* **Description:** This example demonstrates how to configure ESPHome to provide raw data (weight, impedance, last weighing time) to Home Assistant. Home Assistant is then used to manage user logic (measurement association, user data persistence).
[![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/dckiller51/bodymiscale/blob/main/example_config/weight_impedance_update.yaml)
* **Advantages:**
  * Flexibility: Allows for extensive customization of user management in Home Assistant.
  * Home Assistant Integration: Leverages Home Assistant's features for user data management.
* **Usage:** Ideal for users who want advanced customization of user management in Home Assistant.

## Common Features

* **Multi-User Management:** Both examples support managing multiple users (up to 5).
* **Data Persistence:** Data is retained even after an ESPHome restart (in Example 1) or a Home Assistant restart (in Example 2).
* **Flexibility for Scales Without Impedance:** Users can easily adapt the configurations to their scales.
* **Weight Range Filtering:** Measurements are associated with users based on configurable weight ranges.

## Configuration

1. **ESPHome Installation:** Ensure you have ESPHome installed and configured for your ESP32 device.
2. **Secrets Configuration:** Create a `secrets.yaml` file to store your sensitive information (Wi-Fi SSID, password, etc.).
3. **Example Selection:** Choose the desired configuration example (`esphome_configuration.yaml` or `esphome_base_configuration.yaml` + `weight_impedance_update.yaml`).
4. **User Configuration:** Configure user names, weight ranges, and other parameters in the configuration files.
5. **Configuration Upload:** Upload the configuration to your ESP32 device using ESPHome.
6. **Home Assistant Integration:** Sensors will be automatically discovered by Home Assistant. You can add them to your dashboards.

## Code Examples

This directory contains the following configuration files:

* **`esphome_configuration.yaml`:** Complete ESPHome configuration to manage all sensors directly.
* **`esphome_base_configuration.yaml`:** Basic ESPHome configuration to provide raw data to Home Assistant (used in Example 2).
* **`weight_impedance_update.yaml`:** Home Assistant configuration to manage user logic (used in Example 2).

Please refer to these files for detailed code examples and specific configurations.

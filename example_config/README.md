# Example configurations for Xiaomi Mi Scale with multi-user management

This project offers three example configurations for integrating a Xiaomi Mi Scale with Home Assistant, with an emphasis on multi-user management and data persistence.

## Example 1: Complete Management by ESPHome

- **File:** `esphome_configuration.yaml`
- **Description:** This example demonstrates how to configure ESPHome to manage all sensors (weight, impedance, last weighing time) directly. ESPHome is responsible for data persistence and associating measurements with users based on weight ranges.
- **Advantages:**
  - Autonomy: ESPHome handles all logic, reducing the load on Home Assistant.
  - Data Persistence: Data is retained even after an ESPHome restart.
- **Usage:** Ideal for users who want a robust and self-contained solution.

## Example 2: ESPHome or BLE Monitor + Home Assistant (User Management by HA)

- **Files:**
  - `esphome_base_configuration.yaml`: Basic ESPHome configuration to provide raw data to Home Assistant.
  - `weight_impedance_update.yaml`: Home Assistant configuration to manage user logic.
- **Description:** This example demonstrates how to configure ESPHome to provide raw data (weight, impedance, last weighing time) to Home Assistant. Home Assistant is then used to manage user logic (measurement association, user data persistence).
  [![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/dckiller51/bodymiscale/blob/main/example_config/weight_impedance_update.yaml)
- **Advantages:**
  - Flexibility: Allows for extensive customization of user management in Home Assistant.
  - Home Assistant Integration: Leverages Home Assistant's features for user data management.
- **Usage:** Ideal for users who want advanced customization of user management in Home Assistant.

## Example 3: Home Assistant Blueprint for Interactive User Selection

- **File:** `interactive_notification_user_selection_weight_data_update.yaml` (Example Automation using the Blueprint)
- **Description:** This example utilizes a Home Assistant Blueprint to send an interactive notification when a weight measurement is detected. Users can select who is on the scale, and the blueprint updates the corresponding weight (and optionally impedance/last weigh-in) input numbers/datetimes in Home Assistant. This method requires the Mobile Home Assistant app to receive and respond to the notification.
  [![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://github.com/dckiller51/bodymiscale/blob/main/example_config/interactive_notification_user_selection_weight_data_update.yaml)
- **Advantages:**
  - Interactive: Provides a user-friendly way to identify who is being weighed.
  - Flexible User Management: User configuration is done directly in the Home Assistant automation created from the blueprint.
  - No Weight Range Configuration: Relies on direct user interaction for identification.
- **Usage:** Ideal for users who prefer a direct, interactive approach to user identification and want to manage user data within Home Assistant using input helpers.

**Interactive Notification Screenshot:**

![Screenshot of Interactive Scale Notification](/example_config/screenshot_phone_notification.jpg)

## Common Features

- **Multi-User Management:** All examples support managing multiple users.
- **Data Persistence:** Data is retained in ESPHome (Example 1), Home Assistant input helpers (Example 2 & 3).
- **Flexibility for Scales Without Impedance:** Users can easily adapt the configurations to their scales.
- **User Identification:** Examples 1 & 2 use weight ranges, while Example 3 uses interactive notifications.

## Configuration

1. **ESPHome Installation (for Examples 1 & 2):** Ensure you have ESPHome installed and configured for your ESP32 device.
2. **BLE Monitor Installation (for Example 2 & potentially triggering Example 3):** Ensure you have BLE Monitor installed if you are using it to receive data.
3. **Mobile Home Assistant App (for Example 3):** Ensure you have the Mobile Home Assistant app installed on your devices to receive interactive notifications.
4. **Secrets Configuration (for ESPHome):** Create a `secrets.yaml` file to store your sensitive information (Wi-Fi SSID, password, etc.).
5. **Example Selection:** Choose the desired configuration example (ESPHome Direct, ESPHome/BLE Monitor + HA Logic, or HA Blueprint).
6. **User Configuration:**
   - **ESPHome Direct:** Configure user names, weight ranges, and other parameters in `esphome_configuration.yaml`.
   - **ESPHome/BLE Monitor + HA Logic:** Configure user logic in the Home Assistant automation (`weight_impedance_update.yaml`).
   - **HA Blueprint:** Create a new automation from the `interactive_notification_user_selection_weight_data_update.yaml` (you'll need to add the blueprint file to your `blueprints/automation/` folder) and configure user names and input helper entities in the automation's settings.
7. **Configuration Upload (for ESPHome):** Upload the ESPHome configuration to your ESP32 device.
8. **Home Assistant Integration:** Sensors and automations will be automatically discovered or need to be created in Home Assistant. You can add them to your dashboards.

## Code Examples

This directory contains the following configuration files:

- **`esphome_configuration.yaml`:** Complete ESPHome configuration to manage all sensors directly.
- **`esphome_base_configuration.yaml`:** Basic ESPHome configuration to provide raw data to Home Assistant (used in Example 2).
- **`weight_impedance_update.yaml`:** Home Assistant configuration to manage user logic (used in Example 2).
- **`interactive_notification_user_selection_weight_data_update.yaml`**: The Home Assistant blueprint for interactive user selection and weight data update (used in Example 3)

Please refer to these files for detailed code examples and specific configurations.

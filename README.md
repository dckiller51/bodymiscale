# Bodymiscale

[![GH-release](https://img.shields.io/github/v/release/dckiller51/bodymiscale.svg?style=flat-square)](https://github.com/dckiller51/bodymiscale/releases)
[![GH-downloads](https://img.shields.io/github/downloads/dckiller51/bodymiscale/total?style=flat-square)](https://github.com/dckiller51/bodymiscale/releases)
[![GH-last-commit](https://img.shields.io/github/last-commit/dckiller51/bodymiscale.svg?style=flat-square)](https://github.com/dckiller51/bodymiscale/commits/main)
[![GH-code-size](https://img.shields.io/github/languages/code-size/dckiller51/bodymiscale.svg?color=red&style=flat-square)](https://github.com/dckiller51/bodymiscale)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=flat-square)](https://github.com/hacs)

## Track your body composition closely with Bodymiscale

With this Home Assistant integration, track your body composition closely using data from your weight sensor. You will get detailed information for accurate tracking.

**How it works**

BodyMiScale calculates advanced body composition metrics based on your scale's data (Weight and/or Impedance). Unlike simple calculators, it offers three distinct calculation engines tailored to your hardware and preferences:

- **Xiaomi Mode:** Faithful to the original 2017 algorithms for consistency with legacy apps (Zepp Life/Mi Fit).
- **Science Mode:** Uses international health standards like **Schofield (WHO)** for BMR and **Pace & Rathbun** for body water.
- **S400 Mode:** A clinical-grade dual-frequency engine (50/250 kHz) utilizing **Deurenberg** and **Janssen** models for precise compartmental analysis.

Here's a breakdown of the process:

1. **Data Input:** Bodymiscale relies on data provided by your configured weight sensor (Weight and optionally Impedance). This can be a `sensor` or an `input_number` entity.

2. **Smart Calculation Engine:** Depending on your configuration, Bodymiscale applies one of three scientific models:

   - **Xiaomi Mode:** Uses the original 2017 algorithms for consistency with Zepp Life.
   - **Science Mode:** Uses international standards like **Schofield (WHO)** and **Pace (0.73)**.
   - **S400 Mode:** Automatically activated for dual-frequency data, using **Deurenberg** and **Janssen** models.

3. **Validation & Constraints:** The engine checks for physiological consistency (e.g., ensuring water doesn't exceed 73% in Science/S400 modes) and filters out aberrant values.

4. **Output:** The calculated metrics are generated as new `sensor` entities in Home Assistant. These are ready to use in your dashboards, automations, or with the dedicated [Lovelace Card](https://github.com/dckiller51/lovelace-body-miscale-card).

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

**(Optional) Last measurement time sensor:**
Previously mandatory for accurate history, this is now optional. Bodymiscale now automatically generates a timestamp based on Home Assistant's internal clock whenever a weight change is detected. If you provide a dedicated sensor, Bodymiscale will prioritize that "real" measurement time over the system time.

## Generated data

Bodymiscale calculates the following metrics. Note that some advanced parameters require an impedance sensor, and clinical-grade multi-compartment metrics are exclusive to dual-frequency hardware (e.g., Xiaomi S400).

| Data                       | Description                                       | Sensor / Mode Required    |
| :------------------------- | :------------------------------------------------ | :------------------------ |
| **Weight**                 | Measured weight                                   | Weight                    |
| **Height**                 | User height                                       | Config                    |
| **Age**                    | User age                                          | Config                    |
| **BMI**                    | Body Mass Index (Standard)                        | Weight                    |
| **Basal Metabolism (BMR)** | Calories burned at rest (Schofield/Katch-McArdle) | Weight / LBM              |
| **Visceral Fat**           | Fat around organs (Zepp Life / S400 Corrected)    | Weight / ECW Ratio        |
| **Ideal Weight**           | Recommended weight based on height/age            | Config                    |
| **BMI Category**           | Underweight to Obesity classification             | Weight                    |
| **Lean Body Mass (LBM)**   | Body mass without fat                             | Impedance                 |
| **Body Fat Mass**          | Total body fat mass                               | Impedance                 |
| **Water (TBW)**            | Total Body Water percentage                       | Impedance                 |
| **Bone Mass**              | Bone mineral content estimation                   | Impedance                 |
| **Muscle Mass**            | Total muscle mass (including organs)              | Impedance                 |
| **Protein**                | Percentage of protein in the body                 | Impedance                 |
| **ECW**                    | Extracellular Water (L)                           | **Dual-frequency (S400)** |
| **ICW**                    | Intracellular Water (L)                           | **Dual-frequency (S400)** |
| **ECW/TBW Ratio**          | Hydration & Inflammation status                   | **Dual-frequency (S400)** |
| **BCM**                    | Body Cell Mass (Active Tissue)                    | **Dual-frequency (S400)** |
| **Skeletal Muscle**        | Actual SMM (validated via MRI)                    | **Dual-frequency (S400)** |

> ℹ️ **Dual-frequency metrics:** These require a scale capable of measuring impedance at multiple frequencies (50 kHz and 250 kHz). They offer a deeper look into your cellular health and hydration levels.

## Calculation Methods

Bodymiscale allows you to choose between three calculation levels. The formulas used depend on your hardware and the selected calculation mode.

### 1. Xiaomi (Legacy 2017)

The original algorithm based on the 2017 Mi Fit ecosystem (reverse-engineered).

- **With Impedance:** Calculates full body composition based on original Xiaomi regression formulas.
- **Best for:** Maintaining 1:1 consistency with historical Mi Scale, Zepp Life, or Mi Fit data.

### 2. Scientific (New in v2026.4.0)

Modern physiological equations for higher precision, recommended for active profiles.

#### A. Without Impedance (Weight only)

Uses standardized anthropometric equations:

- **BMR (Basal Metabolic Rate):** Uses the **Schofield Equation** (official WHO standard).
- **BMI & Ideal Weight:** Calculated using the **Devine Formula**, adjusted for modern height/weight ratios.

#### B. With Impedance (Single-frequency)

Switches to advanced bioelectrical impedance analysis (BIA) models:

- **Lean Body Mass (LBM):** Uses clinically validated equations to calculate non-fat tissue.
- **Water & Protein:** Derived from LBM using standardized physiological constants (**Pace 73%** for hydration and **Wang 19.5%** for proteins).

### 3. S400 (Dual-frequency)

Exclusive to dual-frequency hardware capable of measuring impedance at 50 kHz and 250 kHz.

- **Advanced BIA Models:** Implements a hardware-calibrated baseline for LBM, combined with clinical models like **Deurenberg (1995)** for multi-frequency water analysis, and **Janssen (2000)** for skeletal muscle.
- **BMR (Basal Metabolic Rate):** Uses the **Schofield Equation** (official WHO standard),
  which accounts for age, weight, height, and gender using age-stratified coefficients
  recommended by the Food and Agriculture Organization (FAO/WHO/UNU 1985).
- **Visceral Fat:** Standard Zepp Life base estimate.
- **Exclusive Metrics:** Unlocks 5 clinical metrics: Extracellular Water (ECW), Intracellular Water (ICW), ECW/TBW Ratio, Body Cell Mass (BCM), and MRI-validated Skeletal Muscle Mass (SMM).

---

> 💡 **Deep Dive:** For a full breakdown of the clinical formulas and scientific references (Sun, Janssen, Deurenberg, Wang, etc.), see the [Advanced Metrics Documentation](README_S400_UPGRADE.md).

**Note:** The results of these modes will differ. **Scientific** and **S400** modes are recommended for users looking for clinical-grade estimations, while **Xiaomi Legacy** is best for those tracking progress against years of historical scale data.

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
   - **Calculation Mode:** Choose between **Xiaomi (Legacy 2017)** or **Scientific**. The Scientific mode (added in v2026.4.0) provides a more granular approach to body composition for specific profiles.
     > **S400 users:** The S400 dual-frequency engine is activated automatically when you configure two impedance sensors (`impedance_low` + `impedance_high`) and select `Dual-frequency S400` as the `impedance_mode`. It uses its own dedicated clinical formulas regardless of the `calculation_mode` setting.
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

- If you do not have an impedance sensor, some metrics will not be available. You can still use Bodymiscale to get basic information (weight, BMI, etc.).

---

## FAQ

- **Why are some values missing?** You must have an impedance sensor configured for Bodymiscale to calculate metrics like Lean Body Mass, Body Fat Mass, and advanced S400 data.
- **How accurate is the data?** Bodymiscale uses peer-reviewed scientific formulas (Scientific/S400 modes) or original Xiaomi constants (Legacy). However, accuracy depends heavily on your scale's sensors and consistent measurement conditions.

## Data Persistence & Multi-user Management

For detailed configuration examples regarding data persistence and multi-user setups, please refer to the [example_config](example_config/) folder.

This folder includes:

- **`esphome_configuration.yaml`**: Complete ESPHome setup for Xiaomi Mi Scales.
- **`weight_impedance_update.yaml`**: HA configuration to generate sensors via ESPHome or BLE Monitor.
- **`interactive_notification_user_selection_weight_data_update.yaml`**: Automation blueprint for user selection via interactive notifications.

---

## ⚠️ Medical Disclaimer

**Bodymiscale is NOT a medical device.**

1. **Informational Purpose Only:** The metrics calculated by this integration (BMI, BMR, Body Fat, Visceral Fat, etc.) are estimations based on mathematical formulas and bioelectrical impedance analysis. They are provided for personal tracking and educational purposes only.
2. **Not Medical Advice:** The data generated by Bodymiscale should not be used to diagnose, treat, or prevent any medical condition. Always seek the advice of a physician or other qualified health provider with any questions you may have regarding a medical condition.
3. **Accuracy:** While Bodymiscale uses peer-reviewed scientific formulas, results may vary based on sensor quality and individual physiological differences. Do not make significant changes to your diet or exercise routine based solely on these metrics.
4. **No Liability:** The author of this integration is a developer, not a medical professional. By using this integration, you acknowledge that the author is not responsible for any health-related decisions made based on the provided data.

## Useful links

- [Lovelace Card for Bodymiscale](https://github.com/dckiller51/lovelace-body-miscale-card)
- [ESPHome for Xiaomi Mi Scale](https://esphome.io/components/sensor/xiaomi_miscale.html)
- [BLE Monitor for Xiaomi Mi Scale](https://github.com/custom-components/ble_monitor)

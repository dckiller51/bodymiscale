# S400 Dual-Frequency BIA — Adapted Model for Foot-to-Foot Scales

## Overview

The Xiaomi S400 and compatible scales measure bioelectrical impedance at two frequencies (50 kHz and 250 kHz) using **foot-to-foot electrodes only**. This differs fundamentally from clinical BIA devices, which use four electrodes placed on both hands and feet (tetrapolar hand-to-foot configuration).

> ⚠️ **Important notice:** No peer-reviewed equations have been published specifically for **dual-frequency foot-to-foot** consumer scales. The formulas used in S400 mode are adapted from hand-to-foot clinical literature and empirically calibrated to produce physiologically plausible results on this hardware. They should be treated as **relative trend indicators**, not clinical measurements.

---

## Impedance Naming Convention (Bluetooth S400)

The developer who decoded the S400 Bluetooth protocol named entities by their **numerical value**, not by their frequency:

| Bluetooth entity | Numerical value    | Physical frequency       | Role in BIA                      |
| :--------------- | :----------------- | :----------------------- | :------------------------------- |
| `impedance_low`  | Smaller (e.g. 408) | **250 kHz** (high freq.) | Z_hf — penetrates cell membranes |
| `impedance_high` | Larger (e.g. 452)  | **50 kHz** (low freq.)   | Z_lf — extracellular fluid only  |

This naming is inverted relative to the BIA standard convention (where "low" refers to low _frequency_, not low _value_). The integration corrects this automatically by always using `max(low, high)` as Z_lf and `min(low, high)` as Z_hf, which is physically correct: at low frequency, current cannot cross cell membranes, resulting in a longer path and higher resistance.

---

## Formulas Used (S400 Mode)

### 1. LBM — Lean Body Mass

**Hardware-Calibrated Formula**

$$LBM = \frac{H \times 9.058}{100} \times \frac{H}{100} + W \times 0.32 + 12.226 - Z_{lf} \times 0.0068 - A \times 0.0542$$

**Sexual dimorphism correction (Science & S400 modes)**
The base regression lacks a sex term. Cross-validation against reference data shows female LBM is overestimated by ~16 % (essential fat + lower skeletal muscle mass). A correction factor of **0.84** is applied for females in Science and Dual-frequency modes. Xiaomi Legacy mode compensates this downstream via its `adjust`/`coeff` constants and is left unchanged.

**Origin:** Empirical regression from the Xiaomi/Zepp Life ecosystem, calibrated for foot-to-foot impedance levels, with sex correction added in v2026.8.x. The most appropriate baseline for this hardware, as it accounts for the higher resistance values typical of foot-to-foot measurements.

---

### 2. TBW — Total Body Water (displayed water%)

**Pace & Rathbun (1945) / Siri (1956)**

$$water\% = (100 - fat\%) \times 0.73$$

This expresses TBW as a percentage of **total body weight**, producing physiologically plausible values in the typical adult range (~55–65% for males, ~50–60% for females).

> ℹ️ The underlying Deurenberg formula is still used internally to compute TBW liters for ECW/ICW/BCM compartment calculations, but the **displayed percentage** uses Pace for consistency with clinical references and consumer scale conventions.

---

### 3. TBW — Internal Source for ECW/ICW/BCM

**Pace & Rathbun (1945) / Siri (1956) constant**

$$TBW_{internal} = (1 - fat\% / 100) \times 0.73 \times W$$

**Why a separate TBW?** Validated on 10 reference profiles, the Deurenberg formula overestimates TBW by +10 to +18 L for subjects with BMI < 28, which would propagate large errors to ECW, ICW, and BCM. Using the fat%-derived TBW (Pace constant) as the internal base for compartment calculations reduces errors to ≤ 0.03 L across all profiles.

---

### 4. ECW — Extracellular Water

**Impedance-Ratio Model (empirical adaptation)**

$$Z_{ratio} = Z_{hf} / Z_{lf} \quad (\text{always} < 1 \text{ by BIA physics})$$

$$ECW = TBW_{internal} \times (0.32 + 0.08 \times Z_{ratio})$$

**Origin:** Clinical ECW formulas (De Lorenzo 1997, Kushner 1992) were validated exclusively on hand-to-foot tetrapolar devices and cannot be applied directly to foot-to-foot hardware. This model uses the impedance ratio as a proxy for membrane permeability: at higher frequencies, current penetrates cell membranes more easily, so Z_hf/Z_lf correlates with the ECW/TBW partitioning. In healthy adults, ECW/TBW ≈ 38–39%.

> ⚠️ The constants `0.32` and `0.08` are empirical, chosen to produce an ECW/TBW ratio consistent with reference values in healthy adults. Treat as a relative indicator.

---

### 5. ICW — Intracellular Water

$$ICW\ (L) = TBW_{internal} - ECW$$

Standard compartmental subtraction, universally applied across BIA methods.

---

### 6. ECW/TBW Ratio

$$ECW/TBW\ (\%) = (ECW / TBW_{internal}) \times 100$$

- **Normal range:** 37–39% in healthy adults.
- **> 39%:** May suggest overhydration, inflammation, or edema.
- **< 37%:** May suggest dehydration.

> ℹ️ Best used to track **personal trends over time** rather than as an absolute clinical value.

---

### 7. Protein Percentage

**Wang et al. (1999)** — Molecular compartment model.

$$Protein\% = (LBM \times 0.195 / W) \times 100$$

Proteins represent a stable ~19.5% fraction of Lean Body Mass in healthy adults.

---

### 8. SMM — Skeletal Muscle Mass

**Janssen et al. (2000)** — Originally validated against MRI on hand-to-foot BIA data.

$$SMM = (H^2 / Z_{lf} \times 0.401) + (Sex \times 3.825) + (A \times -0.071) + 5.102$$

_(Sex = 1 for male, 0 for female)_

**Adaptation note:** Applied here on `Z_lf` (50 kHz) as the closest available equivalent to the original hand-to-foot single-frequency measurement. Tends to slightly overestimate SMM on foot-to-foot hardware due to path length differences, but remains the best published reference for BIA-based skeletal muscle estimation.

**Body score thresholds:** In S400 mode, the muscle part of the body score compares SMM against the **Skeletal Muscle Index** (SMI = SMM / height², in kg/m²) cut-points of **Janssen et al. (2004)**:

| Gender | Max penalty below | No penalty above |
| :----- | :---------------- | :--------------- |
| Male   | 8.51 kg/m²        | 10.75 kg/m²      |
| Female | 5.76 kg/m²        | 6.75 kg/m²       |

Between the two values, the penalty decreases progressively. These cut-points come from the same author as the SMM equation and were derived from NHANES III participants **aged 60 and over**, using hand-to-foot BIA, as the SMM levels below which the risk of physical disability rises (sarcopenia). For younger adults they are lenient thresholds: the score only penalizes clearly low muscle mass.

---

### 9. BMR — Basal Metabolic Rate

**Katch-McArdle (1996)**

$$BMR = 370 + 21.6 \times LBM$$

Uses measured Lean Body Mass directly, offering better precision for active or overweight individuals than weight-only formulas.

---

### 10. Metabolic Age

**BMR-Relative Approach**

$$MetaAge = Age \times (BMR_{expected} / BMR_{actual})$$

Where `BMR_expected` is the Harris-Benedict revised estimate for the user's age, weight, height, and gender. Higher LBM → lower metabolic age; lower LBM → higher metabolic age.

---

### 11. BCM — Body Cell Mass

**Wang et al. (1999)**

$$BCM = ICW / 0.73$$

Metabolically active tissue compartment. ICW represents ~73% of BCM in healthy adults.

---

### 12. Visceral Fat

**Zepp Life / Xiaomi standard estimate**

Uses weight, height, and age ratios from the original Xiaomi physiological model. Applied identically across all three calculation modes.

---

## Xiaomi Home Mode (S400 Firmware Formulas)

Select **Xiaomi — Xiaomi Home (S400 only)** as the calculation mode to get the same values as the Xiaomi Home app instead of the scientific formulas above. This mode is only available in dual-frequency mode. With the S400, the calculation mode is either **Scientific** (the formulas above) or **Xiaomi Home**. **Xiaomi — Zepp Life** is for single-frequency scales only. Existing S400 profiles keep the scientific formulas: profiles saved with **Xiaomi — Zepp Life** already used them and are switched to **Scientific** automatically.

**Origin:** formulas reverse-engineered by [@RX14](https://github.com/RX14) from the S400 Pro firmware (unencrypted OTA image) and contributed under the Apache-2.0 license in [#474](https://github.com/dckiller51/bodymiscale/issues/474). They also apply to the standard S400: all validation weighings below come from a standard S400.

**Inputs:** height (H, cm), weight (W, kg), age (A), sex, Z₅₀ (50 kHz, the larger impedance) and Z₂₅₀ (250 kHz). Values are rounded to 0.1 like the firmware (truncated to 0.01, then rounded half up).

| Metric                                         | Formula                                                                                 |
| :--------------------------------------------- | :-------------------------------------------------------------------------------------- |
| **Body fat %**                                 | 100 × (c₁·H + c₂·W + c₃·A + c₄·Z₅₀ + c₅) / W, with sex-specific coefficients (Z₅₀ only) |
| **LBM**                                        | W × (1 − fat% / 100)                                                                    |
| **BMR**                                        | int(21.6 × LBM + 370.5) with LBM rounded to 0.1 kg, clamped to 400–3500 kcal            |
| **Water, bone, skeletal muscle, visceral fat** | Firmware regressions on H, W, Z₅₀, Z₂₅₀ and their square roots                          |
| **Muscle mass**                                | LBM − bone mass                                                                         |
| **Protein**                                    | LBM − solids − water, where solids is another firmware regression                       |

**Validation:** on 10 S400 weighings reported with their Xiaomi Home values ([#349](https://github.com/dckiller51/bodymiscale/issues/349)), 4 match the app exactly on every metric. Across all 10, the mean gap is 0.10 point on body fat, 0.06 kg on muscle, 0.11 kg on bone and 2.5 kcal on BMR. Most remaining gaps are single values, likely typos in the reported data.

**Firmware limits:** body fat is kept between 3 % and 55 %, muscle mass between 7 and 141.5 kg, and skeletal muscle between 45 % and 70 % of the muscle mass.

**Metabolic age:** shown as "body age" in Xiaomi Home. It compares weight, BMR, body fat and muscle with reference values for the same sex, age and height, and stays between 18 and 100. It matches the app on 9 of the 10 reference weighings.

**Requirement:** the 250 kHz impedance (`impedance_high`) must be updated on every weigh-in. With an older `xiaomi_ble` integration it can stay frozen at an old value, which skews water, protein, visceral fat and skeletal muscle. On a weigh-in where Home Assistant received both impedances, every value matched the Xiaomi Home app.

**Known gaps:**

- **Impedance smoothing:** for the values sent to the app, the scale smooths the impedances with the profile's previous measurement. Within 10 minutes and with less than 3.6 points of body fat change, it reuses the previous impedance; up to 30 minutes it weights it 80/20; beyond, 50/50; above 6.1 points of change it uses the new value. Home Assistant receives the raw impedances over Bluetooth, so values can differ slightly from the app after several weigh-ins close together.
- **Visceral fat:** stored as an integer by the scale; the app only adds a decimal for display.
- **Waist-to-hip ratio:** computed by the scale, but its formula is not validated yet, so it is not exposed.
- **ECW, ICW, ECW/TBW ratio and BCM** are not part of the firmware formulas: they keep the scientific formulas, computed from the Xiaomi Home body fat.

---

## Available Metrics Summary

| Metric            | Unit | Method                     | Reliability   |
| :---------------- | :--- | :------------------------- | :------------ |
| **LBM**           | kg   | Xiaomi calibrated          | ✅ Good       |
| **Water% (TBW)**  | %    | Pace & Rathbun (displayed) | ✅ Good       |
| **TBW (liters)**  | L    | Deurenberg (internal)      | ⚠️ Trend only |
| **ECW**           | L    | Z-ratio / Pace TBW         | ⚠️ Trend only |
| **ICW**           | L    | TBW − ECW / Pace TBW       | ⚠️ Trend only |
| **ECW/TBW Ratio** | %    | Derived / Pace TBW         | ⚠️ Trend only |
| **BCM**           | kg   | Wang / ICW                 | ⚠️ Trend only |
| **SMM**           | kg   | Janssen (adapted)          | ✅ Good       |
| **Fat%**          | %    | Siri 2-compartment         | ✅ Good       |
| **BMR**           | kcal | Katch-McArdle              | ✅ Good       |
| **Metabolic Age** | yrs  | BMR-relative               | ✅ Good       |
| **Visceral Fat**  | -    | Zepp Life                  | ✅ Good       |
| **Protein**       | %    | Wang 1999                  | ✅ Good       |

---

## References

1. Deurenberg P et al. (1995). Body composition in the elderly: a comparison of methods. _Am J Clin Nutr_, 61(1):4-12.
2. Katch FI, McArdle WD (1996). _Nutrition, Weight Control, and Exercise_. Williams & Wilkins.
3. Janssen I et al. (2000). Skeletal muscle mass and distribution in 468 men and women aged 18-88 yr. _J Appl Physiol_, 89(1):81-88.
4. Wang Z et al. (1999). Body composition models: a key to understanding nutritional health. _Am J Clin Nutr_, 70(3):405-411.
5. Janssen I et al. (2004). Skeletal muscle cutpoints associated with elevated physical disability risk in older men and women. _Am J Epidemiol_, 159(4):413-421.

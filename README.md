# bodymiscale

EN :

The purpose of this custom integration is to have additional information when weighing yourself with a Xiaomi Mi Scale (or any other smart scale). The input sensors for the custom integration are `weight` and optionally `impedance` (Mi Scale V2 only). You can use [ESPHome](https://esphome.io/) or [BLE monitor](https://github.com/custom-components/ble_monitor) to collect the required data via Bluetooth. The calculations are done in the `body_metrics.py` file. The configuration is in `bodymiscale.yaml` where you define `name`, `weight`, `height`, `age`, `gender` and `impedance` (only for Mi Scale V2).

FR : 

Le but de ce composant est d'avoir des informations supplémentaires lorsque l'on se pese avec une balance connectée Miscale Xiaomi. Actuellement le poids est envoyé sur Hassio avec un [ESPHome](https://esphome.io/) ou [BLE monitor](https://github.com/custom-components/ble_monitor). Le calculateur est le fichier `body_metrics.py`. La base de données est dans le fichier `bodymiscale.yaml` on y retrouve `name`, `le poids`, `la taille`, `l'age`, `le genre` et `l'impedance` (uniquement pour la Mi Scale V2). Le nom du composant devra être bodymiscale.username

The generated data is :

## For miscale (181D)

- Model Miscale
- Weight
- Height
- Years
- Gender
- Bmi
- Basal metabolism
- Visceral fat
- Ideal weight
- Bmi label

## For miscale 2 (181B) (with to impedance)

- Model Miscale
- Weight
- Height
- Years
- Gender
- Bmi
- Basal metabolism
- Visceral fat
- Ideal weight
- Bmi label
- Lean body mass
- Body fat
- Water
- Bone mass
- Muscle mass
- Fat mass ideal
- Protein
- Body type
 
************* 
 
## Installation

### Via HACS : 
* Add Custom repositories URL : `https://github.com/dckiller51/bodymiscale`

### Manual installation :
- You can install it manually. Simply copy and paste the content of the 
`bodymiscale/custom_components` folder in your `config/custom_components`. 
For example, you will get the file `__init __.py` in the following path:
`/config/custom_components/bodymiscale/__init__.py`.

*************

## Configuration
key | type | description
:--- | :--- | :---
**plateform (Required)** | string | `bodymiscale`
**name (Required)** | string | Custom name for the sensor. `bodymiscale.nom`
**weight (Required)** | sensors / sensor.weight_ | Your sensor returning your weight.
**impedance (Optional)** | sensors / sensor.impedance_ | Your sensor returning your impedance.
**height (Required)** | number | Your height in cm. 
**born (Required)** | string | Your birthday. `"1990-04-10"`
**gender (Required)** | string | female or male. `"male"` 
**Model (Optional)** | string | Define the scale model.`"181D"` or `"181B"`.

*************

## Example
**Configuration YAML**
```yaml
bodymiscale: !include components/bodymiscale.yaml
```
Create a file in `/config/components/bodymiscale.yaml`.

**Configuration with default settings:**
```yaml
aurelien:
  sensors:
    weight: sensor.weight_aurelien
  height: 176
  born: "1990-04-10"
  gender: "male"
  model_miscale: "181D"
```
**Configuration with impedance (miscale2) settings:**
```yaml
aurelien:
  sensors:
    weight: sensor.weight_aurelien
    impedance: sensor.impedance_aurelien
  height: 176
  born: "1990-04-10"
  gender: "male"
  model_miscale: "181B"
```

*************

**VERSION**

**0.0.4**
Fixed a startup error.

**0.0.3**
Delete the units for the future custom card.

**0.0.2**
Implantation of calculations. Thanks to lolouk44. I took the liberty of taking back these files.

**0.0.1**
First version. Thanks to the designer of the component plant of homeassistant.

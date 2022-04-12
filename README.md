# bodymiscale

[![GH-release](https://img.shields.io/github/v/release/dckiller51/bodymiscale.svg?style=flat-square)](https://github.com/dckiller51/bodymiscale/releases)
[![GH-downloads](https://img.shields.io/github/downloads/dckiller51/bodymiscale/total?style=flat-square)](https://github.com/dckiller51/bodymiscale/releases)
[![GH-last-commit](https://img.shields.io/github/last-commit/dckiller51/bodymiscale.svg?style=flat-square)](https://github.com/dckiller51/bodymiscale/commits/main)
[![GH-code-size](https://img.shields.io/github/languages/code-size/dckiller51/bodymiscale.svg?color=red&style=flat-square)](https://github.com/dckiller51/bodymiscale)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=flat-square)](https://github.com/hacs)

EN :

The purpose of this custom integration is to have additional information when weighing yourself with a smart scale like Xiaomi Mi Scale.
For example you can use [ESPHome](https://esphome.io/) or [BLE monitor](https://github.com/custom-components/ble_monitor) to collect the required data via Bluetooth.

Information about the unit of measurement. All calculations are made using the unit of measurement KG. If your scale is set in lbs don't worry Bodymiscale will convert for you. If you want to display your data in lbs you can use the card here [lovelace-body-miscale-card](https://github.com/dckiller51/lovelace-body-miscale-card). Just click on Convert kg to lbs.

The generated data is :

- Weight
- Height
- Years
- Gender
- Bmi
- Basal metabolism
- Visceral fat
- Ideal weight
- Bmi label
- Lean body mass \*
- Body fat \*
- Water \*
- Bone mass \*
- Muscle mass \*
- Fat mass ideal \*
- Protein \*
- Body type \*

\*: When also the impedance sensor is configured

---

## Installation

### Via HACS

- Search "Bodymiscale" recently added Component under Integrations in the HACS Store tab

### Manual installation

- You can install it manually. Simply copy and paste the contents of the
  `bodymiscale/custom_components` folder in your`config/custom_components`.
  For example, you will get the file `__init __.Py` in the following path:
  `/config/custom_components/bodymiscale/__init__. py`.

---

## Configuration

1. [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=bodyscale)
   Click on the button above or go to your HA Configuration (Settings) -> Devices & Services -> Add -> Bodymiscale.

2. Insert the required data and select your input sensor for `weight` and optional `impedance`.

---

<details>
  <summary><b>VERSION</b></summary>

## v2.0.0

Big update offered by @edenhaus. It offers us a better quality code and especially to be able to work in devcontainer.

- Add code quality tools, which run with pre-commit
- removed unused code (e.g. holtek)
- use @cached_property to run certain calculation only once
- adjust names and code to python coding styles
- update ci actions
- Add devcontainer for easier development

Thanks to you for the work done.

## v1.1.5

- Convert weight from lbs to kgs if your scale is set to this unit (thank you @rale)
- added portuguese brazilian language support (thank you @hudsonbrendon)

## v1.1.4

- Update getage function to correctly calculate age from DOB (thank you @borpin)
- Use assignment expressions

## v1.1.3

- Update readme: default integration in Hacs is available
- Update iot_class (thank you @edenhaus)

## v1.1.2

Update for default integration in Hacs

## v1.1.1

Update to fix startup errors (thank you @stefangries )

## v1.1.0

Adding body score (thank you @alinelena )

## v1.0.0

Update for the "181B" model: display the minimum score if the impedance sensor is unavailable.

## v0.0.8

spelling update: Lack-exerscise => Lack-exercise

## v0.0.7

- Update decimal by @typxxi (Thanks)
- Update readme by @typxxi (Thanks)

## v0.0.6

- Use snake_case format for attribute names (thanks to Pavel Popov <https://github.com/dckiller51/bodymiscale/pull/13>)

## v0.0.5

- Rename HomeAssistantType —> HomeAssistant for integrations n*- p* #49559

## v0.0.4

- Fixed a startup error.
- Update readme by @Ernst79 (Thanks)

## v0.0.3

Delete the units for the future custom card.

## v0.0.2

Implantation of calculations. Thanks to lolouk44. I took the liberty of taking back these files.

## v0.0.1

First version. Thanks to the designer of the component plant of homeassistant.

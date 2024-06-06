"""Constants for bodymiscale."""

from homeassistant.const import Platform

MIN_REQUIRED_HA_VERSION = "2023.9.0"
NAME = "BodyMiScale"
DOMAIN = "bodymiscale"
VERSION = "2024.6.0"

ISSUE_URL = "https://github.com/dckiller51/bodymiscale/issues"

CONF_BIRTHDAY = "birthday"
CONF_GENDER = "gender"
CONF_HEIGHT = "height"
CONF_SENSOR_IMPEDANCE = "impedance"
CONF_SENSOR_WEIGHT = "weight"
CONF_SCALE = "scale"

ATTR_AGE = "age"
ATTR_BMI = "bmi"
ATTR_BMILABEL = "bmi_label"
ATTR_BMR = "basal_metabolism"
ATTR_BODY = "body_type"
ATTR_BODY_SCORE = "body_score"
ATTR_BONES = "bone_mass"
ATTR_FAT = "body_fat"
ATTR_FATMASSTOGAIN = "fat_mass_to_gain"
ATTR_FATMASSTOLOSE = "fat_mass_to_lose"
ATTR_IDEAL = "ideal"
ATTR_LBM = "lean_body_mass"
ATTR_METABOLIC = "metabolic_age"
ATTR_MUSCLE = "muscle_mass"
ATTR_PROBLEM = "problem"
ATTR_PROTEIN = "protein"
ATTR_VISCERAL = "visceral_fat"
ATTR_WATER = "water"

UNIT_POUNDS = "lb"

PROBLEM_NONE = "none"

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

CONSTRAINT_HEIGHT_MIN = 50
CONSTRAINT_HEIGHT_MAX = 220
CONSTRAINT_IMPEDANCE_MIN = 50
CONSTRAINT_IMPEDANCE_MAX = 3000
CONSTRAINT_WEIGHT_MIN = 10
CONSTRAINT_WEIGHT_MAX = 200

MIN = "min"
MAX = "max"
COMPONENT = "component"
HANDLERS = "handlers"

PLATFORMS: set[Platform] = {Platform.SENSOR}
UPDATE_DELAY = 2.0

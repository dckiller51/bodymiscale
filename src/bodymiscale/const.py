"""Constants for bodymiscale."""
# Base component constants
NAME = "Body Xiaomi Miscale Esphome"
DOMAIN = "bodymiscale"
VERSION = "0.0.1"

ISSUE_URL = "https://github.com/dckiller51/bodymiscale/issues"
DOC_URL = "https://github.com/dckiller51/bodymiscale"

# Icons
ICON = "mdi:human"

# Common constants Miscale
READING_WEIGHT = "weight"
CONF_SENSOR_WEIGHT = READING_WEIGHT
CONF_MIN_WEIGHT = f"min_{READING_WEIGHT}"
CONF_MAX_WEIGHT = f"max_{READING_WEIGHT}"
ATTR_WEIGHT = "weight"
ATTR_HEIGHT = "height"
ATTR_BORN = "born"
ATTR_GENDER = "gender"
ATTR_AGE = "age"
ATTR_BMI = "bmi"
ATTR_BMR = "basal metabolism"
ATTR_VISCERAL = "visceral fat"
ATTR_IDEAL = "ideal"
ATTR_IMCLABEL = "bmi Label"

# Constants for Miscale 2
READING_IMPEDANCE = "impedance"
CONF_SENSOR_IMPEDANCE = READING_IMPEDANCE
CONF_MIN_IMPEDANCE = f"min_{READING_IMPEDANCE}"
CONF_MAX_IMPEDANCE = f"max_{READING_IMPEDANCE}"
ATTR_IMPEDANCE = "impedance"
ATTR_LBM = "lean_body_mass"
ATTR_FAT = "body fat"
ATTR_WATER = "water"
ATTR_BONES = "bone mass"
ATTR_MUSCLE = "muscle mass"
ATTR_FATMASSIDEAL = "fat mass ideal"
ATTR_PROTEIN = "protein"
ATTR_BODY = "body type"
ATTR_METABOLIC = "metabolic age"

# Defaults
DEFAULT_NAME = "bodymiscale"

ATTR_DICT_OF_UNITS_OF_MEASUREMENT = "unit_of_measurement_dict"

ATTR_PROBLEM = "problem"
ATTR_SENSORS = "sensors"
PROBLEM_NONE = "none"

DEFAULT_MIN_WEIGHT = 10
DEFAULT_MAX_WEIGHT = 200
DEFAULT_MIN_IMPEDANCE = 0
DEFAULT_MAX_IMPEDANCE = 3000

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""


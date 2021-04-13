"""Constants for bodymiscale."""
# Base component constants
NAME = "Body Xiaomi Miscale Esphome"
DOMAIN = "bodymiscale"
VERSION = "0.0.4"

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
ATTR_BMI = "BMI"
ATTR_BMR = "Basal metabolism"
ATTR_VISCERAL = "Visceral fat"
ATTR_IDEAL = "Ideal"
ATTR_BMILABEL = "BMI label"

# Constants for Miscale 2
READING_IMPEDANCE = "impedance"
CONF_SENSOR_IMPEDANCE = READING_IMPEDANCE
CONF_MIN_IMPEDANCE = f"min_{READING_IMPEDANCE}"
CONF_MAX_IMPEDANCE = f"max_{READING_IMPEDANCE}"
ATTR_IMPEDANCE = "impedance"
ATTR_LBM = "Lean body mass"
ATTR_FAT = "Body fat"
ATTR_WATER = "Water"
ATTR_BONES = "Bone mass"
ATTR_MUSCLE = "Muscle mass"
ATTR_FATMASSTOLOSE = "Fat mass to lose"
ATTR_FATMASSTOGAIN = "Fat mass to gain"
ATTR_PROTEIN = "Protein"
ATTR_BODY = "Body type"
ATTR_METABOLIC = "Metabolic age"

# Defaults
DEFAULT_NAME = "bodymiscale"

ATTR_PROBLEM = "problem"
ATTR_SENSORS = "sensors"
PROBLEM_NONE = "none"

ATTR_MODEL = "model_miscale"

DEFAULT_MIN_WEIGHT = 10
DEFAULT_MAX_WEIGHT = 200
DEFAULT_MIN_IMPEDANCE = 0
DEFAULT_MAX_IMPEDANCE = 3000
DEFAULT_MODEL = "181D"

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""


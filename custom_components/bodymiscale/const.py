"""Constants for bodymiscale."""
# Base component constants
NAME = "Body Xiaomi Miscale Esphome"
DOMAIN = "bodymiscale"
VERSION = "1.1.3"

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
ATTR_BMR = "basal_metabolism"
ATTR_VISCERAL = "visceral_fat"
ATTR_IDEAL = "ideal"
ATTR_BMILABEL = "bmi_label"

# Constants for Miscale 2
READING_IMPEDANCE = "impedance"
CONF_SENSOR_IMPEDANCE = READING_IMPEDANCE
CONF_MIN_IMPEDANCE = f"min_{READING_IMPEDANCE}"
CONF_MAX_IMPEDANCE = f"max_{READING_IMPEDANCE}"
ATTR_IMPEDANCE = "impedance"
ATTR_LBM = "lean_body_mass"
ATTR_FAT = "body_fat"
ATTR_WATER = "water"
ATTR_BONES = "bone_mass"
ATTR_MUSCLE = "muscle_mass"
ATTR_FATMASSTOLOSE = "fat_mass_to_lose"
ATTR_FATMASSTOGAIN = "fat_mass_to_gain"
ATTR_PROTEIN = "protein"
ATTR_BODY = "body_type"
ATTR_BODY_SCORE = "body_score"
ATTR_METABOLIC = "metabolic_age"

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


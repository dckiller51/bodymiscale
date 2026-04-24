"""Constants for bodymiscale."""

from homeassistant.const import Platform

MIN_REQUIRED_HA_VERSION = "2023.9.0"
NAME = "BodyMiScale"
DOMAIN = "bodymiscale"
VERSION = "2026.4.3"

ISSUE_URL = "https://github.com/dckiller51/bodymiscale/issues"

# System
COMPONENT = "component"
HANDLERS = "handlers"

# Config
CONF_BIRTHDAY = "birthday"
CONF_GENDER = "gender"
CONF_HEIGHT = "height"
CONF_SCALE = "scale"
CONF_PROFILE_ID = "profile_id"

# calculation mode
# - xiaomi  : formula Zepp Life / Mi Fit, etc. (proprietary Xiaomi algorithm)
# - science : formula OMS / Mifflin / Janmahasatian
# Note : mode S400 (dual frequency) automatically chooses its own formulas
#        regardless of this parameter. calculation_mode only applies to
#        standard mode (single impedance).
CONF_CALCULATION_MODE = "calculation_mode"
ALGO_XIAOMI = "xiaomi"
ALGO_SCIENCE = "science"
CALCULATION_MODE_OPTIONS = [ALGO_XIAOMI, ALGO_SCIENCE]

# impedance mode
# - none            : scale not impedance (e.g. Xiaomi Gen1, etc.)
# - standard        : single impedance (Xiaomi Gen2, etc.)
# - dual_frequency  : dual frequency (50 kHz + 250 kHz) (Xiaomi S400)
CONF_IMPEDANCE_MODE = "impedance_mode"
IMPEDANCE_MODE_NONE = "none"
IMPEDANCE_MODE_STANDARD = "standard"
IMPEDANCE_MODE_DUAL = "dual_frequency"
IMPEDANCE_MODE_OPTIONS = [
    IMPEDANCE_MODE_NONE,
    IMPEDANCE_MODE_STANDARD,
    IMPEDANCE_MODE_DUAL,
]

# Sensors
CONF_SENSOR_WEIGHT = "weight"
CONF_SENSOR_IMPEDANCE = "impedance"  # Mode standard
CONF_SENSOR_IMPEDANCE_LOW = "impedance_low"  # dual mode 50 kHz
CONF_SENSOR_IMPEDANCE_HIGH = "impedance_high"  # dual mode 250 kHz
CONF_SENSOR_LAST_MEASUREMENT_TIME = "last_measurement_time"
CONF_SENSOR_PROFILE_ID = "profile_id_sensor"

# Attributs
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

# Contraint
CONSTRAINT_HEIGHT_MIN = 50
CONSTRAINT_HEIGHT_MAX = 220
CONSTRAINT_IMPEDANCE_MIN = 50
CONSTRAINT_IMPEDANCE_MAX = 3000
CONSTRAINT_WEIGHT_MIN = 10
CONSTRAINT_WEIGHT_MAX = 200
CONSTRAINT_PROFILE_ID_MIN = 1
CONSTRAINT_PROFILE_ID_MAX = 5

# Home Assistant
PLATFORMS: set[Platform] = {Platform.SENSOR}
UPDATE_DELAY = 2.0

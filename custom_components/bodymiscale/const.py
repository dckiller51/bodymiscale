"""Constants for bodymiscale."""

from homeassistant.const import Platform

# Versioning and Metadata
NAME = "Bodymiscale"
DOMAIN = "bodymiscale"
VERSION = "2025.2.19-beta"
MIN_REQUIRED_HA_VERSION = "2023.9.0"
ISSUE_URL = "https://github.com/dckiller51/bodymiscale/issues"

# Configuration Keys
CONF_BIRTHDAY = "birthday"
CONF_GENDER = "gender"
CONF_HEIGHT = "height"
CONF_IMPEDANCE_SENSOR = "impedance"
CONF_WEIGHT_SENSOR = "weight"
CONF_SCALE = "scale"

# Attributes
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
ATTR_IDEAL = "ideal_weight"
ATTR_LBM = "lean_body_mass"
ATTR_METABOLIC = "metabolic_age"
ATTR_MUSCLE = "muscle_mass"
ATTR_PROBLEM = "problem"
ATTR_PROTEIN = "protein"
ATTR_VISCERAL = "visceral_fat"
ATTR_WATER = "water"
ATTR_LAST_MEASUREMENT_TIME = "last_measurement_time"

# Units of Measurement
UNIT_POUNDS = "lb"

# Problem States
PROBLEM_NONE = "none"

# Startup Message
STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

# Constraints
CONSTRAINT_HEIGHT_MIN = 50
CONSTRAINT_HEIGHT_MAX = 220
CONSTRAINT_IMPEDANCE_MIN = 50
CONSTRAINT_IMPEDANCE_MAX = 3000
CONSTRAINT_WEIGHT_MIN = 10
CONSTRAINT_WEIGHT_MAX = 200

# Other Constants
COMPONENT = "component"
HANDLERS = "handlers"
MIN = "min"
MAX = "max"
PLATFORMS: set[Platform] = {Platform.SENSOR}
UPDATE_DELAY = 2.0

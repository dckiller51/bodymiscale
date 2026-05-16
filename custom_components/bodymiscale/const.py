"""Constants for bodymiscale."""

from homeassistant.const import Platform

MIN_REQUIRED_HA_VERSION = "2026.3.0"
NAME = "BodyMiScale"
DOMAIN = "bodymiscale"
VERSION = "2026.5.6"
ISSUE_URL = "https://github.com/dckiller51/bodymiscale/issues"

# System keys for hass.data[DOMAIN]
COMPONENT = "component"
HANDLERS = "handlers"
MAIN_ENTITIES = "main_entities"
NOTIFICATION_COORDINATOR = "notification_coordinator"

# User config
CONF_BIRTHDAY = "birthday"
CONF_GENDER = "gender"
CONF_HEIGHT = "height"
CONF_SCALE = "scale"

# ---------------------------------------------------------------------------
# Profile identification method
# ---------------------------------------------------------------------------
# none           : accept all measurements (default, backward-compatible)
# profile_id     : filter by numeric ID from scale sensor
# weight_range   : filter by half-open interval [min, max[
# nearest_weight : filter by nearest current user weight
# notification   : interactive mobile notification, user taps their name
CONF_PROFILE_METHOD = "profile_method"
PROFILE_METHOD_NONE = "none"
PROFILE_METHOD_ID = "profile_id"
PROFILE_METHOD_WEIGHT = "weight_range"
PROFILE_METHOD_NEAREST = "nearest_weight"
PROFILE_METHOD_NOTIFY = "notification"
PROFILE_METHOD_OPTIONS = [
    PROFILE_METHOD_NONE,
    PROFILE_METHOD_ID,
    PROFILE_METHOD_WEIGHT,
    PROFILE_METHOD_NEAREST,
    PROFILE_METHOD_NOTIFY,
]

# Method 1: profile ID
CONF_SENSOR_PROFILE_ID = "profile_id_sensor"
CONF_PROFILE_ID = "profile_id"
CONSTRAINT_PROFILE_ID_MIN = 1
CONSTRAINT_PROFILE_ID_MAX = 5

# Method 2: weight range [min, max[
CONF_WEIGHT_MIN = "weight_min"
CONF_WEIGHT_MAX = "weight_max"

# Method 3: nearest current weight
CONF_INITIAL_WEIGHT = "initial_weight"
CONF_NEAREST_TOLERANCE = "nearest_tolerance"

# Method 4: notification
CONF_NOTIFY_DEVICE_ID = "notify_device_id"
CONF_NOTIFY_SERVICE = "notify_service"
CONF_NOTIFY_WEIGHT_MIN = "notify_weight_min"
CONF_NOTIFY_WEIGHT_MAX = "notify_weight_max"
PENDING_MEASUREMENT_TIMEOUT = 300
EVENT_MOBILE_APP_NOTIFICATION_ACTION = "mobile_app_notification_action"
NOTIFICATION_TAG = "bodymiscale_user_selection"

# ---------------------------------------------------------------------------
# Calculation mode (standard impedance only; dual mode uses fixed formulas)
# xiaomi  : Zepp Life / Mi Fit proprietary algorithm
# science : OMS / Schofield / Janmahasatian
CONF_CALCULATION_MODE = "calculation_mode"
ALGO_XIAOMI = "xiaomi"
ALGO_SCIENCE = "science"
CALCULATION_MODE_OPTIONS = [ALGO_XIAOMI, ALGO_SCIENCE]

# Impedance mode
# none          : non-impedance scale (Xiaomi Gen1)
# standard      : single impedance (Xiaomi Gen2)
# dual_frequency: dual frequency 50+250 kHz (Xiaomi S400)
CONF_IMPEDANCE_MODE = "impedance_mode"
IMPEDANCE_MODE_NONE = "none"
IMPEDANCE_MODE_STANDARD = "standard"
IMPEDANCE_MODE_DUAL = "dual_frequency"
IMPEDANCE_MODE_OPTIONS = [
    IMPEDANCE_MODE_NONE,
    IMPEDANCE_MODE_STANDARD,
    IMPEDANCE_MODE_DUAL,
]

# Sensor entity IDs
CONF_SENSOR_WEIGHT = "weight"
CONF_SENSOR_IMPEDANCE = "impedance"
CONF_SENSOR_IMPEDANCE_LOW = "impedance_low"
CONF_SENSOR_IMPEDANCE_HIGH = "impedance_high"

# State attributes
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
ATTR_LAST_MEASUREMENT_TIME = "last_measurement_time"
ATTR_LBM = "lean_body_mass"
ATTR_METABOLIC = "metabolic_age"
ATTR_MUSCLE = "muscle_mass"
ATTR_PROBLEM = "problem"
ATTR_PROTEIN = "protein"
ATTR_VISCERAL = "visceral_fat"
ATTR_WATER = "water"
ATTR_EXTRACELLULAR_WATER = "extracellular_water"
ATTR_INTRACELLULAR_WATER = "intracellular_water"
ATTR_ECW_TBW_RATIO = "ecw_tbw_ratio"
ATTR_BCM = "bcm"
ATTR_SKELETAL_MUSCLE_MASS = "skeletal_muscle_mass"

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

# Validation constraints
CONSTRAINT_HEIGHT_MIN = 50
CONSTRAINT_HEIGHT_MAX = 220
CONSTRAINT_IMPEDANCE_MIN = 50
CONSTRAINT_IMPEDANCE_MAX = 3000
CONSTRAINT_WEIGHT_MIN = 10
CONSTRAINT_WEIGHT_MAX = 200

# Home Assistant
PLATFORMS: set[Platform] = {Platform.SENSOR}

# Debounce delays
# waits for all sensors to settle before recalculating
RECALCULATION_DEBOUNCE: float = 5.0
UPDATE_DELAY: float = 2.0  # waits before writing state to HA

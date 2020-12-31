"""Constants for bodymiscale."""
__version__ = "1.0.1"

DEFAULT_NAME = "bodymiscale"

ATTR_PROBLEM = "problem"
ATTR_SENSORS = "sensors"
PROBLEM_NONE = "none"
ATTR_AGE = "age"
ATTR_BMI = "bmi"
ATTR_BMR = "bmr"
ATTR_IDEAL = "ideal"
ATTR_IMCLABEL = "IMC Label"

# we're not returning only one value, we're returning a dict here. So we need
# to have a separate literal for it to avoid confusion.
ATTR_DICT_OF_UNITS_OF_MEASUREMENT = "unit_of_measurement_dict"

CONF_SENSOR_WEIGHT = "weight"
CONF_HEIGHT = "height"
CONF_BORN = "born"
CONF_GENDER = "gender"

DEFAULT_WEIGHT = 40
DEFAULT_HEIGHT = 40
DEFAULT_BORN = "1990-01-01"
DEFAULT_GENDER = "female"

CURRENCY_ATTRIBUTE = [
    "lbm",
    "fat",
    "water",
    "bones",
    "muscle",
    "visceral",
    "imc",
    "bmr",
    "ideal",
    "fatmassideal",
    "protein",
    "body",
    "imclabel",
    "lbm",
    "fat",
    "water",
    "bones",
    "muscle",
    "visceral",
    "imc",
    "bmr",
    "ideal",
    "fatlabel",
    "fatmassideal",
    "protein",
    "body",
    "imclabel",
]
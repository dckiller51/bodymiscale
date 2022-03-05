"""Models module."""
from enum import Enum


class Gender(str, Enum):
    """Gender enum."""

    MALE = "male"
    FEMALE = "female"

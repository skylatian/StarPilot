"""Saved startup settings for TOYOTA_COROLLA_RETROFIT, read once and applied through opendbc."""

from opendbc.car.toyota.retrofit import (SAS_OFFSET_DEFAULT_DEG, SAS_OFFSET_KEY, STEER_ANGLE_DEADZONE_DEFAULT_DEG,
                                         STEER_ANGLE_DEADZONE_KEY, sas_offset_deg, steer_angle_deadzone_deg)
from openpilot.starpilot.saved_source import read_saved

MAX_BYTES = 32


def _saved_float(params, key: str):
  """Saved text, or None when the key is unset or unreadable."""
  try:
    raw, readable = read_saved(params, key, MAX_BYTES)
    if not readable or raw is None:
      return None
    return float(raw.decode("ascii").strip())
  except (OSError, TypeError, ValueError, UnicodeError, OverflowError):
    return None


def sas_offset(params) -> float:
  value = _saved_float(params, SAS_OFFSET_KEY)
  return SAS_OFFSET_DEFAULT_DEG if value is None else sas_offset_deg(value)


def steer_angle_deadzone(params) -> float:
  value = _saved_float(params, STEER_ANGLE_DEADZONE_KEY)
  return STEER_ANGLE_DEADZONE_DEFAULT_DEG if value is None else steer_angle_deadzone_deg(value)

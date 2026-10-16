"""TOYOTA_COROLLA_RETROFIT startup settings.

openpilot reads the saved values once at startup (openpilot/starpilot/car/toyota/retrofit_preferences.py)
and applies them here. Every function is a no-op on any other platform. A missing, unreadable,
non-finite or out-of-range value falls back to its default.
"""
import math

from opendbc.car.toyota.values import CAR

SAS_OFFSET_KEY = "RetrofitSASOffset"
SAS_OFFSET_DEFAULT_DEG = 0.0
SAS_OFFSET_LIMIT_DEG = 180.0


def is_retrofit(cp) -> bool:
  return bool(cp.brand == "toyota" and cp.carFingerprint == CAR.TOYOTA_COROLLA_RETROFIT)


def _bounded(value, low: float, high: float, default: float) -> float:
  try:
    value = float(value)
  except (TypeError, ValueError, OverflowError):
    return default
  return value if math.isfinite(value) and low <= value <= high else default


def sas_offset_deg(value) -> float:
  return _bounded(value, -SAS_OFFSET_LIMIT_DEG, SAS_OFFSET_LIMIT_DEG, SAS_OFFSET_DEFAULT_DEG)


def apply_sas_offset(car_state, value) -> bool:
  """Degrees subtracted from the raw STEER_ANGLE_SENSOR angle, before the angle-offset filter."""
  if not is_retrofit(car_state.CP):
    return False
  car_state.sas_offset_deg = sas_offset_deg(value)
  return True

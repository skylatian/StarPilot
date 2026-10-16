"""TOYOTA_COROLLA_RETROFIT startup settings.

openpilot reads the saved values once at startup (openpilot/starpilot/car/toyota/retrofit_preferences.py)
and applies them here. Every function is a no-op on any other platform. A missing, unreadable,
non-finite or out-of-range value falls back to its default.
"""
import math

from opendbc.car import structs
from opendbc.car.toyota.values import CAR

SAS_OFFSET_KEY = "RetrofitSASOffset"
SAS_OFFSET_DEFAULT_DEG = 0.0
SAS_OFFSET_LIMIT_DEG = 180.0

STEER_ANGLE_DEADZONE_KEY = "RetrofitSteerAngleDeadzone"
STEER_ANGLE_DEADZONE_DEFAULT_DEG = 0.3
STEER_ANGLE_DEADZONE_RANGE_DEG = (0.0, 2.0)


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


def steer_angle_deadzone_deg(value) -> float:
  return _bounded(value, *STEER_ANGLE_DEADZONE_RANGE_DEG, STEER_ANGLE_DEADZONE_DEFAULT_DEG)


def apply_steer_angle_deadzone(cp: structs.CarParams, value) -> bool:
  """Center deadzone of the torque controller's friction term. Frozen into CarParams, so it
  must be applied before CarParams is published; a change takes effect on the next startup."""
  if not is_retrofit(cp) or cp.steerControlType != structs.CarParams.SteerControlType.torque or \
     cp.lateralTuning.which() != "torque":
    return False
  cp.lateralTuning.torque.steeringAngleDeadzoneDeg = steer_angle_deadzone_deg(value)
  return True


def apply_sas_offset(car_state, value) -> bool:
  """Degrees subtracted from the raw STEER_ANGLE_SENSOR angle, before the angle-offset filter."""
  if not is_retrofit(car_state.CP):
    return False
  car_state.sas_offset_deg = sas_offset_deg(value)
  return True

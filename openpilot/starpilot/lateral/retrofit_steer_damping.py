"""TOYOTA_COROLLA_RETROFIT: derivative damping (KD) on the torque controller, at highway speed.

The retrofit's hydraulic rack sticks and breaks away: on the highway the wheel held still for ~0.5 s, then jumped
~1.9 deg, 16 times a minute (2026-10-25 long drive). KD opposes the measured lateral acceleration rate, as a PID D
term with error_rate = -measurement_rate (the Corolla TSS2 and GV70 policies' convention, with their 2 Hz filter and
+/-MAX_LAT_JERK_UP clip), so the torque built up against the stuck column backs off as soon as the wheel moves. It
fades in from 15 to 20 m/s; the low-speed unwind is a separate problem.

It runs after LatControlTorque.update_standard and before Auto Learn's output stage, on the STANDARD controller only,
so the controller mode, policy identity and every learning path stay what they are without it. With KD 0, the
default, the output is the STANDARD controller's, unchanged. The gain is the saved RetrofitSteerKD: read when the
controller is built (controlsd, and Auto Learn's replay process), then refreshed about once a second by KDOwner
from controlsd.

Kept in this one file plus two lines in latcontrol_torque.py and controlsd.py, so it drops cleanly.
"""

import math
import time

import numpy as np

from opendbc.car import structs
from opendbc.car.toyota.retrofit import is_retrofit
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.swaglog import cloudlog
from openpilot.starpilot.lateral.controller_selection import ControllerMode
from openpilot.starpilot.lateral.torque_shaping import MAX_LAT_JERK_UP
from openpilot.starpilot.saved_source import read_saved

KD_KEY = "RetrofitSteerKD"
KD_DEFAULT = 0.0
KD_RANGE = (0.0, 1.0)  # seconds: m/s^2 of lateral accel per m/s^3 of measured rate
KD_SPEED_BP = [15.0, 20.0]  # m/s
KD_SPEED_V = [0.0, 1.0]
RATE_CUTOFF_HZ = MAX_LAT_JERK_UP - 0.5
REFRESH_NS = 1_000_000_000
MAX_BYTES = 32


def supported_cp(cp) -> bool:
  return bool(is_retrofit(cp) and not cp.notCar and not cp.passive and not cp.dashcamOnly and
              cp.steerControlType == structs.CarParams.SteerControlType.torque and cp.lateralTuning.which() == "torque")


def kd_value(value) -> float:
  try:
    value = float(value)
  except (TypeError, ValueError, OverflowError):
    return KD_DEFAULT
  return value if math.isfinite(value) and KD_RANGE[0] <= value <= KD_RANGE[1] else KD_DEFAULT


def read_kd(params) -> float:
  """Saved RetrofitSteerKD; the default when unset, unreadable, non-finite or out of range."""
  try:
    raw, readable = read_saved(params, KD_KEY, MAX_BYTES)
    if not readable or raw is None:
      return KD_DEFAULT
    return kd_value(raw.decode("ascii").strip())
  except (OSError, TypeError, ValueError, UnicodeError):
    return KD_DEFAULT


def _saved_kd() -> float:
  try:
    from openpilot.common.params import Params
    return read_kd(Params())
  except Exception:
    return KD_DEFAULT


class RetrofitSteerDamping:
  def __init__(self, dt, kd=KD_DEFAULT):
    self.dt = dt
    self.kd = kd_value(kd)
    self.measurement_rate_filter = FirstOrderFilter(0.0, 1 / (2 * np.pi * RATE_CUTOFF_HZ), dt)
    self.previous_measurement = 0.0
    self.rate_primed = False

  def apply(self, controller, active, cs, result):
    """result: update_standard's (steer, lateral_output, pid_log), where steer = -output_torque."""
    steer, lateral_output, pid_log = result
    if not active:
      self.rate_primed = False
      self.measurement_rate_filter.x = 0.0
      return result

    # Track the rate on every active frame, so a gain set mid-drive starts from a settled filter
    measurement = float(pid_log.actualLateralAccel)
    if not self.rate_primed:
      self.previous_measurement = measurement
      self.rate_primed = True
    measurement_rate = self.measurement_rate_filter.update((measurement - self.previous_measurement) / self.dt)
    measurement_rate = float(np.clip(measurement_rate, -MAX_LAT_JERK_UP, MAX_LAT_JERK_UP))
    self.previous_measurement = measurement

    kd = self.kd * float(np.interp(cs.vEgo, KD_SPEED_BP, KD_SPEED_V))
    if kd == 0.0:
      return result

    # The D term adds in the PID's lat-accel space and converts like the rest of its output.
    # pid_log.saturated keeps the STANDARD value: _check_saturation is stateful and runs once per frame.
    d = -kd * measurement_rate
    output_torque = -steer + controller.torque_from_lateral_accel(d, controller.torque_params)
    output_torque = float(np.clip(output_torque, -controller.steer_max, controller.steer_max))
    pid_log.d = float(d)
    pid_log.output = float(-output_torque)
    return -output_torque, lateral_output, pid_log


def create(cp, controller_mode, dt):
  """None on every other car, and on the retrofit if a vehicle policy ever replaces the STANDARD path."""
  if not supported_cp(cp) or ControllerMode(controller_mode) != ControllerMode.STANDARD:
    return None
  return RetrofitSteerDamping(dt, _saved_kd())


class KDOwner:
  """Applies the saved gain to the running stage, at most once a second (controlsd)."""

  def __init__(self, params, damping):
    self.params = params
    self.damping = damping
    self.last_refresh_ns = None
    self.refresh()

  def refresh(self, *, now_ns=None) -> None:
    now_ns = time.monotonic_ns() if now_ns is None else now_ns
    if self.last_refresh_ns is not None and 0 <= now_ns - self.last_refresh_ns < REFRESH_NS:
      return
    self.last_refresh_ns = now_ns
    kd = read_kd(self.params)
    if kd != self.damping.kd:
      cloudlog.event("retrofit_steer_kd", kd=kd, previous=self.damping.kd)
      self.damping.kd = kd


def create_kd_owner(params, controller):
  damping = getattr(controller, "retrofit_damping", None)
  return None if damping is None else KDOwner(params, damping)

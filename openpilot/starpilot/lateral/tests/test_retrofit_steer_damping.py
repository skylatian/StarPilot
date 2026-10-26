"""TOYOTA_COROLLA_RETROFIT derivative damping (RetrofitSteerKD) on the STANDARD torque controller."""

import math
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from opendbc.car import gen_empty_fingerprint
from opendbc.car.car_helpers import interfaces
from opendbc.car.structs import car
from opendbc.car.toyota.values import CAR
from opendbc.car.vehicle_model import VehicleModel
from openpilot.cereal import log
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.starpilot.flm.learning_source import automatic_capability
from openpilot.starpilot.lateral import retrofit_steer_damping as damping
from openpilot.starpilot.lateral.controller_selection import ControllerMode, default_selection, policy_for


def car_params(fingerprint=CAR.TOYOTA_COROLLA_RETROFIT):
  return interfaces[fingerprint].get_params(fingerprint, gen_empty_fingerprint(), [], False, False, False)


def controller(cp, mode=None):
  return LatControlTorque(cp.as_reader(), interfaces[cp.carFingerprint](cp), DT_CTRL, controller_mode=mode)


def save_raw(key, raw):
  Path(Params().get_param_path(key)).write_bytes(raw)


def drive(lac, cp, speeds, angles, curvature=0.0):
  """Run the controller over a wheel-angle trace; returns (steer, pid_log) per frame."""
  vm = VehicleModel(cp)
  params = log.VehicleParameters.new_message()
  params.steerRatio, params.stiffnessFactor = cp.steerRatio, 1.0
  vm.update_params(1.0, cp.steerRatio)
  out = []
  for v, angle in zip(speeds, angles, strict=True):
    cs = car.CarState.new_message(vEgo=float(v), steeringAngleDeg=float(angle))
    steer, _, pid_log = lac.update(True, cs, vm, params, False, curvature, False, 0.3)
    out.append((steer, pid_log.as_reader()))
  return out


def breakaway(n=300, start=100, jump_deg=2.0, jump_frames=15):
  """A wheel held still, then a 2 deg breakaway over 0.15 s, then held again."""
  a = np.zeros(n)
  a[start:start + jump_frames] = np.linspace(0, jump_deg, jump_frames)
  a[start + jump_frames:] = jump_deg
  return a


class TestRetrofitSteerDamping(unittest.TestCase):
  def test_param_registered_with_a_zero_default(self):
    self.assertEqual(Params().get_type(damping.KD_KEY).name, "FLOAT")
    self.assertAlmostEqual(Params().get_default_value(damping.KD_KEY), damping.KD_DEFAULT)

  def test_saved_gain_is_bounded(self):
    with OpenpilotPrefix():
      params = Params()
      self.assertEqual(damping.read_kd(params), 0.0)  # unset
      for raw, expected in ((b"0.3", 0.3), (b" 0.5\n", 0.5), (b"1.0", 1.0), (b"0", 0.0), (b"-0.1", 0.0), (b"1.5", 0.0),
                            (b"nan", 0.0), (b"inf", 0.0), (b"abc", 0.0), (b"\xff", 0.0), (b"0." + b"1" * 40, 0.0)):
        save_raw(damping.KD_KEY, raw)
        self.assertEqual(damping.read_kd(params), expected, raw)

  def test_scoped_to_the_retrofit_standard_controller(self):
    cp = car_params()
    self.assertIsNotNone(controller(cp).retrofit_damping)
    self.assertIsNone(damping.create(cp.as_reader(), ControllerMode.STARPILOT, DT_CTRL))
    for other in (CAR.TOYOTA_COROLLA, CAR.TOYOTA_COROLLA_TSS2, CAR.TOYOTA_RAV4):
      self.assertIsNone(controller(car_params(other)).retrofit_damping, other)

  def test_controller_mode_and_learning_identity_unchanged(self):
    # A vehicle policy would switch the retrofit to STARPILOT mode, which has no scalar automatic fit and changes
    # torqued's learning with saved manual values. The damping stage keeps all of that as it was.
    cp = car_params().as_reader()
    self.assertIsNone(policy_for(cp))
    self.assertEqual(default_selection(cp).mode, ControllerMode.STANDARD)
    self.assertIsNotNone(automatic_capability(cp, ControllerMode.STANDARD))
    self.assertIsNone(controller(car_params()).controller_policy)

  def test_zero_gain_is_the_standard_output(self):
    cp = car_params()
    speeds, angles = np.full(300, 30.0), breakaway()
    with_stage = controller(cp)
    without = controller(cp)
    without.retrofit_damping = None
    for (a, la), (b, lb) in zip(drive(with_stage, cp, speeds, angles, 0.0005), drive(without, cp, speeds, angles, 0.0005), strict=True):
      self.assertEqual(a, b)
      self.assertEqual(la.to_dict(), lb.to_dict())

  def test_damping_opposes_the_breakaway(self):
    cp = car_params()
    speeds, angles = np.full(300, 30.0), breakaway()
    base = drive(controller(cp), cp, speeds, angles)
    lac = controller(cp)
    lac.retrofit_damping.kd = 0.3
    damped = drive(lac, cp, speeds, angles)
    # During and just after the jump the measured lat accel moves; D opposes that motion
    meas_rate = np.diff([lg.actualLateralAccel for _, lg in base])
    window = slice(100, 140)
    d = np.array([lg.d for _, lg in damped])[window]
    self.assertTrue(np.all(np.sign(d[np.abs(d) > 1e-4]) == -np.sign(np.sum(meas_rate[window]))))
    self.assertGreater(np.max(np.abs(d)), 0.05)
    # The torque difference is exactly the D term through the linear torque map
    for (a, _), (b, lg) in zip(base[window], damped[window], strict=True):
      self.assertAlmostEqual(-b - -a, lg.d / lac.torque_params.latAccelFactor, places=6)
    # Before the wheel moves and after the filter settles, nothing changes
    self.assertEqual(damped[50][0], base[50][0])
    self.assertAlmostEqual(damped[299][0], base[299][0], places=3)

  def test_fades_in_with_speed(self):
    cp = car_params()
    angles = breakaway()
    peaks = {}
    for v in (10.0, 15.0, 17.5, 20.0, 30.0):
      lac = controller(cp)
      lac.retrofit_damping.kd = 0.3
      peaks[v] = max(abs(lg.d) for _, lg in drive(lac, cp, np.full(300, v), angles))
    self.assertEqual(peaks[10.0], 0.0)
    self.assertEqual(peaks[15.0], 0.0)
    self.assertGreater(peaks[17.5], 0.0)
    self.assertGreater(peaks[20.0], peaks[17.5])

  def test_inactive_resets_the_rate(self):
    cp = car_params()
    lac = controller(cp)
    lac.retrofit_damping.kd = 0.3
    drive(lac, cp, np.full(50, 30.0), np.linspace(0, 5, 50))
    self.assertNotEqual(lac.retrofit_damping.measurement_rate_filter.x, 0.0)
    vm = VehicleModel(cp)
    lac.update(False, car.CarState.new_message(vEgo=30.0), vm, log.VehicleParameters.new_message(), False, 0.0, False, 0.3)
    self.assertEqual(lac.retrofit_damping.measurement_rate_filter.x, 0.0)
    self.assertFalse(lac.retrofit_damping.rate_primed)
    # Re-engaging at a different angle doesn't see a step as a rate
    _, lg = drive(lac, cp, [30.0], [-10.0])[0]
    self.assertEqual(lg.d, 0.0)

  def test_output_stays_within_steer_max(self):
    cp = car_params()
    lac = controller(cp)
    lac.retrofit_damping.kd = 1.0
    for steer, _ in drive(lac, cp, np.full(200, 35.0), np.r_[np.zeros(100), np.linspace(0, -60, 100)], 0.01):
      self.assertLessEqual(abs(steer), lac.steer_max)

  def test_gain_read_at_build_and_refreshed_once_a_second(self):
    with OpenpilotPrefix():
      params = Params()
      save_raw(damping.KD_KEY, b"0.3")
      lac = controller(car_params())
      self.assertEqual(lac.retrofit_damping.kd, 0.3)
      with patch.object(damping.cloudlog, "event") as event:
        owner = damping.create_kd_owner(params, lac)
        owner.refresh(now_ns=0)
        save_raw(damping.KD_KEY, b"0.5")
        owner.refresh(now_ns=500_000_000)
        self.assertEqual(lac.retrofit_damping.kd, 0.3)
        owner.refresh(now_ns=1_000_000_000)
        self.assertEqual(lac.retrofit_damping.kd, 0.5)
        event.assert_called_once_with("retrofit_steer_kd", kd=0.5, previous=0.3)
        save_raw(damping.KD_KEY, b"garbage")
        owner.refresh(now_ns=2_000_000_000)
        self.assertEqual(lac.retrofit_damping.kd, 0.0)
    self.assertIsNone(damping.create_kd_owner(None, controller(car_params(CAR.TOYOTA_COROLLA))))

  def test_controlsd_refreshes_the_owner(self):
    source = Path(__file__).parents[3] / "selfdrive/controls/controlsd.py"
    text = source.read_text()
    self.assertIn("self.retrofit_kd_owner = create_kd_owner(self.params, self.LaC)", text)
    self.assertIn("retrofit_kd_owner.refresh()", text)
    self.assertTrue(math.isfinite(damping.RATE_CUTOFF_HZ) and damping.RATE_CUTOFF_HZ == 2.0)


if __name__ == "__main__":
  unittest.main()

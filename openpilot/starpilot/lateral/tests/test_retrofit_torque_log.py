"""TOYOTA_COROLLA_RETROFIT logs the torque values its lateral controller applies."""

import math
import os
import unittest
from unittest.mock import patch

from opendbc.car import gen_empty_fingerprint
from opendbc.car.car_helpers import interfaces
from opendbc.car.toyota.values import CAR
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.starpilot.lateral import retrofit_torque_log
from openpilot.starpilot.lateral.lane_feedback import feedback_message
from openpilot.starpilot.lateral.torque_runtime import TorqueHost


def car_params(fingerprint=CAR.TOYOTA_COROLLA_RETROFIT):
  return interfaces[fingerprint].get_params(fingerprint, gen_empty_fingerprint(), [], False, False, False)


def save_custom_factor(cp, factor):
  tune = cp.lateralTuning.torque
  document = {"schemaVersion": 1, "vehicles": {str(cp.carFingerprint): {
    "basis": {"friction": tune.friction, "latAccelFactor": tune.latAccelFactor, "latAccelOffset": tune.latAccelOffset},
    "factor": {"customValue": factor, "mode": "custom"},
    "friction": {"customValue": None, "mode": "source"}}}}
  Params().put("TorqueOverrideDocument", document, block=True)


def controller(cp):
  return LatControlTorque(cp.as_reader(), interfaces[cp.carFingerprint](cp), DT_CTRL)


def lateral_state():
  return feedback_message(None, 0.0, True, model_mono_time=0, car_control_mono_time=0, valid=True).starpilotLateralState


class TestRetrofitTorqueLog(unittest.TestCase):
  def test_scoped_to_the_retrofit_torque_controller(self):
    cp = car_params()
    self.assertTrue(retrofit_torque_log.supported(cp, controller(cp)))
    stock = car_params(CAR.TOYOTA_COROLLA)
    self.assertFalse(retrofit_torque_log.supported(stock, controller(stock)))
    self.assertFalse(retrofit_torque_log.supported(cp, object()))

  def test_without_a_torque_host_logs_the_startup_values(self):
    cp = car_params()
    state = lateral_state()
    retrofit_torque_log.write(state, controller(cp), None)
    applied = state.retrofitAppliedTorque
    tune = cp.lateralTuning.torque
    self.assertAlmostEqual(applied.latAccelFactor, tune.latAccelFactor, places=5)
    self.assertAlmostEqual(applied.friction, tune.friction, places=5)
    self.assertEqual(applied.source, 'native')
    self.assertTrue(math.isnan(applied.userFactor) and math.isnan(applied.userFriction))

  def test_custom_factor_is_logged_once_applied(self):
    # The 2026-10-24 drive: 6.075 set in the torque settings while the learner reported 4.05.
    with OpenpilotPrefix():
      cp = car_params()
      save_custom_factor(cp, 6.075)
      host, lac = TorqueHost(Params(), cp, allow_learning=False), controller(cp)
      state = lateral_state()
      for frame in range(1, 300):
        tune = host.sample(None, now_ns=frame * 10_000_000, lat_active=True)
        host.apply(lac, tune)
      retrofit_torque_log.write(state, lac, host)
      applied = state.retrofitAppliedTorque
      self.assertAlmostEqual(applied.latAccelFactor, 6.075, places=4)
      self.assertAlmostEqual(applied.userFactor, 6.075, places=4)
      self.assertTrue(math.isnan(applied.userFriction))
      self.assertEqual(applied.source, 'user')
      # A higher factor means less torque for the same lateral acceleration.
      self.assertAlmostEqual(lac.torque_from_lateral_accel(1.0, lac.torque_params), 1 / 6.075, places=5)

  def test_lateral_inactive_falls_back_to_the_vehicle_values(self):
    with OpenpilotPrefix():
      cp = car_params()
      save_custom_factor(cp, 6.075)
      host, lac = TorqueHost(Params(), cp, allow_learning=False), controller(cp)
      host.apply(lac, host.sample(None, now_ns=10_000_000, lat_active=False))
      state = lateral_state()
      retrofit_torque_log.write(state, lac, host)
      self.assertAlmostEqual(state.retrofitAppliedTorque.latAccelFactor, cp.lateralTuning.torque.latAccelFactor, places=5)
      self.assertEqual(state.retrofitAppliedTorque.source, 'vehicle')

  def test_controlsd_writes_it_only_for_the_retrofit(self):
    from openpilot.selfdrive.controls.controlsd import Controls
    for fingerprint, expected in ((CAR.TOYOTA_COROLLA_RETROFIT, True), (CAR.TOYOTA_COROLLA, False)):
      with self.subTest(fingerprint=fingerprint), OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
        cp = car_params(fingerprint)
        save_custom_factor(cp, 6.075)
        Params().put("CarParams", cp.to_bytes(), block=True)
        controls = Controls()
        self.assertEqual(controls.retrofit_torque_log is not None, expected)
        if expected:
          self.assertIsNotNone(controls.torque_host)
        del controls


if __name__ == '__main__':
  unittest.main()

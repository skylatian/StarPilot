from pathlib import Path
import tempfile
import unittest

from opendbc.car import gen_empty_fingerprint
from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.values import CAR
from openpilot.common.params import Params
from openpilot.starpilot.car.toyota import retrofit_preferences
from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences


class TestRetrofitPreferences(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)

  def raw(self, key, value):
    path = Path(self.params.get_param_path(key))
    if value is None:
      path.unlink(missing_ok=True)
    else:
      path.write_bytes(value)

  def test_keys_are_registered_with_defaults(self):
    self.assertEqual(self.params.get_default_value("RetrofitSASOffset"), 0.0)
    self.assertAlmostEqual(self.params.get_default_value("RetrofitSteerAngleDeadzone"), 0.3, places=5)

  def test_unset_keys_use_defaults(self):
    self.assertEqual(retrofit_preferences.sas_offset(self.params), 0.0)
    self.assertEqual(retrofit_preferences.steer_angle_deadzone(self.params), 0.3)

  def test_saved_values(self):
    for raw, expected in ((b"-48", -48.), (b"-48.0", -48.), (b"12.5", 12.5), (b"180", 180.), (b"-180.0", -180.),
                          (b"-180.5", 0.), (b"nan", 0.), (b"inf", 0.), (b"", 0.), (b"abc", 0.), (b"1" * 40, 0.)):
      with self.subTest(raw=raw):
        self.raw("RetrofitSASOffset", raw)
        self.assertEqual(retrofit_preferences.sas_offset(self.params), expected)
    for raw, expected in ((b"0.8", 0.8), (b"0", 0.), (b"2.0", 2.), (b"2.5", 0.3), (b"-0.1", 0.3), (b"x", 0.3)):
      with self.subTest(raw=raw):
        self.raw("RetrofitSteerAngleDeadzone", raw)
        self.assertEqual(retrofit_preferences.steer_angle_deadzone(self.params), expected)

  def test_startup_preferences_apply_only_to_retrofit(self):
    self.raw("RetrofitSASOffset", b"-48")
    self.raw("RetrofitSteerAngleDeadzone", b"0.8")
    for enabled in (True, False):
      preferences = VehicleStartupPreferences.read(self.params, enabled=enabled)
      self.assertEqual(preferences.toyota_retrofit_sas_offset, -48.)
      self.assertEqual(preferences.toyota_retrofit_steer_deadzone, 0.8)
      for car, deadzone, offset in ((CAR.TOYOTA_COROLLA_RETROFIT, 0.8, -48.), (CAR.TOYOTA_COROLLA, 0., 0.)):
        with self.subTest(enabled=enabled, car=car):
          cp = preferences.prepare(CarInterface.get_params(car, gen_empty_fingerprint(), [], False, False, False))
          ci = CarInterface(cp)
          preferences.finalize(cp)
          preferences.configure_controller(ci)
          self.assertAlmostEqual(cp.lateralTuning.torque.steeringAngleDeadzoneDeg, deadzone, places=5)
          self.assertEqual(ci.CS.sas_offset_deg, offset)

  def test_defaults_without_saved_values(self):
    preferences = VehicleStartupPreferences.read(self.params, enabled=True)
    cp = preferences.prepare(CarInterface.get_params(CAR.TOYOTA_COROLLA_RETROFIT, gen_empty_fingerprint(), [], False, False, False))
    ci = CarInterface(cp)
    preferences.configure_controller(ci)
    self.assertAlmostEqual(cp.lateralTuning.torque.steeringAngleDeadzoneDeg, 0.3, places=5)
    self.assertEqual(ci.CS.sas_offset_deg, 0.)


if __name__ == "__main__":
  unittest.main()

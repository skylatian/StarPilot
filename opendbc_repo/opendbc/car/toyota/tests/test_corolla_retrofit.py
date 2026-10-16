"""TOYOTA_COROLLA_RETROFIT gates. Every test checks the retrofit and TOYOTA_COROLLA side by side."""
import unittest

from opendbc.car import Bus
from opendbc.car.interfaces import get_torque_params
from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.values import CAR, DBC, EPS_SCALE, ToyotaSafetyFlags

RETROFIT = CAR.TOYOTA_COROLLA_RETROFIT
STOCK = CAR.TOYOTA_COROLLA


def empty_fingerprint():
  return {0: {}, 1: {}, 2: {}}


def get_params(car, fingerprint=None, alpha_long=False):
  return CarInterface.get_params(car, fingerprint or empty_fingerprint(), [], alpha_long, False, False)


class TestCorollaRetrofitPlatform(unittest.TestCase):
  def test_dbc_has_no_radar_or_camera_bus(self):
    self.assertEqual(DBC[RETROFIT], {Bus.pt: 'toyota_new_mc_pt_generated'})
    self.assertEqual(DBC[STOCK][Bus.pt], 'toyota_new_mc_pt_generated')
    self.assertIn(Bus.radar, DBC[STOCK])

  def test_radar_unavailable(self):
    self.assertTrue(get_params(RETROFIT).radarUnavailable)
    self.assertFalse(get_params(STOCK).radarUnavailable)

  def test_specs_and_safety_scale(self):
    retrofit, stock = get_params(RETROFIT), get_params(STOCK)
    self.assertAlmostEqual(retrofit.steerRatio, 17.4, places=5)
    self.assertAlmostEqual(stock.steerRatio, 18.27, places=5)
    self.assertEqual(retrofit.mass, stock.mass)
    self.assertEqual(retrofit.wheelbase, stock.wheelbase)
    self.assertEqual(EPS_SCALE[RETROFIT], 88)
    for cp in (retrofit, stock):
      self.assertEqual(cp.safetyConfigs[0].safetyParam & 0xFF, 88)
      self.assertTrue(cp.safetyConfigs[0].safetyParam & ToyotaSafetyFlags.ALT_BRAKE)
      self.assertFalse(cp.dashcamOnly)

  def test_torque_params(self):
    params = get_torque_params()
    self.assertEqual([params[RETROFIT][k] for k in ('LAT_ACCEL_FACTOR', 'MAX_LAT_ACCEL_MEASURED', 'FRICTION')], [4.05, 1.84, 0.15])
    retrofit, stock = get_params(RETROFIT), get_params(STOCK)
    self.assertEqual(retrofit.lateralTuning.which(), 'torque')
    self.assertAlmostEqual(retrofit.lateralTuning.torque.latAccelFactor, 4.05, places=5)
    self.assertAlmostEqual(retrofit.lateralTuning.torque.friction, 0.15, places=5)
    self.assertNotAlmostEqual(stock.lateralTuning.torque.friction, 0.15, places=5)


if __name__ == "__main__":
  unittest.main()

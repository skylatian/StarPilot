"""TOYOTA_COROLLA_RETROFIT gates. Every test checks the retrofit and TOYOTA_COROLLA side by side."""
import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.interfaces import get_torque_params
from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.tests.test_auto_hold import decode
from opendbc.car.toyota.values import CAR, DBC, EPS_SCALE, ToyotaFlags, ToyotaSafetyFlags

RETROFIT = CAR.TOYOTA_COROLLA_RETROFIT
STOCK = CAR.TOYOTA_COROLLA


def empty_fingerprint():
  return {0: {}, 1: {}, 2: {}}


def get_params(car, fingerprint=None, alpha_long=False):
  return CarInterface.get_params(car, fingerprint or empty_fingerprint(), [], alpha_long, False, False)


# What the retrofit's devices put on bus 0 (message: period in 10 ms frames), per the CAN coverage table:
# emulator (PCM stand-in + background), VSS, cruise stalk, real EPS and SAS. Nothing sends LKAS_HUD.
CAR_BUS = {
  'VSC1S07': 2, 'BODY_CONTROL_STATE': 33, 'BRAKE_MODULE': 2, 'ESP_CONTROL': 10, 'PCM_CRUISE': 3,
  'GEAR_PACKET': 10, 'PRE_COLLISION': 3, 'WHEEL_SPEEDS': 1, 'STEER_ANGLE_SENSOR': 1, 'STEER_TORQUE_SENSOR': 2,
  'BLINKERS_STATE': 5, 'EPS_STATUS': 4, 'PCM_CRUISE_2': 3, 'PCM_CRUISE_SM': 10, 'BODY_CONTROL_STATE_2': 10,
  'LIGHT_STALK': 10, 'RSA1': 10,
}


class CarBus:
  """Replays the retrofit's bus 0 into a CarInterface. mirror=True also copies every frame to bus 2,
  as on the car; mirror=False leaves bus 2 silent."""
  def __init__(self, car, mirror=True, values=None, fingerprint=None, alpha_long=False):
    self.CP = get_params(car, fingerprint, alpha_long)
    self.CI = CarInterface(self.CP)
    self.packer = CANPacker(DBC[car][Bus.pt])
    self.mirror = mirror
    self.values = {
      'WHEEL_SPEEDS': {f'WHEEL_SPEED_{w}': 20. for w in ('FL', 'FR', 'RL', 'RR')},
      'GEAR_PACKET': {'GEAR': 0},
      'STEER_TORQUE_SENSOR': {'STEER_ANGLE': 5.},
      'STEER_ANGLE_SENSOR': {'STEER_ANGLE': 5.},
      'EPS_STATUS': {'LKA_STATE': 1},
      'PCM_CRUISE': {'GAS_RELEASED': 1},
      'PCM_CRUISE_2': {'MAIN_ON': 1},
    }
    for name, sigs in (values or {}).items():
      self.values.setdefault(name, {}).update(sigs)
    self.frame = 0
    self.extra = []

  def step(self, extra=None):
    frames = []
    for name, period in CAR_BUS.items():
      if self.frame % period == 0:
        frames.append(self.packer.make_can_msg(name, 0, self.values.get(name, {})))
    frames += list(extra or []) + self.extra
    if self.mirror:
      frames += [(addr, dat, 2) for addr, dat, src in frames if src == 0]
    now = 1_000_000_000 + self.frame * 10_000_000
    self.frame += 1
    return self.CI.update([(now, frames)])

  def run(self, frames, extra=None):
    out = None
    for _ in range(frames):
      out = self.step(extra)
    return out


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


class TestNoCameraParser(unittest.TestCase):
  def test_parsers(self):
    retrofit, stock = CarBus(RETROFIT), CarBus(STOCK)
    self.assertEqual(set(retrofit.CI.can_parsers), {Bus.pt})
    self.assertEqual(set(stock.CI.can_parsers), {Bus.pt, Bus.cam})

  def test_can_valid_with_bus2_mirrored_or_silent(self):
    for mirror in (True, False):
      with self.subTest(mirror=mirror):
        retrofit, stock = CarBus(RETROFIT, mirror=mirror), CarBus(STOCK, mirror=mirror)
        for _ in range(300):
          retrofit_state, stock_state = retrofit.step(), stock.step()
        self.assertTrue(retrofit_state.canValid)
        self.assertFalse(retrofit_state.canTimeout)
        # The same bus on TOYOTA_COROLLA: the camera parser waits for LKAS_HUD, which nobody sends.
        self.assertFalse(stock_state.canValid)
        self.assertEqual(stock_state.canTimeout, not mirror)
        self.assertIn('LKAS_HUD', stock.CI.can_parsers[Bus.cam].vl)

  def test_lkas_hud_tx_uses_static_defaults(self):
    from opendbc.car import structs
    for car in (RETROFIT, STOCK):
      bus = CarBus(car)
      bus.run(150)
      CC = structs.CarControl()
      CC.enabled = CC.latActive = True
      _, sends = bus.CI.apply(CC.as_reader(), 2_500_000_000)
      hud = next(frame for frame in sends if frame[0] == 0x412)
      decoded = decode(bus.CP, hud, 'LKAS_HUD')
      if car == RETROFIT:
        self.assertEqual(bus.CI.CS.lkas_hud, {})
        self.assertEqual((decoded['LANE_SWAY_FLD'], decoded['LANE_SWAY_SENSITIVITY'], decoded['LANE_SWAY_TOGGLE']), (7, 2, 1))
      else:
        # TOYOTA_COROLLA copies the (never received, zero-filled) bus-2 LKAS_HUD into the TX
        self.assertEqual(bus.CI.CS.lkas_hud['LANE_SWAY_FLD'], 0)
        self.assertEqual(decoded['LANE_SWAY_FLD'], 0)


# The car's fingerprint: bus 2 holds the bus-0 mirror, including the emulated EPS-init 0x4CB
MIRRORED_FINGERPRINT = {0: {0x4CB: 8, 0x1D2: 8, 0x260: 8}, 1: {}, 2: {0x4CB: 8, 0x1D2: 8, 0x260: 8}}


class TestNoDsuBypassDetection(unittest.TestCase):
  def test_mirrored_eps_init_is_not_a_bypass(self):
    for fingerprint in (MIRRORED_FINGERPRINT, {0: {}, 1: {}, 2: {0x343: 8, 0x4CB: 8}}):
      for alpha_long in (False, True):
        with self.subTest(fingerprint=fingerprint, alpha_long=alpha_long):
          retrofit = get_params(RETROFIT, fingerprint, alpha_long)
          self.assertFalse(retrofit.dashcamOnly)
          self.assertFalse(retrofit.flags & ToyotaFlags.LONG_FILTER)
          self.assertEqual(retrofit.to_dict(), get_params(RETROFIT, empty_fingerprint(), alpha_long).to_dict())
          # TOYOTA_COROLLA has no camera-fingerprint takeover check either; it stays unaffected.
          self.assertFalse(get_params(STOCK, fingerprint, alpha_long).dashcamOnly)
          # The alpha's other Corolla-body retrofit shows the hazard: the same mirror makes it dashcam-only.
          self.assertTrue(get_params(CAR.TOYOTA_MATRIX_RETROFIT, fingerprint, alpha_long).dashcamOnly)

  def test_carstate_does_not_require_acc_control(self):
    bus = CarBus(RETROFIT, fingerprint=MIRRORED_FINGERPRINT)
    self.assertTrue(bus.run(300).canValid)
    self.assertNotIn('ACC_CONTROL', bus.CI.can_parsers[Bus.pt].vl)


if __name__ == "__main__":
  unittest.main()

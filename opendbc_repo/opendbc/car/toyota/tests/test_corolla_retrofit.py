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


class TestLkaStateZero(unittest.TestCase):
  def test_lka_state_zero_is_not_a_temporary_fault(self):
    from opendbc.car.toyota.carstate import TEMP_STEER_FAULTS
    self.assertIn(0, TEMP_STEER_FAULTS)
    for lka_state, retrofit_fault, stock_fault in ((0, False, True), (1, False, False), (5, False, False),
                                                   (9, True, True), (11, True, True), (21, True, True), (25, True, True)):
      with self.subTest(lka_state=lka_state):
        values = {'EPS_STATUS': {'LKA_STATE': lka_state}}
        retrofit = CarBus(RETROFIT, values=values).run(150)
        stock = CarBus(STOCK, values=values).run(150)
        self.assertEqual(retrofit.steerFaultTemporary, retrofit_fault)
        self.assertEqual(stock.steerFaultTemporary, stock_fault)
        self.assertFalse(retrofit.steerFaultPermanent)

  def test_permanent_faults_unchanged(self):
    for lka_state in (3, 17):
      with self.subTest(lka_state=lka_state):
        values = {'EPS_STATUS': {'LKA_STATE': lka_state}}
        self.assertTrue(CarBus(RETROFIT, values=values).run(150).steerFaultPermanent)
        self.assertTrue(CarBus(STOCK, values=values).run(150).steerFaultPermanent)


class TestSteerAngleLimit(unittest.TestCase):
  def test_lateral_dropped_beyond_300_deg(self):
    from opendbc.car.toyota.carcontroller import MAX_STEER_ANGLE_DEG
    from opendbc.car.toyota.tests.test_auto_hold import setup_hold, step_hold
    self.assertEqual(MAX_STEER_ANGLE_DEG, 300)
    for car in (RETROFIT, STOCK):
      for angle in (0., 299.9, -299.9, 300.1, -300.1, 450., -540.):
        with self.subTest(car=car, angle=angle):
          cp, controller, command, state = setup_hold(car, enabled=False)
          state.out.standstill = False
          state.out.steeringAngleDeg = angle
          command.enabled = command.latActive = True
          command.actuators.torque = 0.5
          frames = [frame for _ in range(5) for frame in step_hold(controller, command, state) if frame[0] == 0x2E4]
          steering = decode(cp, frames[-1], 'STEERING_LKA')
          applied = car == STOCK or abs(angle) <= 300.
          self.assertEqual(steering['STEER_REQUEST'], int(applied))
          self.assertEqual(steering['STEER_TORQUE_CMD'] != 0, applied)
          self.assertEqual(controller.last_torque != 0, applied)


class TestSasOffset(unittest.TestCase):
  def test_offset_applies_only_to_retrofit(self):
    from opendbc.car.toyota.retrofit import apply_sas_offset
    # STEER_ANGLE_SENSOR has 1.5 deg resolution
    values = {'STEER_ANGLE_SENSOR': {'STEER_ANGLE': 6.}, 'STEER_TORQUE_SENSOR': {'STEER_ANGLE': 6.}}
    for car, applied in ((RETROFIT, True), (STOCK, False)):
      with self.subTest(car=car):
        bus = CarBus(car, values=values)
        self.assertEqual(bus.CI.CS.sas_offset_deg, 0.)
        self.assertEqual(apply_sas_offset(bus.CI.CS, -48.), applied)
        state = bus.run(150)
        self.assertAlmostEqual(state.steeringAngleDeg, 54. if applied else 6., places=3)
        # The torque-sensor angle offset filter sees the corrected angle
        self.assertAlmostEqual(state.steeringAngleOffsetDeg, -48. if applied else 0., delta=0.05)

  def test_offset_is_applied_before_angle_offset_filter(self):
    from opendbc.car.toyota.retrofit import apply_sas_offset
    # Raw 99 deg is outside the filter's +/-90 deg update window; corrected 39 deg is inside it
    values = {'STEER_ANGLE_SENSOR': {'STEER_ANGLE': 99.}, 'STEER_TORQUE_SENSOR': {'STEER_ANGLE': 6.}}
    retrofit, stock = CarBus(RETROFIT, values=values), CarBus(STOCK, values=values)
    apply_sas_offset(retrofit.CI.CS, 60.)
    apply_sas_offset(stock.CI.CS, 60.)
    retrofit_state, stock_state = retrofit.run(150), stock.run(150)
    self.assertTrue(retrofit.CI.CS.angle_offset.initialized)
    self.assertAlmostEqual(retrofit_state.steeringAngleDeg, 39., places=3)
    self.assertAlmostEqual(retrofit_state.steeringAngleOffsetDeg, -33., delta=0.05)
    self.assertFalse(stock.CI.CS.angle_offset.initialized)
    self.assertAlmostEqual(stock_state.steeringAngleDeg, 99., places=3)

  def test_offset_validation(self):
    from opendbc.car.toyota.retrofit import sas_offset_deg
    for value, expected in ((-48., -48.), (0., 0.), (180., 180.), (-180., -180.), (180.5, 0.), (-200., 0.),
                            (float('nan'), 0.), (float('inf'), 0.), ('x', 0.), (None, 0.), ('-48', -48.)):
      with self.subTest(value=value):
        self.assertEqual(sas_offset_deg(value), expected)


class TestSteerAngleDeadzone(unittest.TestCase):
  def test_default_deadzone(self):
    self.assertAlmostEqual(get_params(RETROFIT).lateralTuning.torque.steeringAngleDeadzoneDeg, 0.3, places=5)
    self.assertEqual(get_params(STOCK).lateralTuning.torque.steeringAngleDeadzoneDeg, 0.)

  def test_saved_deadzone_applies_only_to_retrofit(self):
    from opendbc.car.toyota.retrofit import apply_steer_angle_deadzone
    retrofit, stock = get_params(RETROFIT), get_params(STOCK)
    self.assertTrue(apply_steer_angle_deadzone(retrofit, 0.8))
    self.assertFalse(apply_steer_angle_deadzone(stock, 0.8))
    self.assertAlmostEqual(retrofit.lateralTuning.torque.steeringAngleDeadzoneDeg, 0.8, places=5)
    self.assertEqual(stock.lateralTuning.torque.steeringAngleDeadzoneDeg, 0.)

  def test_deadzone_validation(self):
    from opendbc.car.toyota.retrofit import steer_angle_deadzone_deg
    for value, expected in ((0., 0.), (0.3, 0.3), (2., 2.), (2.1, 0.3), (-0.1, 0.3), (float('nan'), 0.3), ('x', 0.3), (None, 0.3)):
      with self.subTest(value=value):
        self.assertEqual(steer_angle_deadzone_deg(value), expected)


class TestLongitudinal(unittest.TestCase):
  def test_alpha_long_toggle_selects_openpilot_long(self):
    for alpha_long in (False, True):
      with self.subTest(alpha_long=alpha_long):
        retrofit, stock = get_params(RETROFIT, alpha_long=alpha_long), get_params(STOCK, alpha_long=alpha_long)
        self.assertTrue(retrofit.alphaLongitudinalAvailable)
        self.assertEqual(retrofit.openpilotLongitudinalControl, alpha_long)
        self.assertTrue(retrofit.pcmCruise)
        self.assertEqual(bool(retrofit.safetyConfigs[0].safetyParam & ToyotaSafetyFlags.STOCK_LONGITUDINAL), not alpha_long)
        self.assertEqual(retrofit.safetyConfigs[0].safetyParam, 344 if alpha_long else 856)
        # TOYOTA_COROLLA stays on stock longitudinal with no alpha-long offer
        self.assertFalse(stock.alphaLongitudinalAvailable)
        self.assertFalse(stock.openpilotLongitudinalControl)
        self.assertTrue(stock.pcmCruise)
        self.assertEqual(stock.safetyConfigs[0].safetyParam, 856)

  def test_existing_panda_safety_admits_acc_control_only_with_openpilot_long(self):
    from opendbc.car.structs import CarParams
    from opendbc.safety.tests.common import CANPackerSafety
    from opendbc.safety.tests.libsafety import libsafety_py
    safety = libsafety_py.libsafety
    packer = CANPackerSafety('toyota_new_mc_pt_generated')
    for alpha_long in (False, True):
      with self.subTest(alpha_long=alpha_long):
        cp = get_params(RETROFIT, alpha_long=alpha_long)
        self.assertEqual(safety.set_safety_hooks(CarParams.SafetyModel.toyota, cp.safetyConfigs[0].safetyParam), 0)
        safety.init_tests()
        safety.set_controls_allowed(True)
        self.assertEqual(safety.safety_tx_hook(packer.make_can_msg_safety('ACC_CONTROL', 0, {'ACCEL_CMD': 0.5})), alpha_long)

  def test_controller_sends_acc_control_only_with_openpilot_long(self):
    from opendbc.car import structs
    for alpha_long in (False, True):
      with self.subTest(alpha_long=alpha_long):
        bus = CarBus(RETROFIT, alpha_long=alpha_long)
        bus.run(150)
        CC = structs.CarControl()
        CC.enabled = CC.longActive = True
        sends = [frame for _ in range(3) for frame in bus.CI.apply(CC.as_reader(), 2_500_000_000)[1]]
        self.assertEqual(any(frame[0] == 0x343 for frame in sends), alpha_long)


class TestRetrofitDiagnostics(unittest.TestCase):
  def test_tracker_only_on_retrofit(self):
    retrofit, stock = CarBus(RETROFIT), CarBus(STOCK)
    retrofit.run(5)
    stock.run(5)
    self.assertIsNone(stock.CI.CS.retrofit_diag)
    self.assertNotIn('RETROFIT_EMULATOR_DIAG', stock.CI.can_parsers[Bus.pt].vl)
    self.assertIsNotNone(retrofit.CI.CS.retrofit_diag.state)
    self.assertEqual(retrofit.CI.CS.retrofit_diag.state['epsLkaState'], 1)

  def test_silent_or_rebooting_ecus_never_affect_can_valid(self):
    from opendbc.can.dbc import DBC as CANDBC, SignalType
    from opendbc.car.toyota import retrofit_diag
    from opendbc.car.toyota.tests.test_retrofit_diag import emulator_diag, stalk_0x69, stalk_diag, vss_diag
    dbc = CANDBC(DBC[RETROFIT][Bus.pt])
    for name, _ in retrofit_diag.PT_MESSAGES:
      self.assertNotIn(SignalType.COUNTER, {sig.type for sig in dbc.name_to_msg[name].sigs.values()}, name)

    bus = CarBus(RETROFIT)
    # Reboots every frame: boot count and ROLLING_COUNTER jump on all three ECUs
    for i in range(100):
      state = bus.step([stalk_0x69(0, True), stalk_diag(boot=i % 256, rolling=(i * 7) % 16),
                        emulator_diag(boot=i % 256, rolling=(i * 5) % 16), vss_diag(boot=i % 256, rolling=(i * 3) % 16)])
    self.assertTrue(state.canValid)
    self.assertGreater(bus.CI.CS.retrofit_diag.state['stalk']['restarts'], 90)
    # Then 5 s of silence from every custom ECU
    state = bus.run(500)
    self.assertTrue(state.canValid)
    self.assertFalse(state.canTimeout)
    self.assertGreater(bus.CI.CS.retrofit_diag.state['stalkFrameAge'], 4.9)


if __name__ == "__main__":
  unittest.main()

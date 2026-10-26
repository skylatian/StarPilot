"""Always On Lateral on TOYOTA_COROLLA_RETROFIT.

The car publishes the stock-control word 856, the same as TOYOTA_MATRIX_RETROFIT, so the panda and pandad
sides are upstream's. The host admission is our own (opendbc toyota/retrofit.py configured()).
"""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.values import CAR, ToyotaFlags
from openpilot.cereal import log
from openpilot.starpilot.aol.vehicle import native_matches_cp, policy_for
from openpilot.starpilot.car.toyota.aol import ToyotaCardIntent, matrix_stock_qualified, native_accepts_cp, qualified

TOYOTA = int(structs.CarParams.SafetyModel.toyota)


def retrofit_cp(alpha_long=False):
  return CarInterface.get_params(CAR.TOYOTA_COROLLA_RETROFIT, gen_empty_fingerprint(), [], alpha_long, False, False)


def marked_cp():
  cp = retrofit_cp()
  cp.alternativeExperience |= policy_for(cp).alternative_experience_addition
  return cp


class TestCorollaRetrofitAol(unittest.TestCase):
  def test_stock_control_profile_is_admitted(self):
    for alpha_long in (False, True):
      with self.subTest(alpha_long=alpha_long):
        cp = retrofit_cp(alpha_long)
        self.assertEqual((cp.safetyConfigs[0].safetyParam, cp.alternativeExperience, int(cp.flags)), (856, 0, 0))
        self.assertTrue(qualified(cp))
        self.assertFalse(qualified(cp, marked_only=True))
        policy = policy_for(cp)
        self.assertTrue(policy.runtime_supported and policy.settings_supported and policy.intent_supported)
        self.assertEqual(policy.alternative_experience_addition, 32)
    cp = marked_cp()
    self.assertTrue(qualified(cp, marked_only=True))
    self.assertTrue(native_matches_cp(cp, TOYOTA, 856))
    self.assertTrue(native_accepts_cp(cp, TOYOTA, 856))

  def test_panda_grants_lateral_for_the_published_word(self):
    # Ask the panda safety library, with a 5-byte EPS_STATUS like this car's EPS, rather than reading its word list.
    from opendbc.safety.tests.test_toyota_matrix_stock_aol import Physical
    cp = marked_cp()
    case = Physical(word=cp.safetyConfigs[0].safetyParam, experience=cp.alternativeExperience)
    try:
      case.warm()
      self.assertTrue(case.safety.safety_config_valid())
      self.assertEqual(case.safety.aol_get_permission_mask(), 1)
      self.assertTrue(case.tx('STEERING_LKA', {'STEER_TORQUE_CMD': 1, 'STEER_REQUEST': 1}))
      self.assertFalse(case.tx('ACC_CONTROL', {'ACCEL_CMD': .1}))
    finally:
      case.close()

  def test_same_shape_as_the_matrix_stock_control_profile(self):
    # Reference only: admission never goes through the Matrix check. If upstream changes what word 856
    # requires, this fails on the next rebase so the two can be compared.
    cp = marked_cp()
    self.assertFalse(matrix_stock_qualified(cp, marked_only=True))
    probe = cp.as_reader().as_builder()
    probe.carFingerprint = CAR.TOYOTA_MATRIX_RETROFIT
    self.assertTrue(matrix_stock_qualified(probe, marked_only=True))

  def test_mutations_fail_closed(self):
    marked = marked_cp()
    mutations = {
      'identity': lambda cp: setattr(cp, 'carFingerprint', CAR.TOYOTA_COROLLA),
      'flags': lambda cp: setattr(cp, 'flags', int(ToyotaFlags.AUTO_BRAKE_HOLD)),
      'alpha word': lambda cp: setattr(cp.safetyConfigs[0], 'safetyParam', 344),
      'scale word': lambda cp: setattr(cp.safetyConfigs[0], 'safetyParam', 88),
      'long': lambda cp: setattr(cp, 'openpilotLongitudinalControl', True),
      'experience': lambda cp: setattr(cp, 'alternativeExperience', 160),
      'passive': lambda cp: setattr(cp, 'passive', True),
      'dashcam': lambda cp: setattr(cp, 'dashcamOnly', True),
      'model': lambda cp: setattr(cp.safetyConfigs[0], 'safetyModel', structs.CarParams.SafetyModel.noOutput),
      'pcm': lambda cp: setattr(cp, 'pcmCruise', False),
      'configs': lambda cp: setattr(cp, 'safetyConfigs', [cp.safetyConfigs[0], cp.safetyConfigs[0]]),
    }
    for name, mutate in mutations.items():
      with self.subTest(mutation=name):
        bad = marked.as_reader().as_builder()
        mutate(bad)
        self.assertFalse(qualified(bad, marked_only=True))

  def test_no_minimum_engage_speed_with_stock_longitudinal(self):
    # Toyota raises belowEngageSpeed only with openpilot longitudinal, so the 19 mph minimum never applies.
    from openpilot.selfdrive.car.car_events import CarEvents
    cp = marked_cp()
    self.assertGreater(cp.minEnableSpeed, 0)
    state = structs.CarState(canValid=True, vEgo=2., gearShifter=structs.CarState.GearShifter.drive)
    state.cruiseState.available = True
    events = CarEvents(cp).update(state, state, structs.CarControl())
    self.assertNotIn(log.OnroadEvent.EventName.belowEngageSpeed, events.names)

  def test_main_on_allows_the_latch(self):
    from openpilot.starpilot.aol.intent import AolSettings
    owner = ToyotaCardIntent(AolSettings(True, 0., 9, 9, (0, 0, 0), (0, 0, 0)))
    state = structs.CarState(canValid=True, gearShifter=structs.CarState.GearShifter.drive)
    for available in (False, True, False):
      state.cruiseState.available = available
      owner.update(state.as_reader())
      self.assertEqual(owner.allowed_latch, available)

  def test_card_publishes_the_marked_profile(self):
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.selfdrive.car.card import Car
    from openpilot.selfdrive.controls.controlsd import Controls
    from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD
    for enabled in (False, True):
      with self.subTest(enabled=enabled), OpenpilotPrefix(), \
           patch.dict(os.environ, {'SIMULATION': '1', 'AOL_REPLAY_RUNTIME': '0'}):
        saved = Params()
        for key, value in (('OpenpilotEnabledToggle', True), ('AlwaysOnLateral', enabled), ('SafeMode', False)):
          saved.put_bool(key, value, block=True)
        cp = retrofit_cp()

        def discover(*args, pre_create_hook, cp=cp, **kwargs):
          return CarInterface(pre_create_hook(cp.as_reader().as_builder(), cp.carFingerprint, {}, []))
        with patch('openpilot.selfdrive.car.card.messaging.recv_one_retry', return_value=SimpleNamespace(can=[1])), \
             patch('openpilot.selfdrive.car.card.get_car', side_effect=discover):
          selected = Car()
        self.assertEqual((selected.CP.safetyConfigs[0].safetyParam, selected.CP.alternativeExperience), (856, 32))
        self.assertTrue(qualified(selected.CP, marked_only=True))
        with structs.CarParams.from_bytes(saved.get('CarParams')) as published:
          self.assertEqual(published.to_dict(), selected.CP.to_dict())
        controls = Controls()
        with patch('openpilot.selfdrive.selfdrived.selfdrived.REPLAY', False):
          sd = SelfdriveD(CP=selected.CP)
        self.assertTrue(controls.aol_replay)
        self.assertTrue(sd.aol_replay)
        state = structs.CarState(canValid=True, gearShifter=structs.CarState.GearShifter.drive)
        state.cruiseState.available = True
        selected.aol_card_intent.update(state.as_reader())
        self.assertEqual(selected.aol_card_intent.allowed_latch, enabled)
        del controls, sd, selected


# firestar's held-pedal intent (car/toyota/aol.py held_lateral_pedal) keys off qualified(marked_only=True),
# so it reaches the retrofit through our admission. Run his RAV4 route scenario with our CarParams.
@pytest.mark.parametrize('pedal', ('brake', 'gas'))
def test_held_pedal_source_gap_keeps_retrofit_intent(pedal):
  from openpilot.starpilot.aol.tests.test_toyota_brake_source_gap import (BASE, ExitStack, OpenpilotPrefix, fixture,
                                                                         intent, refresh_saved_settings, rolling)
  brake, gas = pedal == 'brake', pedal == 'gas'
  with ExitStack() as cleanup:
    cleanup.enter_context(OpenpilotPrefix())
    case = fixture.IoniqAvailabilityTests(methodName='runTest')
    cleanup.callback(case.doCleanups)
    sd, _, drive = case._authority_callers(False, cp=retrofit_cp(), genuine_events=True)
    refresh_saved_settings(sd)
    assert qualified(sd.CP, marked_only=True)
    for tick in (0, 1):
      axis, _, command = drive(tick, observed_state=rolling(brake, gas), brake=brake, gas=gas, native_request_long=False)
      assert axis.lateralActive and command.latActive and not command.longActive
    prior, _, command = drive(2, offset_ns=5_209_427, state_stamp=BASE,
      intent_message=intent(BASE, 3), observed_state=rolling(brake, gas), brake=brake, gas=gas, native_request_long=False)
    assert prior.lateralActive and command.latActive
    axis, host, command = drive(5, offset_ns=2_073_802, timeout=True,
      state_stamp=BASE, intent_message=intent(BASE, 3), brake=brake, gas=gas, native_request_long=False)
    assert log.OnroadEvent.EventName.controlsMismatch not in sd.events.names
    assert str(axis.faultReason) == 'availabilityPause' and not command.latActive and not host.enabled
    assert axis.desiredLateral and axis.nativeAcknowledged and not sd.aol_authority_lost
    source = BASE + 28_454_011
    axis, _, command = drive(6, state_stamp=source, intent_message=intent(source, 4),
      observed_state=rolling(brake, gas), brake=brake, gas=gas, native_request_long=False)
    assert axis.lateralActive and command.latActive and not command.longActive


@pytest.mark.parametrize('fault', ('native_denied', 'rx_fault', 'latch_withdrawn', 'missing_anchor', 'dm_lockout'))
def test_held_pedal_source_gap_keeps_retrofit_restrictions(fault):
  from openpilot.starpilot.aol.tests.test_toyota_brake_source_gap import (BASE, ExitStack, OpenpilotPrefix, fixture,
                                                                         intent, refresh_saved_settings, rolling)
  with ExitStack() as cleanup:
    cleanup.enter_context(OpenpilotPrefix())
    case = fixture.IoniqAvailabilityTests(methodName='runTest')
    cleanup.callback(case.doCleanups)
    sd, _, drive = case._authority_callers(False, cp=retrofit_cp(), genuine_events=True)
    refresh_saved_settings(sd)
    for tick in (0, 1, 2):
      drive(tick, offset_ns=5_209_427 if tick == 2 else 0, state_stamp=BASE if tick == 2 else None,
            intent_message=intent(BASE, 3) if tick == 2 else None, observed_state=rolling(), brake=True,
            native_request_long=False)
    if fault == 'missing_anchor':
      sd.aol_ordinary_source_anchor = None
    elif fault == 'dm_lockout':
      sd.aol_dm_lateral_inhibit = True
    axis, host, command = drive(5, offset_ns=2_073_802, timeout=True,
      state_stamp=BASE, intent_message=intent(BASE, 3, latched=fault != 'latch_withdrawn'),
      brake=True, native_request_long=False, allowed=fault != 'native_denied', panda_fault=fault == 'rx_fault')
    assert not axis.lateralActive and not command.latActive and not host.enabled
    if fault != 'latch_withdrawn':
      assert str(axis.faultReason) != 'availabilityPause'


if __name__ == '__main__':
  unittest.main()

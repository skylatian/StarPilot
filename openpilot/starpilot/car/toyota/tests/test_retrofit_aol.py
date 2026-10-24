"""Always On Lateral admission for TOYOTA_COROLLA_RETROFIT (safety word 344, 5-byte EPS_STATUS)."""
import os
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.values import CAR, ToyotaFlags
from openpilot.starpilot.aol.vehicle import native_matches_cp, policy_for
from openpilot.starpilot.car.toyota.aol import AOL_WORDS, ToyotaCardIntent, native_accepts_cp, qualified

TOYOTA = int(structs.CarParams.SafetyModel.toyota)


def retrofit_cp(alpha_long=True):
  return CarInterface.get_params(CAR.TOYOTA_COROLLA_RETROFIT, gen_empty_fingerprint(), [], alpha_long, False, False)


class TestRetrofitAolAdmission(unittest.TestCase):
  def test_alpha_long_profile_is_admitted(self):
    cp = retrofit_cp()
    self.assertEqual((cp.safetyConfigs[0].safetyParam, cp.alternativeExperience, int(cp.flags)), (344, 0, 0))
    self.assertTrue(cp.openpilotLongitudinalControl)
    self.assertTrue(qualified(cp))
    self.assertFalse(qualified(cp, marked_only=True))
    policy = policy_for(cp)
    self.assertTrue(policy.runtime_supported and policy.settings_supported and policy.intent_supported)
    self.assertEqual(policy.alternative_experience_addition, 32)
    cp.alternativeExperience |= policy.alternative_experience_addition
    self.assertTrue(qualified(cp, marked_only=True))
    self.assertIn(344, AOL_WORDS)
    self.assertTrue(native_matches_cp(cp, TOYOTA, 344))
    self.assertTrue(native_accepts_cp(cp, TOYOTA, 344))
    self.assertFalse(native_matches_cp(cp, TOYOTA, 73))

  def test_word_lists_agree_across_host_pandad_and_panda(self):
    # The Toyota AOL words live in three places; a word missing from pandad's list leaves aolSafetyWire
    # unpublished (no AOL, and controlsMismatch on every engagement): 2026-10-23 drive, 00000003.
    root = Path(__file__).resolve().parents[5]
    def words(path, function):
      source = (root / path).read_text()
      body = source[source.index(function):]
      body = body[:body.index('\n}')]
      return {int(n, 0) for n in re.findall(r'param == (0x[0-9A-Fa-f]+|\d+)U', body)}
    pandad = words('openpilot/starpilot/car/toyota/aol_policy.h', 'inline bool toyota_aol_param')
    panda = words('opendbc_repo/opendbc/safety/modes/toyota_aol.h', 'static void toyota_aol_configure')
    self.assertIn(344, AOL_WORDS)
    self.assertEqual(pandad, set(AOL_WORDS))
    self.assertEqual(panda, set(AOL_WORDS))

  def test_stock_longitudinal_is_not_admitted(self):
    # Alpha long off sets STOCK_LONGITUDINAL (word 856), which the panda's AOL list does not hold.
    cp = retrofit_cp(alpha_long=False)
    self.assertEqual(cp.safetyConfigs[0].safetyParam, 856)
    self.assertFalse(qualified(cp))
    self.assertEqual(policy_for(cp).alternative_experience_addition, 0)

  def test_mutations_fail_closed(self):
    marked = retrofit_cp()
    marked.alternativeExperience = 32
    for mutation in ('identity', 'matrix', 'flags', 'word', 'long', 'experience', 'passive', 'dashcam', 'model', 'pcm', 'configs'):
      with self.subTest(mutation=mutation):
        bad = marked.as_reader().as_builder()
        if mutation == 'identity':
          bad.carFingerprint = CAR.TOYOTA_COROLLA
        elif mutation == 'matrix':
          bad.carFingerprint = CAR.TOYOTA_MATRIX_RETROFIT
        elif mutation == 'flags':
          bad.flags |= int(ToyotaFlags.AUTO_BRAKE_HOLD)
        elif mutation == 'word':
          bad.safetyConfigs[0].safetyParam = 88
        elif mutation == 'long':
          bad.openpilotLongitudinalControl = False
        elif mutation == 'experience':
          bad.alternativeExperience = 160
        elif mutation == 'passive':
          bad.passive = True
        elif mutation == 'dashcam':
          bad.dashcamOnly = True
        elif mutation == 'model':
          bad.safetyConfigs[0].safetyModel = structs.CarParams.SafetyModel.noOutput
        elif mutation == 'pcm':
          bad.pcmCruise = False
        else:
          bad.safetyConfigs = [bad.safetyConfigs[0], bad.safetyConfigs[0]]
        self.assertFalse(qualified(bad, marked_only=True))

  def test_stock_corolla_is_not_admitted_at_the_same_word(self):
    cp = CarInterface.get_params(CAR.TOYOTA_COROLLA, gen_empty_fingerprint(), [], True, False, False)
    cp.safetyConfigs[0].safetyParam = 344
    self.assertFalse(qualified(cp))
    cp.alternativeExperience = 32
    self.assertFalse(native_accepts_cp(cp, TOYOTA, 344))

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
        self.assertEqual((selected.CP.safetyConfigs[0].safetyParam, selected.CP.alternativeExperience), (344, 32))
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


if __name__ == '__main__':
  unittest.main()

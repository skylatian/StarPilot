"""TOYOTA_COROLLA_RETROFIT logs which gate keeps lane centering from acting."""

import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from opendbc.car import gen_empty_fingerprint
from opendbc.car.car_helpers import interfaces
from opendbc.car.toyota.values import CAR
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.lateral import retrofit_lane_gate_log as gate_log
from openpilot.starpilot.lateral.lane_centering import (ControlMode, LaneCenteringController, LaneCenteringInput,
                                                       LaneCenteringSettings)
from openpilot.starpilot.lateral.lane_runtime import LaneCenteringHost
from openpilot.starpilot.lateral.tests.test_lane_centering import model

NOW = 10_000_000_000


def car_params(fingerprint=CAR.TOYOTA_COROLLA_RETROFIT):
  return interfaces[fingerprint].get_params(fingerprint, gen_empty_fingerprint(), [], False, False, False)


class Frame:
  """A SubMaster stand-in whose individual checks can fail."""

  def __init__(self, now_ns=NOW, *, not_alive=(), bad_freq=(), invalid=(), ages_ms=None, can_valid=True):
    ages_ms = ages_ms or {}
    self.logMonoTime = {s: now_ns - int(ages_ms.get(s, 5) * 1e6) for s in LaneCenteringHost.REQUIRED}
    self.not_alive, self.bad_freq, self.invalid = set(not_alive), set(bad_freq), set(invalid)
    self.state = SimpleNamespace(canValid=can_valid, canTimeout=False)
    self.freq_tracker = {s: SimpleNamespace(avg_dt=SimpleNamespace(get_average=lambda: 0.08)) for s in self.bad_freq}

  def all_alive(self, services):
    return not set(services) & self.not_alive

  def all_freq_ok(self, services):
    return not set(services) & self.bad_freq

  def all_valid(self, services):
    return not set(services) & self.invalid

  def all_checks(self, services):
    return self.all_alive(services) and self.all_freq_ok(services) and self.all_valid(services)

  def __getitem__(self, _service):
    return self.state


def observation(*, model_valid=True, speed=25.0, lateral_active=True, enabled=True):
  return LaneCenteringInput(model=model(), model_sample_id=1, model_valid=model_valid, base_curvature=0.0, speed_mps=speed,
                            mode=ControlMode.LATERAL_ONLY if lateral_active else ControlMode.OFF, lateral_active=lateral_active,
                            settings=LaneCenteringSettings(enabled=enabled), elapsed_seconds=0.01)


class TestRetrofitLaneGateLog(unittest.TestCase):
  def setUp(self):
    self.prefix = OpenpilotPrefix()
    self.prefix.__enter__()
    Params().put_bool('LaneCentering', True, block=True)
    self.counter = gate_log.GateCounter()
    self.host = gate_log.GateLoggedHost(Params(), self.counter)

  def tearDown(self):
    self.prefix.__exit__(None, None, None)

  def sample(self, sm, now_ns=NOW, lateral_active=True):
    return self.host.sample(sm, now_ns=now_ns, lateral_active=lateral_active, longitudinal_active=False)

  def test_wraps_only_the_retrofit(self):
    controller, host = LaneCenteringController(), LaneCenteringHost(Params())
    wrapped = gate_log.wrap(car_params(), controller, host, Params())
    self.assertIsInstance(wrapped[0], gate_log.GateLoggedController)
    self.assertIsInstance(wrapped[1], gate_log.GateLoggedHost)
    self.assertIs(wrapped[0].counter, wrapped[1].counter)
    self.assertEqual(gate_log.wrap(car_params(CAR.TOYOTA_COROLLA), controller, host, Params()), (controller, host))
    self.assertEqual(gate_log.wrap(car_params(), controller, None, Params()), (controller, None))

  def test_host_names_every_failing_check(self):
    self.assertIsNone(self.sample(Frame(bad_freq=('vehicleParameters',), ages_ms={'carState': 40})))
    self.assertEqual(self.counter.gates, {'host:stale:carState+freq:vehicleParameters': 1})
    self.assertEqual(self.counter.freq_hz, {'vehicleParameters': 12.5})
    self.assertIsNone(self.sample(Frame(not_alive=('modelV2',), invalid=('selfdriveState',), can_valid=False)))
    self.assertIn('host:can_invalid+invalid:selfdriveState+not_alive:modelV2', self.counter.gates)

  def test_host_passes_requests_through_unchanged(self):
    request = self.sample(Frame())
    self.assertIsNotNone(request)
    self.assertEqual(request.mode, ControlMode.LATERAL_ONLY)
    self.assertEqual(self.counter.ticks, 0)  # the controller records the verdict for a request

  def test_ignores_ticks_without_steering_or_with_lane_centering_off(self):
    self.assertIsNone(self.sample(Frame(bad_freq=('modelV2',)), lateral_active=False))
    Params().put_bool('LaneCentering', False, block=True)
    self.assertIsNone(self.sample(Frame(bad_freq=('modelV2',)), now_ns=NOW + 2_000_000_000))
    self.assertEqual(self.counter.ticks, 0)

  def test_controller_names_why_it_was_inactive(self):
    controller = gate_log.GateLoggedController(self.counter)
    self.counter.start_tick(Frame(bad_freq=('modelV2',)), NOW)
    result = controller.update(observation(model_valid=False))
    self.assertEqual(result.reason, 'inactive')
    controller.update(observation(speed=2.0))
    self.assertEqual(self.counter.gates, {'update:model_invalid(freq:modelV2)': 1, 'update:slow': 1})
    self.assertEqual(self.counter.flips, 1)

  def test_controller_results_match_upstream(self):
    wrapped, plain = gate_log.GateLoggedController(self.counter), LaneCenteringController()
    self.counter.start_tick(Frame(), NOW)
    for obs in (observation(), observation(model_valid=False), observation(speed=2.0)):
      self.assertEqual(wrapped.update(obs), plain.update(obs))
    self.assertEqual(self.counter.ticks, 3)

  def test_one_event_per_window(self):
    controller = gate_log.GateLoggedController(self.counter)
    with patch.object(gate_log.cloudlog, 'event') as event:
      for tick in range(int(gate_log.WINDOW_S * 100) + 1):
        now = NOW + tick * 10_000_000
        self.counter.start_tick(Frame(now), now)
        controller.update(observation(model_valid=tick % 2 == 0))
    event.assert_called_once()
    name, kwargs = event.call_args.args[0], event.call_args.kwargs
    self.assertEqual(name, 'lane_centering_gates')
    self.assertEqual(kwargs['ticks'], 1000)
    self.assertEqual(kwargs['flips'], 999)
    self.assertEqual(kwargs['gates']['update:model_invalid'], 500)
    self.assertEqual(sum(kwargs['gates'].values()), 1000)

  def test_controlsd_wraps_it_only_for_the_retrofit(self):
    from openpilot.selfdrive.controls.controlsd import Controls
    for fingerprint, expected in ((CAR.TOYOTA_COROLLA_RETROFIT, True), (CAR.TOYOTA_COROLLA, False)):
      with self.subTest(fingerprint=fingerprint), OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
        Params().put("CarParams", car_params(fingerprint).to_bytes(), block=True)
        controls = Controls()
        self.assertEqual(isinstance(controls.lane_centering_controller, gate_log.GateLoggedController), expected)
        self.assertEqual(isinstance(controls.lane_centering_host, gate_log.GateLoggedHost), expected)
        del controls


if __name__ == '__main__':
  unittest.main()

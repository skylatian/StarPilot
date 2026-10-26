"""TOYOTA_COROLLA_RETROFIT: log which gate keeps lane centering from acting.

On the 2026-10-25 drive lane centering logged `qualified` and `inactive` 10-27 times a second while
steering was engaged, and each `inactive` tick resets its correction. The log doesn't say which check
failed. The host and controller subclasses here re-check the same inputs right after an upstream call
returns no request or `inactive`, and name every check that failed. Ticks are counted while steering
is engaged and lane centering is switched on, and each WINDOW_S goes out as one `lane_centering_gates`
swaglog event. Nothing here changes what lane centering does. Kept in this one file so it can be
dropped once the cause is fixed.
"""

from openpilot.cereal.services import SERVICE_LIST
from openpilot.common.swaglog import cloudlog
from opendbc.car.toyota.retrofit import is_retrofit
from openpilot.starpilot.lateral.lane_centering import MIN_SPEED, LaneCenteringController
from openpilot.starpilot.lateral.lane_runtime import LaneCenteringHost

WINDOW_S = 10.0
MAX_EVENTS = 720  # two hours of windows per drive


def _limit_ns(service: str) -> int:
  return int(2.5e9 / SERVICE_LIST[service].frequency)


def _checks(sm, service: str) -> list[str]:
  """Which SubMaster check fails for one service, as host.sample's all_checks sees it."""
  if not all(hasattr(sm, name) for name in ('all_alive', 'all_freq_ok', 'all_valid')):
    return [] if sm.all_checks([service]) else [f'checks:{service}']
  failed = []
  if not sm.all_alive([service]):
    failed.append(f'not_alive:{service}')
  if not sm.all_freq_ok([service]):
    failed.append(f'freq:{service}')
  if not sm.all_valid([service]):
    failed.append(f'invalid:{service}')
  return failed


def _measured_hz(sm, service: str) -> float | None:
  try:
    average = sm.freq_tracker[service].avg_dt.get_average()
    return round(1.0 / average, 2) if average > 0 else None
  except (AttributeError, KeyError, TypeError, ZeroDivisionError):
    return None


class GateCounter:
  def __init__(self):
    self.events = 0
    self.window_start_ns: int | None = None
    self.model_checks: list[str] = []
    self.ages_ms: dict[str, float | None] = {}
    self._clear()

  def _clear(self):
    self.ticks = 0
    self.flips = 0
    self.gates: dict[str, int] = {}
    self.max_age_ms: dict[str, float] = {}
    self.freq_hz: dict[str, float] = {}
    self.last_gate: str | None = None

  def start_tick(self, sm, now_ns: int):
    if self.window_start_ns is None or now_ns < self.window_start_ns:
      self.window_start_ns = now_ns
    elif now_ns - self.window_start_ns >= WINDOW_S * 1e9:
      self.flush(now_ns)
    self.model_checks = _checks(sm, 'modelV2')
    self.ages_ms = {}
    for service in LaneCenteringHost.REQUIRED:
      stamp = int(sm.logMonoTime[service])
      self.ages_ms[service] = round((now_ns - stamp) / 1e6, 1) if stamp > 0 else None

  def note_freq(self, sm, service: str):
    measured = _measured_hz(sm, service)
    if measured is not None:
      self.freq_hz[service] = measured

  def record(self, gate: str):
    self.ticks += 1
    self.gates[gate] = self.gates.get(gate, 0) + 1
    if self.last_gate is not None and gate != self.last_gate:
      self.flips += 1
    self.last_gate = gate
    for service, age in self.ages_ms.items():
      if age is not None and age > self.max_age_ms.get(service, float('-inf')):
        self.max_age_ms[service] = age

  def flush(self, now_ns: int):
    if self.ticks and self.events < MAX_EVENTS:
      self.events += 1
      cloudlog.event('lane_centering_gates', window_s=round((now_ns - self.window_start_ns) / 1e9, 2), ticks=self.ticks,
                     flips=self.flips, gates=dict(sorted(self.gates.items(), key=lambda item: -item[1])),
                     max_age_ms=self.max_age_ms, freq_hz=self.freq_hz)
    self.window_start_ns = now_ns
    self._clear()


class GateLoggedHost(LaneCenteringHost):
  def __init__(self, params, counter: GateCounter):
    super().__init__(params)
    self.counter = counter

  def sample(self, sm, *, now_ns: int, lateral_active: bool, longitudinal_active: bool):
    request = super().sample(sm, now_ns=now_ns, lateral_active=lateral_active, longitudinal_active=longitudinal_active)
    if now_ns <= 0:
      return request
    self.counter.start_tick(sm, now_ns)
    # Only the ticks where the driver wants lane centering and steering is engaged are of interest.
    if request is not None or not lateral_active or not self.settings.enabled:
      return request
    failed = []
    state = sm['carState']
    if not state.canValid:
      failed.append('can_invalid')
    if state.canTimeout:
      failed.append('can_timeout')
    for service in self.REQUIRED:
      checks = _checks(sm, service)
      failed += checks
      if any(check.startswith('freq:') for check in checks):
        self.counter.note_freq(sm, service)
      stamp = int(sm.logMonoTime[service])
      if stamp <= 0:
        failed.append(f'never_seen:{service}')
      elif now_ns - stamp < 0:
        failed.append(f'future:{service}')
      elif now_ns - stamp > _limit_ns(service):
        failed.append(f'stale:{service}')
    self.counter.record('host:' + ('+'.join(failed) or 'unknown'))
    return request


class GateLoggedController(LaneCenteringController):
  def __init__(self, counter: GateCounter, **kwargs):
    super().__init__(**kwargs)
    self.counter = counter

  def update(self, observation):
    result = super().update(observation)
    try:
      if not observation.lateral_active or not observation.settings.enabled:
        return result
      if result.reason != 'inactive':
        self.counter.record(result.reason)
        return result
      failed = []
      if not observation.mode.lateral_authority:
        failed.append(f'mode:{observation.mode}')
      if not observation.model_valid:
        failed.append('model_invalid' + (f'({",".join(self.counter.model_checks)})' if self.counter.model_checks else ''))
      if observation.speed_mps < MIN_SPEED:
        failed.append('slow')
      self.counter.record('update:' + ('+'.join(failed) or 'unknown'))
    except AttributeError:
      pass
    return result


def wrap(CP, controller: LaneCenteringController, host: LaneCenteringHost | None, params):
  """Swap in the logging subclasses on the retrofit; other cars keep the upstream objects."""
  if not is_retrofit(CP) or host is None:
    return controller, host
  counter = GateCounter()
  return (GateLoggedController(counter, body=controller._body, body_required=controller._body_required),
          GateLoggedHost(params, counter))

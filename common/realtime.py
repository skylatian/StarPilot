"""Utilities for reading real time clocks and keeping soft real time constraints."""
import gc
import os
import sys
import time

from setproctitle import getproctitle

from openpilot.common.util import MovingAverage
from openpilot.system.hardware import PC


# time step for each process
DT_CTRL = 0.01  # controlsd
DT_MDL = 0.05  # model
DT_HW = 0.5  # hardwared and manager
DT_DMON = 0.05  # driver monitoring


class Priority:
  # CORE 2
  # - modeld = 55
  # - camerad = 54
  CTRL_LOW = 51 # plannerd & radard
  UI = 50

  # CORE 3
  # - pandad = 55
  CTRL_HIGH = 53


# Cores the realtime processes leave to ordinary work on comma devices (athenad, uploader and loggerd run here too).
BACKGROUND_CORES = (0, 1, 2, 3)


def drop_realtime_priority() -> None:
  """Make the caller ordinary background work: SCHED_OTHER on BACKGROUND_CORES.

  Pass it as preexec_fn when a process that ran config_realtime_process starts a subprocess. A child
  inherits SCHED_FIFO and the parent's cores, and nice has no effect on a realtime task, so a busy child
  otherwise outranks everything else on that core. From starpilot_process (FIFO 51, core 5) that is
  above the UI (FIFO 50, core 5): the Galaxy dashboard analyzer froze the UI for 46-49 s that way.

  Called in a thread, it moves only that thread (Linux applies both calls per thread). It is a no-op
  for a caller that is not realtime, which includes every desktop host. It runs between fork and exec,
  so it must not import, log or take locks.
  """
  try:
    if os.sched_getscheduler(0) not in (os.SCHED_FIFO, os.SCHED_RR):
      return
    os.sched_setscheduler(0, os.SCHED_OTHER, os.sched_param(0))
  except (AttributeError, OSError):
    return
  try:
    os.sched_setaffinity(0, BACKGROUND_CORES)
  except OSError:
    pass


def set_core_affinity(cores: list[int]) -> None:
  if sys.platform == 'linux' and not PC:
    try:
      os.sched_setaffinity(0, cores)
    except OSError:
      pass


def config_realtime_process(cores: int | list[int], priority: int) -> None:
  gc.disable()
  if sys.platform == 'linux' and not PC:
    os.sched_setscheduler(0, os.SCHED_FIFO, os.sched_param(priority))
  c = cores if isinstance(cores, list) else [cores, ]
  set_core_affinity(c)


class Ratekeeper:
  def __init__(self, rate: float, print_delay_threshold: float | None = 0.0) -> None:
    """Rate in Hz for ratekeeping. print_delay_threshold must be nonnegative."""
    self._interval = 1. / rate
    self._print_delay_threshold = print_delay_threshold
    self._frame = 0
    self._remaining = 0.0
    self._process_name = getproctitle()
    self._last_monitor_time = -1.
    self._next_frame_time = -1.

    self.avg_dt = MovingAverage(100)
    self.avg_dt.add_value(self._interval)

  @property
  def frame(self) -> int:
    return self._frame

  @property
  def remaining(self) -> float:
    return self._remaining

  @property
  def lagging(self) -> bool:
    expected_dt = self._interval * (1 / 0.9)
    return self.avg_dt.get_average() > expected_dt

  # Maintain loop rate by calling this at the end of each loop
  def keep_time(self) -> bool:
    lagged = self.monitor_time()
    if self._remaining > 0:
      time.sleep(self._remaining)
    return lagged

  # Monitors the cumulative lag, but does not enforce a rate
  def monitor_time(self) -> bool:
    if self._last_monitor_time < 0:
      self._next_frame_time = time.monotonic() + self._interval
      self._last_monitor_time = time.monotonic()

    prev = self._last_monitor_time
    self._last_monitor_time = time.monotonic()
    self.avg_dt.add_value(self._last_monitor_time - prev)

    lagged = False
    remaining = self._next_frame_time - time.monotonic()
    self._next_frame_time += self._interval
    if self._print_delay_threshold is not None and remaining < -self._print_delay_threshold:
      print(f"{self._process_name} lagging by {-remaining * 1000:.2f} ms")
      lagged = True
    self._frame += 1
    self._remaining = remaining
    return lagged

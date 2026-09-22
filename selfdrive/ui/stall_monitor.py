import os
import resource
import sys
import time
import traceback
import threading
from collections import Counter, deque
from pathlib import Path
from typing import Any

from openpilot.common.swaglog import cloudlog


def _capture_message(*args, **kwargs) -> None:
  from openpilot.system import sentry
  sentry.capture_message(*args, **kwargs)


def _default_dump_dir() -> Path:
  for candidate in ("/data/log", "/tmp"):
    if os.path.isdir(candidate) and os.access(candidate, os.W_OK):
      return Path(candidate)
  return Path.cwd()


class UIStallMonitor:
  def __init__(self, name: str):
    self._name = name
    self._threshold_s = float(os.getenv("UI_STALL_PROBE_MAX_DT", "5"))
    self._poll_s = float(os.getenv("UI_STALL_PROBE_POLL_DT", "0.25"))
    self._hitch_threshold_s = float(os.getenv("UI_HITCH_PROBE_MAX_DT", "0.25"))
    self._hitch_report_interval_s = max(self._poll_s, float(os.getenv("UI_HITCH_REPORT_INTERVAL", "300")))
    self._hitch_report_min_count = max(1, int(os.getenv("UI_HITCH_REPORT_MIN_COUNT", "3")))
    self._hitch_log_interval_s = max(0.0, float(os.getenv("UI_HITCH_LOG_INTERVAL", "10")))

    # A stall parked inside a native graphics call is the display/GPU block, not a wedged
    # loop -- see the GPU guard in _run(). Kick in from below the 10s watchdog so there is
    # room to act, and stop kicking after _gpu_guard_max_s so a genuine hang still dies.
    self._gpu_guard_enabled = os.getenv("UI_GPU_GUARD", "1") == "1"
    self._gpu_guard_after_s = float(os.getenv("UI_GPU_GUARD_AFTER", "3"))
    self._gpu_guard_max_s = float(os.getenv("UI_GPU_GUARD_MAX", "60"))
    self._gpu_guard_kicks = 0
    self._gpu_guard_active = False
    self._gpu_guard_gave_up = False
    self._dump_dir = _default_dump_dir()
    self._main_thread_id = threading.get_ident()

    now = time.monotonic()
    self._last_progress = now
    self._phase = "init"
    self._phase_entered = now
    self._stall_reported = False
    self._stalled_since = now
    self._stalled_phase = self._phase
    self._context: dict[str, Any] = {}

    self._hitch_counts: Counter[str] = Counter()
    self._hitch_max_s: dict[str, float] = {}
    self._recent_hitches = deque(maxlen=max(1, int(os.getenv("UI_HITCH_HISTORY_LEN", "16"))))
    self._hitch_window_started = now
    self._last_hitch_report = now
    self._last_hitch_log = now - self._hitch_log_interval_s

    self._lock = threading.Lock()
    self._history = deque(maxlen=max(1, int(os.getenv("UI_STALL_HISTORY_LEN", "64"))))
    self._history.append((now, self._phase))
    self._stop_event = threading.Event()
    self._thread = threading.Thread(target=self._run, name=f"{name}_stall_probe", daemon=True)

  def start(self) -> None:
    if self._threshold_s <= 0.0 and self._hitch_threshold_s <= 0.0:
      return
    self._thread.start()

  def stop(self) -> None:
    if self._threshold_s <= 0.0 and self._hitch_threshold_s <= 0.0:
      return
    self._stop_event.set()
    self._thread.join(timeout=1.0)

  def set_context(self, context: dict[str, Any]) -> None:
    with self._lock:
      self._context = dict(context)

  def progress(self, phase: str) -> None:
    now = time.monotonic()
    recovered = None
    hitch_warning = None

    with self._lock:
      previous_phase = self._phase
      phase_duration_s = now - self._last_progress
      if phase != self._phase:
        self._phase = phase
        self._phase_entered = now
        self._history.append((now, phase))
      self._last_progress = now

      if self._hitch_threshold_s > 0.0 and phase_duration_s >= self._hitch_threshold_s:
        self._hitch_counts[previous_phase] += 1
        self._hitch_max_s[previous_phase] = max(phase_duration_s, self._hitch_max_s.get(previous_phase, 0.0))
        self._recent_hitches.append({
          "phase": previous_phase,
          "next_phase": phase,
          "duration_ms": round(phase_duration_s * 1000.0, 1),
          "monotonic": round(now, 3),
        })
        if now - self._last_hitch_log >= self._hitch_log_interval_s:
          self._last_hitch_log = now
          hitch_warning = (previous_phase, phase, phase_duration_s)

      if self._stall_reported:
        recovered = (now - self._stalled_since, self._stalled_phase, phase)
        self._stall_reported = False

    if hitch_warning is not None:
      previous_phase, current_phase, duration_s = hitch_warning
      cloudlog.warning(f"{self._name} frame hitch {duration_s * 1000.0:.0f}ms in phase={previous_phase} (next_phase={current_phase})")

    if recovered is not None:
      stalled_for_s, stalled_phase, current_phase = recovered
      cloudlog.warning(f"{self._name} stall recovered after {stalled_for_s:.1f}s (stalled_phase={stalled_phase}, current_phase={current_phase})")

  def _run(self) -> None:
    while not self._stop_event.wait(self._poll_s):
      now = time.monotonic()
      with self._lock:
        stalled_for_s = now - self._last_progress
        phase = self._phase
        phase_for_s = now - self._phase_entered
        already_reported = self._stall_reported

        should_report_stall = self._threshold_s > 0.0 and stalled_for_s >= self._threshold_s and not already_reported
        if should_report_stall:
          self._stall_reported = True
          self._stalled_since = self._last_progress
          self._stalled_phase = phase

      if should_report_stall:
        frames = sys._current_frames()
        preview = self._main_thread_preview(frames)
        dump = self._build_dump(now, phase, stalled_for_s, phase_for_s, frames=frames)
        dump_path = self._write_dump(dump)
        self._report_stall(dump, dump_path, phase, stalled_for_s, phase_for_s, preview=preview)

      self._service_gpu_guard(stalled_for_s, phase)

      hitch_report = self._take_hitch_report(now)
      if hitch_report is not None:
        self._report_hitches(hitch_report)

  def _service_gpu_guard(self, stalled_for_s: float, phase: str) -> None:
    """Keep the watchdog alive while the main thread is blocked inside a native GL call.

    Manager SIGKILLs `ui` when its loop has not kicked for UI_WATCHDOG_MAX_DT (10s), and
    the kick lives inside the render loop -- so any render stall past 10s restarts the
    process, costing ~8s of layout init and the user's place in the UI. Measured on device
    2026-09-18: rl.end_drawing() blocked 4.7s and the next frame's rl.draw_circle() blocked
    5.2s back to back, and the watchdog killed it at dt=10.312.

    Those stalls also happen under the Qt UI on this device, which does not restart nearly
    as often -- so the stall itself is a platform (display/GPU) problem, while the restart
    loop is ours. A process blocked in eglSwapBuffers is not wedged; it is waiting on the
    GPU and will come back. Kick for it, and let everything else die exactly as before:
    a stall in our own Python code never reaches this guard's kick path.
    """
    if not self._gpu_guard_enabled:
      return

    if stalled_for_s < self._gpu_guard_after_s:
      # Loop is healthy (or only briefly behind) -- reset for the next stall.
      if self._gpu_guard_active:
        cloudlog.warning(f"{self._name} gpu guard released after {self._gpu_guard_kicks} kicks")
      self._gpu_guard_active = False
      self._gpu_guard_gave_up = False
      self._gpu_guard_kicks = 0
      return

    where = self._main_thread_in_native_gfx()
    if where is None:
      # Stalled, but not in a graphics call. That is a real hang -- do not mask it.
      return

    if stalled_for_s >= self._gpu_guard_max_s:
      if not self._gpu_guard_gave_up:
        self._gpu_guard_gave_up = True
        cloudlog.error(f"{self._name} gpu guard gave up after {stalled_for_s:.1f}s in {where} (phase={phase}); letting the watchdog fire")
      return

    if not self._gpu_guard_active:
      self._gpu_guard_active = True
      cloudlog.error(f"{self._name} gpu stall: main thread blocked {stalled_for_s:.1f}s in {where} (phase={phase}); holding off the watchdog")

    from openpilot.common.watchdog import kick_watchdog
    kick_watchdog()
    self._gpu_guard_kicks += 1

  def _report_stall(self, dump: str, dump_path: Path | None, phase: str, stalled_for_s: float, phase_for_s: float,
                    preview: str | None = None) -> None:
    preview = preview if preview is not None else self._main_thread_preview()
    path_s = str(dump_path) if dump_path is not None else "<write_failed>"
    with self._lock:
      context = dict(self._context)

    cloudlog.error(f"{self._name} main loop stalled for {stalled_for_s:.1f}s in phase={phase} (phase_for={phase_for_s:.1f}s) dump={path_s}\n{preview}")
    tags = {
      "ui_stall_name": self._name,
      "ui_stall_phase": phase,
    }
    if "ui_mode" in context:
      tags["ui_mode"] = str(context["ui_mode"])
    if "started" in context:
      tags["ui_onroad"] = str(bool(context["started"])).lower()

    _capture_message(
      "raylib UI main loop stalled",
      tags=tags,
      extras={
        "pid": os.getpid(),
        "stalled_for_s": round(stalled_for_s, 3),
        "phase_for_s": round(phase_for_s, 3),
        "dump_path": path_s,
        "main_thread_stack": preview,
        "thread_dump": dump,
        "ui_context": context,
        "runtime_metrics": self._runtime_metrics(),
      },
      attachment_path=dump_path,
      flush_timeout=2.0,
    )

  def _take_hitch_report(self, now: float) -> dict[str, Any] | None:
    with self._lock:
      count = sum(self._hitch_counts.values())
      if now - self._last_hitch_report < self._hitch_report_interval_s or count < self._hitch_report_min_count:
        return None

      report = {
        "window_s": round(now - self._hitch_window_started, 3),
        "hitch_threshold_ms": round(self._hitch_threshold_s * 1000.0, 1),
        "total_hitches": count,
        "phase_counts": dict(self._hitch_counts),
        "phase_max_ms": {phase: round(duration_s * 1000.0, 1) for phase, duration_s in self._hitch_max_s.items()},
        "recent_hitches": list(self._recent_hitches),
        "ui_context": dict(self._context),
      }
      self._hitch_counts.clear()
      self._hitch_max_s.clear()
      self._recent_hitches.clear()
      self._hitch_window_started = now
      self._last_hitch_report = now
      return report

  def _report_hitches(self, report: dict[str, Any]) -> None:
    phase_max_ms = report["phase_max_ms"]
    worst_phase = max(phase_max_ms, key=phase_max_ms.get)
    context = report["ui_context"]
    tags = {
      "ui_stall_name": self._name,
      "ui_hitch_worst_phase": worst_phase,
    }
    if "ui_mode" in context:
      tags["ui_mode"] = str(context["ui_mode"])
    if "started" in context:
      tags["ui_onroad"] = str(bool(context["started"])).lower()

    _capture_message(
      "raylib UI frame hitches",
      level="warning",
      tags=tags,
      extras={**report, "runtime_metrics": self._runtime_metrics()},
      flush_timeout=0.25,
    )

  @staticmethod
  def _runtime_metrics() -> dict[str, Any]:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    try:
      load_average = [round(value, 3) for value in os.getloadavg()]
    except OSError:
      load_average = []
    return {
      "load_average": load_average,
      "max_rss_kb": usage.ru_maxrss,
      "user_cpu_s": round(usage.ru_utime, 3),
      "system_cpu_s": round(usage.ru_stime, 3),
      "thread_count": threading.active_count(),
    }

  def _build_dump(self, now: float, phase: str, stalled_for_s: float, phase_for_s: float,
                  frames: dict[int, Any] | None = None) -> str:
    frames = frames if frames is not None else sys._current_frames()
    threads = {thread.ident: thread for thread in threading.enumerate()}
    lines = [
      f"name={self._name}",
      f"pid={os.getpid()}",
      f"wall_time={time.strftime('%Y-%m-%dT%H:%M:%S%z')}",
      f"monotonic={now:.6f}",
      f"stalled_for_s={stalled_for_s:.3f}",
      f"phase={phase}",
      f"phase_for_s={phase_for_s:.3f}",
      "",
    ]

    with self._lock:
      history = list(self._history)

    lines.append("Recent phase transitions:")
    for ts, phase_name in history:
      age_s = now - ts
      lines.append(f"  - {ts:.6f} ({age_s:.3f}s ago) {phase_name}")
    lines.append("")

    ordered_idents = sorted(frames.keys(), key=lambda ident: ident != self._main_thread_id)
    for ident in ordered_idents:
      thread = threads.get(ident)
      name = thread.name if thread is not None else "<unknown>"
      daemon = thread.daemon if thread is not None else None
      lines.append(f"Thread {name} ident={ident} daemon={daemon}")
      lines.extend(traceback.format_stack(frames[ident]))
      lines.append("")

    return "".join(line if line.endswith("\n") else f"{line}\n" for line in lines)

  # Frames whose innermost Python entry means "we called into native graphics and it has
  # not come back". pyray wraps every raylib entry point, so a blocked eglSwapBuffers or a
  # blocked GPU submit leaves the wrapper as the top Python frame -- that is exactly what
  # the 2026-09-18 dumps showed (pyray/__init__.py:94 in wrapped_func, inside draw_circle).
  _NATIVE_GFX_MARKERS = ("/pyray/", "/raylib/", "_raylib_cffi")

  def _main_thread_in_native_gfx(self, frames: dict[int, Any] | None = None) -> str | None:
    """Return a description when the main thread is parked in a native graphics call.

    Only the innermost frame counts. A GL call that is merely somewhere up the stack has
    already returned; what matters is whether the thread is sitting in one right now.
    """
    frames = frames if frames is not None else sys._current_frames()
    frame = frames.get(self._main_thread_id)
    if frame is None:
      return None
    path = frame.f_code.co_filename
    if not any(marker in path for marker in self._NATIVE_GFX_MARKERS):
      return None
    # Name our own call site, which is the frame below the wrapper, so the log says
    # "draw_circle in aethergrid" rather than just "wrapped_func".
    caller = frame.f_back
    while caller is not None:
      cpath = caller.f_code.co_filename
      if "/openpilot/" in cpath and "site-packages" not in cpath:
        rel = cpath.split("/openpilot/", 1)[-1]
        return f"{frame.f_code.co_name} <- {rel}:{caller.f_lineno} in {caller.f_code.co_name}"
      caller = caller.f_back
    return frame.f_code.co_name

  def _main_thread_preview(self, frames: dict[int, Any] | None = None) -> str:
    frames = frames if frames is not None else sys._current_frames()
    frame = frames.get(self._main_thread_id)
    if frame is None:
      return "main_thread_stack=<unavailable>"
    stack_lines = traceback.format_stack(frame)
    preview = "".join(stack_lines[-8:]).strip()
    return f"main_thread_stack:\n{preview}" if preview else "main_thread_stack=<empty>"

  def _write_dump(self, dump: str) -> Path | None:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = self._dump_dir / f"{self._name}_stall_{os.getpid()}_{timestamp}.log"
    try:
      path.write_text(dump)
      return path
    except OSError as e:
      cloudlog.error(f"failed to write {self._name} stall dump to {path}: {e}")
      return None


class StartupGuard:
  """Kick the watchdog and sample the main thread across a long, uninterruptible init.

  MainLayout() builds every settings panel eagerly, and on device that block does
  D-Bus round trips to NetworkManager and BlueZ, several param writes (each a global
  flock plus two fsyncs), an SSL handshake from ModelManager and a zmq poll -- none of
  which the host sees, which is why it measures 0.18s on a Mac and 5.6-10.5s on a C3.

  ui.py kicks the watchdog once before that block and once after, so an init slower
  than UI_WATCHDOG_MAX_DT (10s) gets the process SIGKILLed, restarted, and sent
  straight back into the same block. A process that is still constructing widgets is
  alive, so kick while it runs -- but only up to `max_grace_s`, after which a genuine
  hang is allowed to die as before.

  While kicking, sample where the main thread actually is. The stall dump gives one
  sample per stall; this gives a distribution over the whole init, which is what
  names the slow panel.
  """

  def __init__(self, name: str, max_grace_s: float = 45.0, poll_s: float = 0.1,
               report_top: int = 8):
    self._name = name
    self._max_grace_s = max_grace_s
    self._poll_s = poll_s
    self._report_top = report_top
    self._main_thread_id = threading.get_ident()
    self._stop = threading.Event()
    self._samples: Counter[str] = Counter()
    self._kicks = 0
    self._gave_up = False
    self._thread = threading.Thread(target=self._run, name=f"{name}_startup_guard", daemon=True)
    self._t0 = 0.0

  @staticmethod
  def _describe(frame) -> str:
    path = frame.f_code.co_filename
    rel = path.split("/openpilot/", 1)[-1] if "/openpilot/" in path else path
    return f"{rel}:{frame.f_lineno} in {frame.f_code.co_name}"

  def _sample_main(self) -> str | None:
    innermost = frame = sys._current_frames().get(self._main_thread_id)
    if frame is None:
      return None
    # Prefer the innermost frame that belongs to openpilot, so the sample names our
    # own call site rather than the stdlib or site-packages function it is sitting in.
    # Fall back to the innermost frame, so a main thread parked entirely inside a
    # library (a D-Bus reply wait, an SSL handshake) still reports something.
    while frame is not None:
      path = frame.f_code.co_filename
      if "/openpilot/" in path and "site-packages" not in path:
        return self._describe(frame)
      frame = frame.f_back
    return self._describe(innermost)

  def _run(self) -> None:
    from openpilot.common.watchdog import kick_watchdog
    while not self._stop.wait(self._poll_s):
      sample = self._sample_main()
      if sample is not None:
        self._samples[sample] += 1
      if time.monotonic() - self._t0 < self._max_grace_s:
        kick_watchdog()
        self._kicks += 1
      elif not self._gave_up:
        self._gave_up = True
        cloudlog.error(f"{self._name} startup guard gave up after {self._max_grace_s:.0f}s; letting the watchdog fire. main thread at: {sample}")

  def __enter__(self) -> "StartupGuard":
    self._t0 = time.monotonic()
    self._thread.start()
    return self

  def __exit__(self, *exc_info) -> None:
    self._stop.set()
    self._thread.join(timeout=1.0)
    elapsed = time.monotonic() - self._t0
    if elapsed < 1.0 or not self._samples:
      return
    total = sum(self._samples.values())
    top = "".join(
      f"\n  {count * self._poll_s:5.2f}s ({100.0 * count / total:4.1f}%) {site}"
      for site, count in self._samples.most_common(self._report_top)
    )
    log = cloudlog.warning if elapsed < 5.0 else cloudlog.error
    log(f"{self._name} took {elapsed:.1f}s ({self._kicks} watchdog kicks). Main thread spent it here:{top}")

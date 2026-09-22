from openpilot.selfdrive.ui import stall_monitor


def test_stall_report_is_sent_to_bugsink(monkeypatch, tmp_path):
  report = {}

  def capture_message(message, **kwargs):
    report["message"] = message
    report.update(kwargs)

  monkeypatch.setattr(stall_monitor, "_capture_message", capture_message)

  monitor = stall_monitor.UIStallMonitor("raylib_ui")
  monitor._dump_dir = tmp_path
  dump = "full thread dump"
  dump_path = monitor._write_dump(dump)
  monitor._report_stall(dump, dump_path, "gui_app.present_end", 5.001, 4.999)

  assert report["message"] == "raylib UI main loop stalled"
  assert report["tags"] == {"ui_stall_name": "raylib_ui", "ui_stall_phase": "gui_app.present_end"}
  assert report["extras"]["stalled_for_s"] == 5.001
  assert report["extras"]["phase_for_s"] == 4.999
  assert "test_stall_report_is_sent_to_bugsink" in report["extras"]["main_thread_stack"]
  assert report["extras"]["thread_dump"] == dump
  assert report["attachment_path"] == dump_path


def test_phase_hitches_are_aggregated(monkeypatch):
  now = [100.0]
  monkeypatch.setattr(stall_monitor.time, "monotonic", lambda: now[0])
  monkeypatch.setattr(stall_monitor.cloudlog, "warning", lambda *_args, **_kwargs: None)

  monitor = stall_monitor.UIStallMonitor("raylib_ui")
  monitor._hitch_report_interval_s = 1.0
  monitor._hitch_report_min_count = 2
  monitor.set_context({"ui_mode": "small", "started": True})
  monitor.progress("gui_app.before_widget_render")

  now[0] += 0.4
  monitor.progress("gui_app.after_widget_render")
  now[0] += 0.3
  monitor.progress("gui_app.before_end_drawing")
  now[0] += 0.4

  report = monitor._take_hitch_report(now[0])

  assert report is not None
  assert report["total_hitches"] == 2
  assert report["phase_counts"] == {
    "gui_app.before_widget_render": 1,
    "gui_app.after_widget_render": 1,
  }
  assert report["phase_max_ms"]["gui_app.before_widget_render"] == 400.0
  assert report["ui_context"] == {"ui_mode": "small", "started": True}


def test_hitch_report_is_rate_limited_and_sent_to_bugsink(monkeypatch):
  reports = []
  monkeypatch.setattr(stall_monitor, "_capture_message", lambda message, **kwargs: reports.append((message, kwargs)))
  monitor = stall_monitor.UIStallMonitor("raylib_ui")
  monitor._hitch_counts.update({"gui_app.before_end_drawing": 3})
  monitor._hitch_max_s["gui_app.before_end_drawing"] = 0.75
  monitor._hitch_report_interval_s = 10.0
  monitor._hitch_report_min_count = 3
  monitor._last_hitch_report = 5.0
  monitor._hitch_window_started = 5.0
  monitor.set_context({"ui_mode": "small", "started": False})

  assert monitor._take_hitch_report(14.9) is None
  report = monitor._take_hitch_report(15.0)
  assert report is not None
  monitor._report_hitches(report)

  message, kwargs = reports[0]
  assert message == "raylib UI frame hitches"
  assert kwargs["level"] == "warning"
  assert kwargs["tags"] == {
    "ui_stall_name": "raylib_ui",
    "ui_hitch_worst_phase": "gui_app.before_end_drawing",
    "ui_mode": "small",
    "ui_onroad": "false",
  }
  assert kwargs["extras"]["total_hitches"] == 3
  assert monitor._take_hitch_report(30.0) is None


def test_stall_report_uses_captured_stack_preview(monkeypatch, tmp_path):
  report = {}
  monkeypatch.setattr(stall_monitor, "_capture_message", lambda _message, **kwargs: report.update(kwargs))
  monitor = stall_monitor.UIStallMonitor("raylib_ui")
  dump_path = monitor._write_dump("thread dump")

  monitor._report_stall("thread dump", dump_path, "gui_app.before_end_drawing", 5.0, 5.0,
                        preview="main_thread_stack:\ncaptured before recovery")

  assert report["extras"]["main_thread_stack"] == "main_thread_stack:\ncaptured before recovery"


def _frame_in(filename):
  """A real frame object whose code lives in `filename`, for the native-GL detector."""
  src = "def f():\n  import sys\n  return sys._getframe()\n"
  ns: dict = {}
  exec(compile(src, filename, "exec"), ns)
  return ns["f"]()


def test_gpu_guard_holds_off_watchdog_only_for_native_gl_stalls(monkeypatch):
  """A stall inside a GL call must not restart the UI; a wedged Python loop still must.

  Measured on device 2026-09-18: rl.end_drawing() blocked 4.7s and the next frame's
  rl.draw_circle() blocked 5.2s, and manager SIGKILLed ui at dt=10.312. Those same
  stalls happen under the Qt UI, which does not restart nearly as often, so the stall
  is a platform problem while the restart loop is ours.
  """
  kicks = []
  monkeypatch.setattr(stall_monitor.cloudlog, "error", lambda *_a, **_k: None)
  monkeypatch.setattr(stall_monitor.cloudlog, "warning", lambda *_a, **_k: None)

  import sys as _sys
  import types as _types
  fake = _types.ModuleType("openpilot.common.watchdog")
  fake.kick_watchdog = lambda: kicks.append(1)
  monkeypatch.setitem(_sys.modules, "openpilot.common.watchdog", fake)

  monitor = stall_monitor.UIStallMonitor("raylib_ui")
  monitor._gpu_guard_after_s = 1.0
  monitor._gpu_guard_max_s = 10.0

  gl_frame = _frame_in("/venv/lib/python3.12/site-packages/pyray/__init__.py")
  py_frame = _frame_in("/data/openpilot/openpilot/selfdrive/ui/layouts/main.py")

  # Stalled in a native GL call -> kick, so the watchdog does not fire.
  monkeypatch.setattr(stall_monitor.sys, "_current_frames",
                      lambda: {monitor._main_thread_id: gl_frame})
  monitor._service_gpu_guard(5.0, "gui_app.before_end_drawing")
  assert len(kicks) == 1

  # Stalled in our own Python -> a genuine hang, must be left to die.
  monkeypatch.setattr(stall_monitor.sys, "_current_frames",
                      lambda: {monitor._main_thread_id: py_frame})
  monitor._service_gpu_guard(5.0, "gui_app.before_widget_render")
  assert len(kicks) == 1

  # Below the engage threshold -> nothing, whatever the thread is doing.
  monkeypatch.setattr(stall_monitor.sys, "_current_frames",
                      lambda: {monitor._main_thread_id: gl_frame})
  monitor._service_gpu_guard(0.5, "gui_app.before_end_drawing")
  assert len(kicks) == 1

  # Past the cap -> stop covering for it and let the watchdog fire.
  monitor._service_gpu_guard(11.0, "gui_app.before_end_drawing")
  assert len(kicks) == 1
  assert monitor._gpu_guard_gave_up

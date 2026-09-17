import pytest

from openpilot.system.ui.lib import application
from openpilot.system.ui.lib.application import gui_app, settle
from openpilot.system.ui.lib.scroll_panel2 import GuiScrollPanel2, ScrollState


@pytest.fixture
def adaptive(monkeypatch):
  """Adaptive rendering on, with a controllable clock and no raylib calls."""
  clock = {"t": 1000.0}
  monkeypatch.setattr(application.time, "monotonic", lambda: clock["t"])
  monkeypatch.setattr(application.rl, "set_target_fps", lambda fps: None)
  gui_app.configure_adaptive_rendering(True)
  gui_app._high_fps_until = 0.0
  gui_app._apply_render_mode()
  yield clock
  gui_app.configure_adaptive_rendering(False)


def test_animating_holds_full_rate_only_while_called(adaptive):
  clock = adaptive
  assert gui_app.target_fps == gui_app._idle_target_fps

  gui_app.animating()
  assert gui_app.target_fps == gui_app._full_target_fps

  # still animating a few frames later: the hold window slides forward
  clock["t"] += application.UI_ANIMATION_FPS_HOLD * 0.8
  gui_app.animating()
  clock["t"] += application.UI_ANIMATION_FPS_HOLD * 0.8
  gui_app._apply_render_mode()
  assert gui_app.target_fps == gui_app._full_target_fps

  # nothing animating: back to the idle rate once the hold expires
  clock["t"] += application.UI_ANIMATION_FPS_HOLD * 1.1
  gui_app._apply_render_mode()
  assert gui_app.target_fps == gui_app._idle_target_fps


def test_animating_never_shortens_an_interaction_window(adaptive):
  gui_app.request_high_fps()  # a touch: 1.25 s
  until = gui_app._high_fps_until
  gui_app.animating()  # 0.3 s hold must not pull the deadline in
  assert gui_app._high_fps_until == until


def test_settle_snaps_within_eps_without_requesting_fps(monkeypatch):
  calls = []
  monkeypatch.setattr(gui_app, "animating", lambda: calls.append(1))
  assert settle(0.9995, 1.0) == 1.0
  assert settle(0.5, 0.5) == 0.5
  assert calls == []


def test_settle_keeps_value_and_requests_fps_while_converging(monkeypatch):
  calls = []
  monkeypatch.setattr(gui_app, "animating", lambda: calls.append(1))
  assert settle(0.6, 1.0) == 0.6
  assert settle(0.95, 1.0, eps=0.01) == 0.95
  assert len(calls) == 2


def test_scroll_momentum_requests_full_rate_until_steady(monkeypatch):
  calls = []
  monkeypatch.setattr(gui_app, "animating", lambda: calls.append(1))
  monkeypatch.setattr(application.rl, "get_frame_time", lambda: 1 / 60)

  panel = GuiScrollPanel2(horizontal=False)
  panel._state = ScrollState.AUTO_SCROLL
  panel._velocity = -400.0  # fling the content up, staying inside the scroll bounds
  panel._update_state(bounds_size=500.0, content_size=5000.0)
  assert panel._state == ScrollState.AUTO_SCROLL
  assert calls == [1]

  # once the fling has decayed the panel goes steady and stops asking
  panel._velocity = 0.0
  panel._update_state(bounds_size=500.0, content_size=5000.0)
  assert panel._state == ScrollState.STEADY
  panel._update_state(bounds_size=500.0, content_size=5000.0)
  assert calls == [1, 1]

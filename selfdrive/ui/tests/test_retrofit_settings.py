import math
import re

import pyray as rl
import pytest

from openpilot.common.basedir import BASEDIR
from openpilot.system.ui.lib.application import MouseEvent, MousePos
from openpilot.selfdrive.ui.layouts.settings.starpilot import retrofit


class FakeParams:
  """Shared store so every Params() the page code constructs sees the same values."""
  store: dict[str, float | bool] = {}

  def get_float(self, key, default=0.0, **kwargs):
    return float(self.store.get(key, default))

  def put_float(self, key, value, **kwargs):
    self.store[key] = float(value)

  def get_bool(self, key, **kwargs):
    return bool(self.store.get(key, False))

  def put_bool(self, key, value, **kwargs):
    self.store[key] = bool(value)


@pytest.fixture(autouse=True)
def fake_params(monkeypatch):
  FakeParams.store = {}
  monkeypatch.setattr(retrofit, "Params", FakeParams)
  return FakeParams


ALL_SPECS = retrofit.NONLINEAR_PARAMS + retrofit.ABCD_PARAMS + retrofit.FF_PARAMS + retrofit.TURN_PARAMS + retrofit.CENTER_PARAMS


def test_sigmoid_model_matches_car_interface():
  from opendbc.car.toyota.interface import _build_siglin_table, _user_params_to_abcd
  for strength, saturation, bias in ((0.0, 2.5, 0.0), (1.0, 0.5, -1.0), (0.4, 3.3, 0.25)):
    left, right = retrofit.user_params_to_abcd(strength, saturation, bias)
    assert (left, right) == _user_params_to_abcd(strength, saturation, bias)
    table, xs = _build_siglin_table(left, right)
    for i in range(0, len(xs), 25):
      assert math.isclose(retrofit.siglin_torque(float(xs[i]), left, right), float(table[i]), abs_tol=1e-9)


def test_tune_previews_match_controller_math():
  from openpilot.selfdrive.controls.lib import latcontrol_vehicle_tunes as vt
  tune = vt.RetrofitTuneParams(transition_speed=10.0, phase_scale=0.1, ff_gain=0.2, ff_onset=0.3, ff_onset_width=0.1, ff_cutoff=1.2,
                               ff_cutoff_width=0.4, friction_lat_rise=0.2, friction_jerk_rise=0.24, turn_in_boost=0.0, unwind_boost=0.0,
                               unwind_taper=0.0, turn_in_threshold_reduction=0.0, unwind_threshold_increase=0.0, turn_in_friction_boost=0.0,
                               unwind_friction_reduction=0.0, center_taper_max=0.25, center_taper_lat=0.14, center_taper_lat_width=0.04,
                               center_taper_speed=14.0, center_taper_speed_width=2.5)
  for lat_accel in (0.05, 0.3, 0.9, 1.5):
    # zero jerk => phase terms vanish, so the FF scale is just the onset/cutoff window the preview draws
    assert math.isclose(retrofit.ff_window_scale(lat_accel, 0.2, 0.3, 0.1, 1.2, 0.4), vt.get_retrofit_ff_scale(lat_accel, 0.0, 5.0, tune), rel_tol=1e-9)
    for v_ego in (10.0, 15.0, 20.0):
      assert math.isclose(retrofit.center_taper_scale(lat_accel, v_ego, 0.25, 0.14, 0.04, 14.0, 2.5),
                          vt.get_retrofit_center_taper_scale(lat_accel, v_ego, tune), rel_tol=1e-9)


def test_specs_cover_every_retrofit_tune_param_with_matching_defaults():
  keys_src = open(f"{BASEDIR}/common/params_keys.h").read()
  keys = set(re.findall(r'"(Retrofit(?:Tune|Nonlinear)[A-Za-z0-9_]+)"', keys_src))
  spec_keys = {p.key for p in ALL_SPECS} | {pt.key for pt in retrofit.KP_POINTS} | {"RetrofitNonlinearSteering", "RetrofitNonlinearAdvanced"}
  assert keys == spec_keys
  defaults = dict(re.findall(r'\{"(Retrofit[A-Za-z0-9_]+)", \{PERSISTENT, FLOAT, "([^"]*)"', keys_src))
  for spec in ALL_SPECS:
    assert math.isclose(float(defaults[spec.key]), spec.default), spec.key
    assert spec.min <= spec.default <= spec.max, spec.key
  for pt in retrofit.KP_POINTS:
    assert math.isclose(float(defaults[pt.key]), pt.default), pt.key
    assert pt.y_min <= pt.default <= pt.y_max, pt.key


def test_layout_has_every_page_and_reenters_sub_pages():
  layout = retrofit.StarPilotRetrofitLayout()
  assert set(layout._sub_panels) == {"tuning", "nonlinear", "nonlinear_advanced", "tune", "tune_kp", "tune_ff", "tune_turn", "tune_center"}

  pushed = []
  layout.set_navigate_callback(pushed.append)
  layout.show_event()

  # hub -> detail bubbles up through the sub-page to main_panel's stack callback
  layout._navigate_to("tune")
  layout._sub_panels["tune"]._navigate_to("tune_ff")
  assert pushed == ["tune", "tune_ff"]
  assert layout._current_sub_panel == "tune_ff"

  # back (main_panel restores the previous stack entry), then re-enter the same detail page
  layout.set_current_sub_panel("tune")
  layout._sub_panels["tune"]._navigate_to("tune_ff")
  assert pushed == ["tune", "tune_ff", "tune_ff"]
  assert layout._current_sub_panel == "tune_ff"


def test_switching_pages_reloads_previews(fake_params):
  layout = retrofit.StarPilotRetrofitLayout()
  layout.show_event()
  ff_page = layout._sub_panels["tune_ff"]
  fake_params.store["RetrofitTuneFFGain"] = 0.33
  layout.set_current_sub_panel("tune_ff")
  assert ff_page._preview._gain == pytest.approx(0.33)
  fake_params.store["RetrofitTuneFFGain"] = 0.11
  layout.set_current_sub_panel("tune")
  layout.set_current_sub_panel("tune_ff")
  assert ff_page._preview._gain == pytest.approx(0.11)


def test_opening_advanced_seeds_abcd_from_shape_params(fake_params):
  layout = retrofit.StarPilotRetrofitLayout()
  fake_params.store.update({"RetrofitNonlinearStrength": 0.6, "RetrofitNonlinearSaturation": 3.0, "RetrofitNonlinearBias": -0.5})
  layout.set_navigate_callback(lambda name: None)
  layout._sub_panels["nonlinear"]._open_advanced()
  left, right = retrofit.user_params_to_abcd(0.6, 3.0, -0.5)
  assert [fake_params.store[f"RetrofitNonlinearLeft{s}"] for s in "ABCD"] == pytest.approx(left)
  assert [fake_params.store[f"RetrofitNonlinearRight{s}"] for s in "ABCD"] == pytest.approx(right)
  assert layout._current_sub_panel == "nonlinear_advanced"

  # once raw ABCD mode is on, opening the page must not clobber the user's raw values
  fake_params.store["RetrofitNonlinearAdvanced"] = True
  fake_params.store["RetrofitNonlinearLeftA"] = 7.0
  layout._sub_panels["nonlinear"]._open_advanced()
  assert fake_params.store["RetrofitNonlinearLeftA"] == 7.0


def _event(x, y, *, pressed=False, released=False, down=True):
  return MouseEvent(MousePos(x, y), 0, pressed, released, down, 0.0)


def test_kp_editor_drag_writes_clamped_param(fake_params):
  editor = retrofit.KPCurveEditor()
  editor._plot = rl.Rectangle(0, 0, 1000, 500)
  editor.reload()
  point = retrofit.KP_POINTS[4]  # 5 m/s, default 11.5, clamp 0.1..50
  x, y = editor.sx(point.speed), editor.sy(point.default)

  editor._handle_mouse_press(MousePos(x + 10, y - 10))
  assert editor._drag == 4
  target_sy = editor.sy(20.0)
  editor._handle_mouse_event(_event(x, target_sy))
  assert editor._values[4] == pytest.approx(20.0, rel=1e-6)
  editor._handle_mouse_event(_event(x, target_sy, released=True, down=False))
  assert editor._drag is None
  assert fake_params.store[point.key] == pytest.approx(20.0, rel=1e-6)

  # dragging above the plot clamps to the point's own y_max, not the axis max
  editor._handle_mouse_press(MousePos(x, editor.sy(20.0)))
  editor._handle_mouse_event(_event(x, -50))
  editor._handle_mouse_release(MousePos(x, -50))
  assert fake_params.store[point.key] == point.y_max

  # a press far from every point starts no drag
  editor._handle_mouse_press(MousePos(x + 300, y + 300))
  assert editor._drag is None


def test_kp_editor_reset_restores_defaults(fake_params):
  editor = retrofit.KPCurveEditor()
  fake_params.store["RetrofitTuneKP1"] = 1.0
  editor.reset_defaults()
  assert all(fake_params.store[pt.key] == pt.default for pt in retrofit.KP_POINTS)
  assert editor._values == [pt.default for pt in retrofit.KP_POINTS]

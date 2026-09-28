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


def test_steer_angle_deadzone_default_matches_car_interface():
  # The deadzone default lives in two places: the param table (what the UI slider starts from)
  # and interface.py (the fallback when the key is absent from a stale compiled table).
  from opendbc.car.toyota.interface import RETROFIT_STEER_ANGLE_DEADZONE_DEG

  keys_src = open(f"{BASEDIR}/common/params_keys.h").read()
  defaults = dict(re.findall(r'\{"(Retrofit[A-Za-z0-9_]+)", \{PERSISTENT, FLOAT, "([^"]*)"', keys_src))
  assert math.isclose(float(defaults["RetrofitSteerAngleDeadzone"]), RETROFIT_STEER_ANGLE_DEADZONE_DEG)
  assert RETROFIT_STEER_ANGLE_DEADZONE_DEG > 0.0


def test_layout_has_every_page_and_reenters_sub_pages():
  layout = retrofit.StarPilotRetrofitLayout()
  assert set(layout._sub_panels) == {"tuning", "nnff", "nonlinear", "nonlinear_advanced", "tune", "tune_kp", "tune_ff", "tune_turn", "tune_center"}

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


class _UnsetParams:
  """Every key unset, like a fresh install or a newly added param: a bare read returns
  0.0, return_default=True returns the params_keys.h default — as the real Params does."""

  def __init__(self, table):
    self.table = table

  def get_float(self, key, return_default=False, default=0.0, **kwargs):
    return float(self.table[key]) if return_default and key in self.table else default


def test_tuning_rows_show_and_open_at_the_table_default_when_unset(monkeypatch):
  keys_src = open(f"{BASEDIR}/common/params_keys.h").read()
  table = dict(re.findall(r'\{"(Retrofit[A-Za-z0-9_]+)", \{PERSISTENT, FLOAT, "([^"]*)"', keys_src))

  layout = retrofit.StarPilotRetrofitLayout()
  opened = []
  pages = {
    "RetrofitNNFFFrictionAccel": "nnff",
    "RetrofitNNFFFrictionJerk": "nnff",
    "RetrofitSteerAngleDeadzone": "tune_center",
    "RetrofitPedalOffsetStandstill": "tuning",
  }
  for key, panel in pages.items():
    page = layout._sub_panels[panel]
    page._params = _UnsetParams(table)
    monkeypatch.setattr(page, "_show_slider", lambda key, lo, hi, **kw: opened.append((key, lo, hi, kw.get("current_value"))))
    rows = {row.id: row for section in page._manager_view._sections for row in section.rows}
    default = float(table[key])
    assert default != 0.0, key  # otherwise this row cannot tell the bug from the fix
    assert f"{default:.1f}" in rows[key].get_value() or f"{default:.2f}" in rows[key].get_value(), key
    rows[key].on_click()
    assert opened[-1][0] == key and opened[-1][3] == default, key


def test_nnff_friction_rows_open_sliders_matching_the_toggle_range(monkeypatch):
  # The UI slider range must match the clamp in starpilot_variables, or a value the slider
  # offers would be silently clamped before it reaches the controller.
  variables_src = open(f"{BASEDIR}/starpilot/common/starpilot_variables.py").read()
  clamps = {k: (float(lo), float(hi)) for k, lo, hi in re.findall(
    r'get_value\("(RetrofitNNFF[A-Za-z]+)", cast=float, default=[0-9.]+, min=([0-9.]+), max=([0-9.]+)\)', variables_src)}
  assert set(clamps) == {"RetrofitNNFFFrictionAccel", "RetrofitNNFFFrictionJerk"}

  page = retrofit.StarPilotRetrofitLayout()._sub_panels["nnff"]
  opened = []
  monkeypatch.setattr(page, "_show_slider", lambda key, lo, hi, **kw: opened.append((key, lo, hi)))
  rows = {row.id: row for section in page._manager_view._sections for row in section.rows}
  for key, (lo, hi) in clamps.items():
    assert key in rows, key
    rows[key].on_click()
    assert opened[-1] == (key, lo, hi)


class _StringParams:
  def __init__(self, store):
    self.store = store

  def get(self, key, encoding=None, **kwargs):
    return self.store.get(key)

  def put(self, key, value):
    self.store[key] = value


@pytest.mark.parametrize("selection, label", [
  (None, "Newest (v2_2026-02-01)"),
  ("", "Newest (v2_2026-02-01)"),
  ("v1_2026-01-01", "v1_2026-01-01"),
  ("v9_2026-01-01", "v9_2026-01-01 missing, using v2_2026-02-01"),
])
def test_nnff_model_row_label(selection, label):
  assert retrofit.nnff_model_label(selection or "", ["v2_2026-02-01", "v1_2026-01-01"]) == label
  assert retrofit.nnff_model_label("", []) == "None installed"


@pytest.mark.parametrize("panel, row_id", [
  ("nnff", "RetrofitNNFFModel"),  # NNFF Tune page
  (None, "RetrofitNNFFModelShortcut"),  # shortcut on the Retrofit Options hub
])
@pytest.mark.parametrize("picked, stored", [
  ("Newest (v2_2026-02-01)", ""),  # newest is stored as empty, so later models are followed
  ("v2_2026-02-01", "v2_2026-02-01"),  # picking the newest by name pins it
  ("v1_2026-01-01", "v1_2026-01-01"),
])
def test_nnff_model_picker_writes_selection(monkeypatch, picked, stored, panel, row_id):
  from openpilot.system.ui.widgets import DialogResult
  monkeypatch.setattr(retrofit, "get_retrofit_nnff_models", lambda: ["v2_2026-02-01", "v1_2026-01-01"])
  dialogs = []

  class FakeDialog:
    def __init__(self, title, options, current, callback):
      self.options, self.current, self.callback, self.selection = options, current, callback, None
      dialogs.append(self)

  monkeypatch.setattr(retrofit, "MultiOptionDialog", FakeDialog)
  monkeypatch.setattr(retrofit.gui_app, "push_widget", lambda w: None)

  layout = retrofit.StarPilotRetrofitLayout()
  page = layout._sub_panels[panel] if panel else layout
  store = {"RetrofitNNFFModel": "v1_2026-01-01"}
  page._params = _StringParams(store)
  rows = {row.id: row for section in page._manager_view._sections for row in section.rows}
  assert rows[row_id].get_value() == "v1_2026-01-01"

  rows[row_id].on_click()
  dialog = dialogs[-1]
  assert dialog.options == ["Newest (v2_2026-02-01)", "v2_2026-02-01", "v1_2026-01-01"]
  assert dialog.current == "v1_2026-01-01"
  dialog.selection = picked
  dialog.callback(DialogResult.CONFIRM)
  assert store["RetrofitNNFFModel"] == stored


class _BoolParams:
  def __init__(self, store):
    self.store = store

  def get_bool(self, key, **kwargs):
    return self.store.get(key, key == "LateralTune")  # params_keys.h default: LateralTune on, NNFF/NNFFLite off


@pytest.mark.parametrize("store, models, controller, tune_status, nnff_status", [
  ({}, ["v1"], "torque", "Active", "Inactive (NNFF off)"),
  ({"NNFF": True}, ["v1"], "nnff", "Inactive (NNFF on)", "Active"),
  ({"NNFF": True}, [], "torque", "Active", "Inactive (NNFF off)"),  # no model: NNFF toggle is inert
  ({"NNFF": True, "NNFFLite": True}, ["v1"], "nnff", "Inactive (NNFF on)", "Active"),  # NNFF wins over Lite
  ({"NNFF": True, "NNFFLite": True}, [], "nnff_lite", "Inactive (NNFF Lite on)", "Inactive (NNFF Lite on)"),
  ({"NNFFLite": True}, ["v1"], "nnff_lite", "Inactive (NNFF Lite on)", "Inactive (NNFF Lite on)"),
  ({"NNFF": True, "LateralTune": False}, ["v1"], "torque", "Active", "Inactive (NNFF off)"),  # both need Lateral Tuning
])
def test_controller_status_follows_controlsd_selection(monkeypatch, store, models, controller, tune_status, nnff_status):
  monkeypatch.setattr(retrofit, "get_retrofit_nnff_models", lambda: models)
  params = _BoolParams(store)
  assert retrofit.lateral_controller(params) == controller
  assert retrofit.controller_tune_status(params) == tune_status
  assert retrofit.nnff_tune_status(params) == nnff_status

  layout = retrofit.StarPilotRetrofitLayout()
  layout._params = params
  rows = {row.id: row for section in layout._manager_view._sections for row in section.rows}
  assert rows["RetrofitTuneNav"].get_value() == tune_status
  assert rows["RetrofitNNFFTuneNav"].get_value() == nnff_status


def test_tune_rows_show_the_spec_default_when_unset(fake_params):
  # _value_row must display the same default its slider opens at, not 0.0 for a never-written key.
  page = retrofit.StarPilotRetrofitLayout()._sub_panels["tune_center"]
  rows = {row.id: row for section in page._manager_view._sections for row in section.rows}
  for p in retrofit.CENTER_PARAMS:
    assert rows[p.key].get_value() == retrofit.format_adjustor_value(p.default, step=p.step), p.key

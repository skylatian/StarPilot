from opendbc.car.hyundai.values import CAR as HYUNDAI_CAR

from openpilot.starpilot.controls.lib.neural_network_feedforward import (
  DEFAULT_NNFF_LAT_JERK_FRICTION_FACTOR,
  PALISADE_NNFF_LAT_JERK_FRICTION_FACTOR,
  get_nnff_lat_jerk_friction_factor,
)


def test_palisade_nnff_jerk_friction_factor_is_damped_for_bumps():
  assert get_nnff_lat_jerk_friction_factor(HYUNDAI_CAR.HYUNDAI_PALISADE_2023) == PALISADE_NNFF_LAT_JERK_FRICTION_FACTOR
  assert PALISADE_NNFF_LAT_JERK_FRICTION_FACTOR < DEFAULT_NNFF_LAT_JERK_FRICTION_FACTOR


def test_other_nnff_cars_keep_default_jerk_friction_factor():
  assert get_nnff_lat_jerk_friction_factor(HYUNDAI_CAR.HYUNDAI_SONATA) == DEFAULT_NNFF_LAT_JERK_FRICTION_FACTOR
  assert get_nnff_lat_jerk_friction_factor(HYUNDAI_CAR.HYUNDAI_PALISADE) == DEFAULT_NNFF_LAT_JERK_FRICTION_FACTOR


# --- TOYOTA_COROLLA_RETROFIT live friction factors -------------------------------------------
import re
from types import SimpleNamespace

import pytest

from cereal import car, custom, log
from opendbc.car.car_helpers import interfaces
from opendbc.car.toyota.values import CAR as TOYOTA_CAR
from opendbc.car.vehicle_model import VehicleModel
from openpilot.common.basedir import BASEDIR
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.modeld.constants import ModelConstants
from openpilot.starpilot.controls.lib.neural_network_feedforward import (
  RETROFIT_NNFF_FRICTION_ACCEL_DEFAULT,
  RETROFIT_NNFF_FRICTION_JERK_DEFAULT,
  LatControlNNFF,
)

UPSTREAM_ACCEL_FACTOR = 0.7  # the value __init__ sets before the first look-ahead reset


class _RecordingModel:
  """Stand-in for the network: records every input vector, returns zero torque."""
  friction_override = False

  def __init__(self):
    self.calls = []

  def evaluate(self, inputs):
    self.calls.append(list(inputs))
    return 0.0


def _build(car_name):
  CarInterface = interfaces[car_name]
  CP = CarInterface.get_non_essential_params(car_name)
  CI = CarInterface(CP, custom.StarPilotCarParams.new_message())
  controller = LatControlNNFF(CP.as_reader(), CI, DT_CTRL)
  model = _RecordingModel()
  controller.lat_torque_nn_model = model
  controller.nnff_loaded = True
  controller.nn_friction_override = False

  CS = car.CarState.new_message()
  CS.vEgo = 20.0
  CS.steeringAngleDeg = 2.0
  params = log.LiveParametersData.new_message()
  params.steerRatio = CP.steerRatio
  params.stiffnessFactor = 1.0
  params.angleOffsetDeg = 0.0
  return controller, model, VehicleModel(CP), CS, params


def _plan(flip):
  """Planned lateral accel. flip=False: jerk keeps one sign (look-ahead jerk non-zero).
  flip=True: jerk alternates sign, so get_lookahead_value returns 0 — the branch that
  upstream uses to reset the accel factor to 1.0."""
  md = log.ModelDataV2.new_message()
  n = len(ModelConstants.T_IDXS)
  md.orientation.x = [0.0] * n
  md.orientation.y = [0.0] * n
  if flip:
    md.acceleration.y = [0.8 + (0.2 if i % 2 else -0.2) for i in range(n)]
  else:
    md.acceleration.y = [0.8 + 0.3 * t for t in ModelConstants.T_IDXS]
  return md


def _step(controller, model, VM, CS, params, toggles, flip=False):
  model.calls.clear()
  controller.update(True, CS, VM, params, False, 0.8 / CS.vEgo ** 2, False, 0.2, None, _plan(flip), toggles)
  setpoint_input, ff_input = model.calls[0], model.calls[-1]
  return {"friction_input": ff_input[2], "jerk_setpoint": setpoint_input[2]}


def _toggles(**factors):
  return SimpleNamespace(nnff=True, nnff_lite=False, **factors)


def _retrofit_step(accel=None, jerk=None, flip=False):
  factors = {}
  if accel is not None:
    factors["retrofit_nnff_friction_accel"] = accel
  if jerk is not None:
    factors["retrofit_nnff_friction_jerk"] = jerk
  controller, model, VM, CS, params = _build(TOYOTA_CAR.TOYOTA_COROLLA_RETROFIT)
  return _step(controller, model, VM, CS, params, _toggles(**factors), flip=flip)


def test_retrofit_accel_factor_scales_the_error_term():
  error = _retrofit_step(accel=1.0, jerk=0.0)["friction_input"]
  assert error != 0.0  # the scenario has tracking error, or this test proves nothing
  assert _retrofit_step(accel=2.0, jerk=0.0)["friction_input"] == pytest.approx(2.0 * error)
  assert _retrofit_step(accel=0.0, jerk=0.0)["friction_input"] == pytest.approx(0.0, abs=1e-9)


def test_retrofit_jerk_factor_scales_lookahead_in_feedforward_and_feedback():
  base = _retrofit_step(accel=0.0, jerk=0.4)
  doubled = _retrofit_step(accel=0.0, jerk=0.8)
  assert base["friction_input"] != 0.0
  assert doubled["friction_input"] == pytest.approx(2.0 * base["friction_input"])
  # the same factor also scales the jerk the network sees in the feedback (error) path
  assert doubled["jerk_setpoint"] == pytest.approx(2.0 * base["jerk_setpoint"])


def test_retrofit_defaults_reproduce_current_behaviour():
  # A missing toggle attribute (e.g. an old toggles blob) falls back to the defaults,
  # and the defaults are exactly what upstream runs after its first look-ahead reset.
  defaults = _retrofit_step()
  explicit = _retrofit_step(accel=RETROFIT_NNFF_FRICTION_ACCEL_DEFAULT, jerk=RETROFIT_NNFF_FRICTION_JERK_DEFAULT)
  assert defaults == pytest.approx(explicit)
  assert RETROFIT_NNFF_FRICTION_ACCEL_DEFAULT == 1.0


def test_retrofit_factor_survives_the_lookahead_reset_and_is_live():
  controller, model, VM, CS, params = _build(TOYOTA_CAR.TOYOTA_COROLLA_RETROFIT)
  toggles = _toggles(retrofit_nnff_friction_accel=0.5, retrofit_nnff_friction_jerk=0.0)

  # upstream would switch to 1.0 on this frame and stay there; the retrofit keeps 0.5
  _step(controller, model, VM, CS, params, toggles, flip=True)
  assert controller.lat_accel_friction_factor == pytest.approx(0.5)
  _step(controller, model, VM, CS, params, toggles, flip=False)
  assert controller.lat_accel_friction_factor == pytest.approx(0.5)

  # live: a changed param applies on the next frame, no controller rebuild
  toggles.retrofit_nnff_friction_accel = 1.5
  _step(controller, model, VM, CS, params, toggles)
  assert controller.lat_accel_friction_factor == pytest.approx(1.5)


def test_other_cars_ignore_the_retrofit_params_and_keep_upstream_behaviour():
  controller, model, VM, CS, params = _build(TOYOTA_CAR.TOYOTA_COROLLA)
  toggles = _toggles(retrofit_nnff_friction_accel=2.5, retrofit_nnff_friction_jerk=2.5)

  _step(controller, model, VM, CS, params, toggles, flip=False)
  assert controller.lat_accel_friction_factor == pytest.approx(UPSTREAM_ACCEL_FACTOR)
  assert controller.lat_jerk_friction_factor == pytest.approx(DEFAULT_NNFF_LAT_JERK_FRICTION_FACTOR)

  # upstream's sticky reset is preserved for everyone else
  _step(controller, model, VM, CS, params, toggles, flip=True)
  assert controller.lat_accel_friction_factor == pytest.approx(1.0)
  _step(controller, model, VM, CS, params, toggles, flip=False)
  assert controller.lat_accel_friction_factor == pytest.approx(1.0)


def test_retrofit_friction_defaults_agree_everywhere():
  # The defaults live in three places: the param table (UI slider start and fresh installs),
  # starpilot_variables (what reaches the controller) and the controller's own fallback.
  keys_src = open(f"{BASEDIR}/common/params_keys.h").read()
  table = dict(re.findall(r'\{"(RetrofitNNFF[A-Za-z]+)", \{PERSISTENT, FLOAT, "([^"]*)"', keys_src))
  variables_src = open(f"{BASEDIR}/starpilot/common/starpilot_variables.py").read()
  variables = dict(re.findall(r'get_value\("(RetrofitNNFF[A-Za-z]+)", cast=float, default=([0-9.]+)', variables_src))

  expected = {"RetrofitNNFFFrictionAccel": RETROFIT_NNFF_FRICTION_ACCEL_DEFAULT,
              "RetrofitNNFFFrictionJerk": RETROFIT_NNFF_FRICTION_JERK_DEFAULT}
  assert set(table) == set(expected) == set(variables)
  for key, value in expected.items():
    assert float(table[key]) == pytest.approx(value), key
    assert float(variables[key]) == pytest.approx(value), key

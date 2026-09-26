"""Versioned TOYOTA_COROLLA_RETROFIT NNFF models (starpilot/assets/nnff_models/retrofit/).

The file checks run over every model in the folder, so a newly added version is checked
before it is driven. They exist because the trainer's own self-test passed on a model whose
torque sign was inverted.
"""
import re
from pathlib import Path

import pytest

from opendbc.car.toyota.values import CAR as TOYOTA_CAR
from openpilot.common.params import Params
from openpilot.starpilot.common import starpilot_variables as sv
from openpilot.starpilot.controls.lib import neural_network_feedforward as nnff
from openpilot.starpilot.controls.lib.neural_network_feedforward import FluxModel

RETROFIT = TOYOTA_CAR.TOYOTA_COROLLA_RETROFIT
MODEL_FILES = sorted(sv.RETROFIT_NNFF_MODELS_PATH.glob("*.json"))
STOCK_COROLLA = sv.NNFF_MODELS_PATH / "TOYOTA_COROLLA.json"


def _input_vars(path):
  import json
  with open(path) as f:
    return json.load(f).get("input_vars")


def _normalize(name):
  # nnlc-tools names these "actual_lateral_accel_tm03"; the shipped models use "lateral_accel_m03"
  name = name.removeprefix("actual_")
  return re.sub(r"_t([mp])(\d+)$", r"_\1\2", name)


def _torque(model, v_ego, lat_accel):
  # Steady turn: the 7 lat-accel history/future inputs hold the same value, rolls are 0. Zeroing
  # the history instead is off-distribution; the retrofit model takes most of its response from
  # those inputs, so a lone current value at 30 m/s is swamped by its learned straight-line offset.
  return model.evaluate([v_ego, lat_accel, 0.0, 0.0] + [lat_accel] * 7 + [0.0] * 7)


def test_folder_has_a_model():
  assert MODEL_FILES, f"no models in {sv.RETROFIT_NNFF_MODELS_PATH}"


def test_files_follow_naming_with_unique_versions():
  versions = []
  for file in sv.RETROFIT_NNFF_MODELS_PATH.iterdir():
    if file.name == "README.md":
      continue
    assert file.suffix == ".json", f"unexpected file {file.name}"
    match = sv.RETROFIT_NNFF_MODEL_PATTERN.match(file.stem)
    assert match, f"{file.name} must be named v<N>_<YYYY-MM-DD>[_label].json"
    versions.append(int(match.group(1)))
  assert len(versions) == len(set(versions)), f"duplicate version numbers: {sorted(versions)}"


@pytest.mark.parametrize("path", MODEL_FILES, ids=lambda p: p.stem)
def test_model_is_listed_in_readme(path):
  readme = (sv.RETROFIT_NNFF_MODELS_PATH / "README.md").read_text()
  assert f"| {path.stem} |" in readme, f"add a row for {path.stem} to README.md"


@pytest.mark.parametrize("path", MODEL_FILES, ids=lambda p: p.stem)
def test_model_inputs_match_runtime_order(path):
  # FluxModel.evaluate is positional, so the names must line up with what LatControlNNFF builds,
  # which is the order the shipped models were trained on.
  model = FluxModel(str(path))
  assert model.input_size == 18
  assert [_normalize(v) for v in _input_vars(path)] == _input_vars(STOCK_COROLLA)


@pytest.mark.parametrize("path", MODEL_FILES, ids=lambda p: p.stem)
def test_model_torque_sign_matches_stock_corolla(path):
  stock = FluxModel(str(STOCK_COROLLA))
  model = FluxModel(str(path))
  for v_ego in (5.0, 20.0, 30.0):
    assert _torque(stock, v_ego, 1.0) > 0 > _torque(stock, v_ego, -1.0)
    assert _torque(model, v_ego, 1.0) > 0 > _torque(model, v_ego, -1.0), f"{path.stem} steers the wrong way at {v_ego} m/s"


def test_stock_loader_never_sees_versioned_models():
  retrofit_names = {p.stem for p in MODEL_FILES}
  assert not retrofit_names & set(sv.get_nnff_model_files())
  path = nnff.get_nn_model_path(RETROFIT, "")
  assert path is None or Path(path).parent != sv.RETROFIT_NNFF_MODELS_PATH


def test_nnff_supported_for_retrofit():
  assert sv.nnff_supported(RETROFIT)


@pytest.fixture
def model_dir(tmp_path, monkeypatch):
  for name in ("v1_2026-01-01", "v2_2026-02-01_label", "v10_2026-03-01", "notes", "v3_bad-date"):
    (tmp_path / f"{name}.json").write_text("{}")
  (tmp_path / "README.md").write_text("")
  monkeypatch.setattr(sv, "RETROFIT_NNFF_MODELS_PATH", tmp_path)
  return tmp_path


def test_models_sort_newest_version_first(model_dir):
  # numeric, so v10 is newer than v2
  assert sv.get_retrofit_nnff_models() == ["v10_2026-03-01", "v2_2026-02-01_label", "v1_2026-01-01"]


@pytest.mark.parametrize("selection, expected", [
  ("", "v10_2026-03-01"),
  (None, "v10_2026-03-01"),
  ("v2_2026-02-01_label", "v2_2026-02-01_label"),
  ("v1_2026-01-01", "v1_2026-01-01"),
  ("v7_2026-01-01", "v10_2026-03-01"),  # pinned but deleted -> newest
])
def test_resolution(model_dir, selection, expected):
  assert sv.resolve_retrofit_nnff_model(selection) == expected


def test_resolution_without_models(tmp_path, monkeypatch):
  monkeypatch.setattr(sv, "RETROFIT_NNFF_MODELS_PATH", tmp_path / "missing")
  assert sv.get_retrofit_nnff_models() == []
  assert sv.resolve_retrofit_nnff_model("") is None
  assert not sv.nnff_supported(RETROFIT)


def test_get_nn_model_loads_newest_by_default():
  params = Params()
  params.remove("RetrofitNNFFModel")
  newest = sv.get_retrofit_nnff_models()[0]
  model = nnff.get_nn_model(RETROFIT, "")
  assert isinstance(model, FluxModel)
  assert params.get("NNFFModelName", encoding="utf-8") == f"Corolla Retrofit {newest}"


@pytest.mark.parametrize("selection", ["pinned", "v999_2099-01-01"])
def test_get_nn_model_honours_pin_and_falls_back(selection):
  params = Params()
  oldest = sv.get_retrofit_nnff_models()[-1]
  newest = sv.get_retrofit_nnff_models()[0]
  params.put("RetrofitNNFFModel", oldest if selection == "pinned" else selection)
  nnff.get_nn_model(RETROFIT, "")
  expected = oldest if selection == "pinned" else newest
  assert params.get("NNFFModelName", encoding="utf-8") == f"Corolla Retrofit {expected}"


def test_other_cars_do_not_read_retrofit_selection():
  params = Params()
  params.put("RetrofitNNFFModel", sv.get_retrofit_nnff_models()[0])
  nnff.get_nn_model(TOYOTA_CAR.TOYOTA_COROLLA, "")
  assert params.get("NNFFModelName", encoding="utf-8") == "TOYOTA COROLLA"

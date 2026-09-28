import json
import re

import pytest

from test_navigation_params import _params_client, the_galaxy
from test_device_settings_layout import LAYOUT_PATH, PARAM_KEYS_PATH


EXPECTED_KEY_TYPE = {"numeric": "FLOAT", "toggle": "BOOL", "dropdown": "STRING"}


def _retrofit_section():
  layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
  sections = [section for section in layout if section["name"] == "Retrofit"]
  assert len(sections) == 1
  return layout, sections[0]


def test_retrofit_section_is_gated_to_the_retrofit_platform():
  layout, section = _retrofit_section()
  params_source = PARAM_KEYS_PATH.read_text(encoding="utf-8")
  retrofit_keys = {param["key"] for param in section["params"]}

  assert "RetrofitPauseSteering" not in retrofit_keys
  for param in section["params"]:
    assert param["requires_capability"] == "IsRetrofit", param["key"]
    assert param["settings_tier"] == "simple", param["key"]
    declared = re.search(rf'\{{"{param["key"]}",\s*\{{[^,]+,\s*(\w+)', params_source)
    assert declared is not None, f"{param['key']} is not in params_keys.h"
    assert declared.group(1) == EXPECTED_KEY_TYPE[param["ui_type"]], param["key"]

  for other in layout:
    if other is not section:
      assert not retrofit_keys & {param["key"] for param in other["params"]}, other["name"]


@pytest.mark.parametrize("fingerprint,expected", [("TOYOTA_COROLLA_RETROFIT", True), ("TOYOTA_COROLLA", False), (None, False)])
def test_params_all_reports_retrofit_capability(monkeypatch, fingerprint, expected):
  client, _ = _params_client(monkeypatch, {}, "tici")
  if fingerprint is None:
    monkeypatch.delenv("FINGERPRINT", raising=False)
  else:
    monkeypatch.setenv("FINGERPRINT", fingerprint)
  monkeypatch.setattr(the_galaxy, "_safe_params_get_live_raw", lambda key: None)

  response = client.get("/api/params/all")

  assert response.status_code == 200
  assert response.get_json()["IsRetrofit"] is expected


@pytest.mark.parametrize("models,selection,expected", [
  (["v2_2026-10-01", "v1_2026-09-23"], "", [
    {"value": "", "label": "Newest (v2_2026-10-01)"},
    {"value": "v2_2026-10-01", "label": "v2_2026-10-01"},
    {"value": "v1_2026-09-23", "label": "v1_2026-09-23"},
  ]),
  (["v1_2026-09-23"], "v0_gone", [
    {"value": "", "label": "Newest (v1_2026-09-23)"},
    {"value": "v0_gone", "label": "v0_gone (missing, using v1_2026-09-23)"},
    {"value": "v1_2026-09-23", "label": "v1_2026-09-23"},
  ]),
  ([], "", [{"value": "", "label": "None installed"}]),
])
def test_nnff_model_options(monkeypatch, models, selection, expected):
  client, _ = _params_client(monkeypatch, {"RetrofitNNFFModel": selection}, "tici")
  monkeypatch.setattr(the_galaxy, "_get_retrofit_nnff_models", lambda: models)

  response = client.get("/api/retrofit/nnff_models")

  assert response.status_code == 200
  assert response.get_json() == expected


def test_nnff_model_options_endpoint_always_returns_a_list(monkeypatch):
  client, _ = _params_client(monkeypatch, {}, "tici")
  def unavailable():
    raise OSError("models folder unreadable")
  monkeypatch.setattr(the_galaxy, "_get_retrofit_nnff_models", unavailable)

  response = client.get("/api/retrofit/nnff_models")

  assert response.status_code == 200
  assert response.get_json() == []


def test_negative_float_default_is_typed_by_the_layout(monkeypatch):
  # "-0.1" doesn't parse as a float in the default-string guess, so without the layout
  # override the pedal offset would be served and edited as a string.
  monkeypatch.setattr(the_galaxy, "starpilot_default_params", [("RetrofitPedalOffsetStandstill", "-0.1", None, 2)])
  monkeypatch.setattr(the_galaxy, "_cached_allowed_keys", None)
  monkeypatch.setattr(the_galaxy, "_cached_param_types", None)

  _, types = the_galaxy._get_param_type_info()

  assert types["RetrofitPedalOffsetStandstill"] is float

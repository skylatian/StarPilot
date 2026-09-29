from cereal import custom
from openpilot.selfdrive.ui.layouts.settings.starpilot.retrofit import ECU_OFFROAD_NOTE, ecu_status_text


def _diag(**fields):
  diag = custom.StarPilotCarState.new_message().init("retrofitDiag")
  for path, value in fields.items():
    obj = diag
    *parents, name = path.split("__")
    for p in parents:
      obj = getattr(obj, p)
    setattr(obj, name, value)
  return diag


def test_offroad_never_shows_status():
  diag = _diag(stalkFrameAge=0.0, stalk__seen=True, stalk__firmwareVersion="092726a")
  for key in ("emulator", "stalk", "vss", "eps", "sas"):
    assert ecu_status_text(key, diag, started=False) == ECU_OFFROAD_NOTE
    assert ecu_status_text(key, None, started=False) == ECU_OFFROAD_NOTE


def test_onroad_statuses():
  diag = _diag(stalkFrameAge=0.05, stalk__seen=True, stalk__firmwareVersion="092726a", stalk__restarts=2,
               vssFrameAge=3.0, emulatorFrameAge=0.02, epsFrameAge=0.01, epsLkaState=1, sasFrameAge=0.02)
  assert ecu_status_text("stalk", diag, True) == "Connected · 092726a · 2 restarts"
  assert ecu_status_text("vss", diag, True) == "Missing"
  assert ecu_status_text("emulator", diag, True) == "Connected · no status frame (old firmware)"
  assert ecu_status_text("eps", diag, True) == "Connected · LKA state 1"
  assert ecu_status_text("sas", diag, True) == "Connected"
  assert ecu_status_text("stalk", None, True) == "No data"


def test_live_path_reads_published_message(monkeypatch):
  # Exercise the real SubMaster-style reader path (the onroad crash was here: readers have
  # _has(), not has()).
  from types import SimpleNamespace
  from cereal import messaging
  from openpilot.selfdrive.ui.layouts.settings.starpilot import retrofit
  import openpilot.selfdrive.ui.ui_state as ui_state_mod

  msg = messaging.new_message("starpilotCarState")
  diag = msg.starpilotCarState.init("retrofitDiag")
  diag.stalkFrameAge = 0.05
  diag.stalk.seen = True
  diag.stalk.firmwareVersion = "092726a"
  reader = msg.as_reader().starpilotCarState

  fake = SimpleNamespace(started=True, sm={"starpilotCarState": reader})
  fake.sm = type("SM", (dict,), {"valid": {"starpilotCarState": True}})(fake.sm)
  monkeypatch.setattr(ui_state_mod, "ui_state", fake)
  assert retrofit.live_ecu_status("stalk") == "Connected · 092726a"

  # Message without retrofitDiag set (another car / old card): no crash
  empty = messaging.new_message("starpilotCarState").as_reader().starpilotCarState
  fake.sm = type("SM", (dict,), {"valid": {"starpilotCarState": True}})({"starpilotCarState": empty})
  assert retrofit.live_ecu_status("stalk") == "No data"

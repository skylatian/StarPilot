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

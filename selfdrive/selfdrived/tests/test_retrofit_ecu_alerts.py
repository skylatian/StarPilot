from types import SimpleNamespace

from cereal import custom
from openpilot.selfdrive.selfdrived.events import ET, Events, STARPILOT_EVENTS
from openpilot.selfdrive.selfdrived.selfdrived import add_retrofit_starpilot_events

StarPilotEventName = custom.StarPilotOnroadEvent.EventName

RETROFIT_CP = SimpleNamespace(carFingerprint="TOYOTA_COROLLA_RETROFIT")


def _fpcs(stalk_age=0.05, **ecu_fields):
  msg = custom.StarPilotCarState.new_message()
  diag = msg.init("retrofitDiag")
  diag.stalkFrameAge = stalk_age
  for path, value in ecu_fields.items():
    ecu, field = path.split("__")
    setattr(getattr(diag, ecu), field, value)
  return msg


def _events(fpcs, prev=(0, 0), cp=RETROFIT_CP):
  events = Events(starpilot=True)
  counts = add_retrofit_starpilot_events(cp, fpcs, events, prev)
  return events.names, counts


def _alert(event, fpcs):
  callback = STARPILOT_EVENTS[event][ET.PERMANENT]
  sm = {"starpilotCarState": fpcs}
  return callback(None, None, sm, False, 0, None, None)


def test_stalk_unresponsive_after_timeout():
  names, _ = _events(_fpcs(stalk_age=0.3))
  assert StarPilotEventName.retrofitStalkUnresponsive not in names
  names, _ = _events(_fpcs(stalk_age=1.5))
  assert StarPilotEventName.retrofitStalkUnresponsive in names


def test_restart_and_recovery_fire_once_per_new_count():
  fpcs = _fpcs(stalk__restarts=1, vss__recoveryEvents=2)
  names, counts = _events(fpcs)
  assert StarPilotEventName.retrofitEcuRestarted in names
  assert StarPilotEventName.retrofitEcuCanRecovered in names
  assert counts == (1, 2)

  names, counts = _events(fpcs, prev=counts)
  assert StarPilotEventName.retrofitEcuRestarted not in names
  assert StarPilotEventName.retrofitEcuCanRecovered not in names
  assert counts == (1, 2)


def test_other_cars_untouched():
  names, counts = _events(_fpcs(stalk_age=5.0, stalk__restarts=3), cp=SimpleNamespace(carFingerprint="TOYOTA_COROLLA"))
  assert names == []
  assert counts == (0, 0)


def test_restart_alert_names_watchdog_phase():
  fpcs = _fpcs(stalk__resetKind=4, stalk__resetPhase=5)
  fpcs.retrofitDiag.lastRestartEcu = "stalk"
  alert = _alert(StarPilotEventName.retrofitEcuRestarted, fpcs)
  assert alert.alert_text_1 == "Cruise Stalk ECU Restarted"
  assert alert.alert_text_2 == "Watchdog: hung in CAN send, cruise off"


def test_restart_alert_unknown_cause_for_vss():
  fpcs = _fpcs(vss__resetKind=0)
  fpcs.retrofitDiag.lastRestartEcu = "vss"
  alert = _alert(StarPilotEventName.retrofitEcuRestarted, fpcs)
  assert alert.alert_text_1 == "VSS Speed ECU Restarted"
  assert alert.alert_text_2 == "Power loss or brown-out"


def test_recovery_alert_reason():
  fpcs = _fpcs(stalk__recoveryReason=2)
  fpcs.retrofitDiag.lastRecoveryEcu = "stalk"
  alert = _alert(StarPilotEventName.retrofitEcuCanRecovered, fpcs)
  assert alert.alert_text_1 == "Cruise Stalk CAN Controller Reset"
  assert alert.alert_text_2 == "Controller left normal mode, cruise off"

  fpcs.retrofitDiag.lastRecoveryEcu = "emulator"
  alert = _alert(StarPilotEventName.retrofitEcuCanRecovered, fpcs)
  assert alert.alert_text_1 == "Main Emulator CAN Controller Reset"
  assert alert.alert_text_2 == ""

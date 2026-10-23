"""Read-only TOYOTA_COROLLA_RETROFIT onroad check: samples live messages for DURATION seconds (default 20).

On the C3: cd /data/openpilot && PYTHONPATH=. /usr/local/venv/bin/python3 scripts/retrofit/c3_onroad_check.py
"""
import os
import time
from collections import Counter
from openpilot.cereal import messaging

DURATION = float(os.environ.get("DURATION", "20"))
services = ["carState", "starpilotCarState", "pandaStates", "onroadEvents", "selfdriveState", "deviceState"]
sm = messaging.SubMaster(services, poll="carState")

n = valid = timeout = 0
faults = Counter()
angle_min, angle_max = 1e9, -1e9
vego_max = 0.0
events = Counter()
panda = []
diag = None
end = time.monotonic() + DURATION
while time.monotonic() < end:
  sm.update(100)
  if sm.updated["carState"]:
    cs = sm["carState"]
    n += 1
    valid += cs.canValid
    timeout += cs.canTimeout
    for f in ("steerFaultTemporary", "steerFaultPermanent", "accFaulted", "espDisabled", "brakePressed", "steeringPressed"):
      if getattr(cs, f):
        faults[f] += 1
    angle_min = min(angle_min, cs.steeringAngleDeg)
    angle_max = max(angle_max, cs.steeringAngleDeg)
    vego_max = max(vego_max, cs.vEgo)
  if sm.updated["onroadEvents"]:
    for e in sm["onroadEvents"]:
      events[str(e.name)] += 1
  if sm.updated["starpilotCarState"] and sm["starpilotCarState"]._has("retrofitDiag"):
    diag = sm["starpilotCarState"].retrofitDiag
  if sm.updated["pandaStates"]:
    panda = list(sm["pandaStates"])

print(f"deviceState.started={sm['deviceState'].started} seen={sm.seen}")
print(f"carState samples={n} canValid={valid} canTimeout={timeout} faults={dict(faults)}")
if n:
  cs = sm["carState"]
  print(f"steeringAngleDeg min={angle_min:.1f} max={angle_max:.1f} last={cs.steeringAngleDeg:.1f} vEgo max={vego_max:.2f}")
  print(f"cruise enabled={cs.cruiseState.enabled} available={cs.cruiseState.available} gear={cs.gearShifter}")
sd = sm["selfdriveState"]
print(f"selfdriveState: {sd.state} alert: {sd.alertText1!r} {sd.alertText2!r}")
print("onroadEvents:", dict(events))
for p in panda:
  print(f"panda: type={p.pandaType} safety={p.safetyModel} param={p.safetyParam:#x} ignLine={p.ignitionLine} ignCan={p.ignitionCan} " +
        f"allowed={p.controlsAllowed} rxInvalid={p.safetyRxInvalid} txBlocked={p.safetyTxBlocked} " +
        f"rxChecksInvalid={p.safetyRxChecksInvalid} faults={[str(f) for f in p.faults]}")
if diag is None:
  print("retrofitDiag: none")
else:
  for ecu in ("emulator", "stalk", "vss"):
    d = getattr(diag, ecu)
    print(f"retrofitDiag.{ecu}: seen={d.seen} age={d.age:.2f} fw={d.firmwareVersion!r} build={d.buildTime!r} boot={d.bootCount} " +
          f"restarts={d.restarts} recoveries={d.recoveryEvents} eflg={d.canErrorFlags:#x} txFails={d.txFails}")
  print(f"retrofitDiag: stalkAge={diag.stalkFrameAge:.2f} epsAge={diag.epsFrameAge:.2f} sasAge={diag.sasFrameAge:.2f} " +
        f"emuAge={diag.emulatorFrameAge:.2f} vssAge={diag.vssFrameAge:.2f} lka={diag.epsLkaState} " +
        f"cruise={diag.emulatorCruiseState} stalkMain={diag.stalkMainOn} stalkC3={diag.stalkC3Present}")

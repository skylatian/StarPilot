"""Read-only TOYOTA_COROLLA_RETROFIT check of the C3's params and CarParams.

On the C3: cd /data/openpilot && source launch_env.sh && PYTHONPATH=. /usr/local/venv/bin/python3 scripts/retrofit/c3_params_check.py
"""
import os
from openpilot.common.params import Params
from opendbc.car.structs import car

p = Params()
print("env FINGERPRINT:", os.environ.get("FINGERPRINT"), "SKIP_FW_QUERY:", os.environ.get("SKIP_FW_QUERY"))
for k in ("RetrofitSASOffset", "RetrofitSteerAngleDeadzone", "RetrofitSteerKD"):
  try:
    print(f"{k}: type={p.get_type(k)} value={p.get(k)!r}")
  except Exception as e:
    print(f"{k}: NOT IN COMPILED TABLE ({type(e).__name__}: {e})")
for k in ("AlphaLongitudinalEnabled", "LaneCentering", "ForceAutoTuneOff", "OpenpilotEnabledToggle", "IsOffroad"):
  try:
    print(f"{k}: {p.get_bool(k)}")
  except Exception as e:
    print(f"{k}: {type(e).__name__}: {e}")

raw = p.get("CarParams")
if not raw:
  print("CarParams: not written yet (card has not started)")
else:
  with car.CarParams.from_bytes(raw) as cp:
    sc = cp.safetyConfigs[-1] if len(cp.safetyConfigs) else None
    print("carFingerprint:", cp.carFingerprint, "| fingerprintSource:", cp.fingerprintSource)
    print("openpilotLongitudinalControl:", cp.openpilotLongitudinalControl, "| alphaLongitudinalAvailable:", cp.alphaLongitudinalAvailable)
    print("radarUnavailable:", cp.radarUnavailable, "| steerAtStandstill:", cp.steerAtStandstill, "| minEnableSpeed:", cp.minEnableSpeed)
    print("dashcamOnly:", cp.dashcamOnly, "| passive:", cp.passive)
    if cp.lateralTuning.which() == "torque":
      t = cp.lateralTuning.torque
      print("torque: latAccelFactor", t.latAccelFactor, "friction", t.friction, "steeringAngleDeadzoneDeg", t.steeringAngleDeadzoneDeg)
    if sc is not None:
      print("safetyModel:", sc.safetyModel, "| safetyParam:", sc.safetyParam, hex(sc.safetyParam),
            "| fork bits 0x2000/0x4000 set:", bool(sc.safetyParam & 0x6000))

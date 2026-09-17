#!/usr/bin/env python3
"""Seed desktop params so the host UIs behave like the retrofit car (no C3 needed)."""
import argparse
import os

DEFAULT_FINGERPRINT = "TOYOTA_COROLLA_RETROFIT"


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--fingerprint", default=DEFAULT_FINGERPRINT)
  parser.add_argument("--params-root", help="params root to seed (default: ~/.comma/params)")
  parser.add_argument("--alpha-long", action=argparse.BooleanOptionalAction, default=True)
  parser.add_argument("--calibration", action=argparse.BooleanOptionalAction, default=True)
  args = parser.parse_args()

  # must precede the openpilot imports: Path::params() reads PARAMS_ROOT
  if args.params_root:
    os.environ["PARAMS_ROOT"] = args.params_root

  from cereal import log
  from opendbc.car import gen_empty_fingerprint
  from opendbc.car.car_helpers import interfaces
  from openpilot.common.params import Params
  from openpilot.starpilot.common.starpilot_variables import get_starpilot_toggles
  from openpilot.system.hardware.hw import Paths

  candidate = args.fingerprint
  if candidate not in interfaces:
    raise SystemExit(f"unknown platform: {candidate}")

  toggles = get_starpilot_toggles(read_persisted_force_params=True)
  CI = interfaces[candidate]
  CP = CI.get_params(candidate, gen_empty_fingerprint(), [], args.alpha_long, False, docs=False, starpilot_toggles=toggles)
  FPCP = CI.get_starpilot_params(candidate, gen_empty_fingerprint(), [], CP, toggles)

  params = Params()

  cp_bytes = CP.to_bytes()
  for key in ("CarParams", "CarParamsCache", "CarParamsPersistent"):
    params.put(key, cp_bytes)

  fpcp_bytes = FPCP.to_bytes()
  for key in ("StarPilotCarParams", "StarPilotCarParamsPersistent"):
    params.put(key, fpcp_bytes)

  params.put("CarMake", candidate.split("_")[0].title())
  params.put("CarModel", candidate)
  params.put_bool("OpenpilotEnabledToggle", True)
  params.put_bool("AlphaLongitudinalEnabled", args.alpha_long)
  params.put_bool("ExperimentalLongitudinalEnabled", args.alpha_long)

  if args.calibration:
    msg = log.Event.new_message()
    msg.init("liveCalibration")
    cal = msg.liveCalibration
    cal.validBlocks = 5
    cal.calStatus = log.LiveCalibrationData.Status.calibrated
    cal.calPerc = 100
    cal.rpyCalib = [0.0, 0.0, 0.0]
    cal.rpyCalibSpread = [0.0, 0.0, 0.0]
    cal.wideFromDeviceEuler = [0.0, 0.0, 0.0]
    cal.height = [1.22]
    params.put("CalibrationParams", msg.to_bytes())

  root = os.environ.get("PARAMS_ROOT") or os.path.join(Paths.comma_home(), "params")
  print(f"seeded {candidate} into {root}")
  print(f"  brand={CP.brand} alphaLongAvailable={CP.alphaLongitudinalAvailable} "
        f"opLong={CP.openpilotLongitudinalControl} radarUnavailable={CP.radarUnavailable}")
  print(f"  calibration={'seeded' if args.calibration else 'skipped'}")
  print(f"\nLaunch with the env gate too:\n  FINGERPRINT={candidate} ./c3")


if __name__ == "__main__":
  main()

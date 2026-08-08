#!/usr/bin/env python3
"""Reset all retrofit tune params to pass-through baseline values.

Run on C3 via SSH: python3 /data/openpilot/scripts/set_baseline_tune.py

At baseline, the controller behaves like stock — all custom FF windowing,
friction shaping, center taper, and nonlinear sigmoid are disabled.
The tuning infrastructure remains intact; any non-zero value is an
intentional, data-driven choice.

KP curve and nonlinear changes require an offroad cycle after reset.
Other tune params take effect live.
"""

import sys

sys.path.insert(0, "/data/openpilot")
from openpilot.common.params import Params

BASELINE = {
    "RetrofitTuneFFGain": 0.0,
    "RetrofitTuneFFOnset": 0.18,
    "RetrofitTuneFFOnsetWidth": 0.08,
    "RetrofitTuneFFCutoff": 1.10,
    "RetrofitTuneFFCutoffWidth": 0.30,
    "RetrofitTuneTransitionSpeed": 10.0,
    "RetrofitTunePhaseScale": 0.10,
    "RetrofitTuneFrictionLatRise": 0.20,
    "RetrofitTuneFrictionJerkRise": 0.24,
    "RetrofitTuneTurnInBoost": 0.0,
    "RetrofitTuneUnwindBoost": 0.0,
    "RetrofitTuneUnwindTaper": 0.0,
    "RetrofitTuneTurnInThresholdReduction": 0.0,
    "RetrofitTuneUnwindThresholdIncrease": 0.0,
    "RetrofitTuneTurnInFrictionBoost": 0.0,
    "RetrofitTuneUnwindFrictionReduction": 0.0,
    "RetrofitTuneCenterTaperMax": 0.0,
    "RetrofitTuneCenterTaperLat": 0.14,
    "RetrofitTuneCenterTaperLatWidth": 0.04,
    "RetrofitTuneCenterTaperSpeed": 14.0,
    "RetrofitTuneCenterTaperSpeedWidth": 2.5,
    "RetrofitTuneKP1": 250.0,
    "RetrofitTuneKP1_5": 120.0,
    "RetrofitTuneKP2": 65.0,
    "RetrofitTuneKP3": 30.0,
    "RetrofitTuneKP5": 11.5,
    "RetrofitTuneKP7_5": 5.5,
    "RetrofitTuneKP10": 3.5,
    "RetrofitTuneKP15": 2.0,
    "RetrofitTuneKP30": 0.6,
    "RetrofitNonlinearStrength": 0.0,
    "RetrofitNonlinearSaturation": 2.5,
    "RetrofitNonlinearBias": 0.0,
}


def main():
    p = Params()
    print("=== Retrofit Baseline Tune Reset ===\n")

    changed = []
    unchanged = []
    for key, target in BASELINE.items():
        raw = p.get(key)
        if raw is not None:
            try:
                current = float(raw)
            except (ValueError, TypeError):
                current = None
        else:
            current = None

        if current is not None and abs(current - target) < 1e-6:
            unchanged.append(key)
            print(f"  {key}: {current} (already baseline)")
        else:
            current_str = str(current) if current is not None else "(unset)"
            changed.append(key)
            print(f"  {key}: {current_str} -> {target}")

    print(f"\n{len(changed)} params to change, {len(unchanged)} already at baseline.")

    if not changed:
        print("Nothing to do.")
        return

    resp = input("\nApply baseline values? [y/N] ").strip().lower()
    if resp != "y":
        print("Aborted.")
        return

    for key, target in BASELINE.items():
        p.put_float(key, target)

    print(f"\nDone. {len(changed)} params updated.")
    print("\nReminder: KP curve and nonlinear changes require an offroad cycle.")
    print("Other tune params take effect live.")


if __name__ == "__main__":
    main()

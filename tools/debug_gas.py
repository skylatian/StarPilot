#!/usr/bin/env python3
"""Debug gas interceptor command pipeline.

Shows the full chain: planner → longcontrol → carcontroller → CAN gas command.
Run on C3: cd /data/openpilot && python3 starpilot/tools/debug_gas.py
"""
import cereal.messaging as messaging
import numpy as np
import time

from openpilot.common.params import Params

MIN_ACC_SPEED = 8.50   # 19 mph in m/s
PEDAL_TRANSITION = 4.47  # 10 mph in m/s

sm = messaging.SubMaster(['carControl', 'carState', 'carOutput', 'longitudinalPlan', 'controlsState'])
params = Params()

MS_TO_MPH = 2.23694

print(f"{'longState':>10s} {'planner':>8s} {'cmdAccel':>8s} {'pidOut':>8s} "
      f"{'gasCAN':>6s} {'gasOld':>6s} {'offset':>7s} {'setMph':>6s} {'mph':>6s} {'cruiseOn':>8s} {'cruiseEn':>8s}")
print("-" * 100)

while True:
    sm.update(1000)
    cc = sm['carControl']
    cs = sm['carState']
    co = sm['carOutput']
    lp = sm['longitudinalPlan']
    ctrl = sm['controlsState']

    pid_accel = co.actuatorsOutput.accel
    cmd_accel = cc.actuators.accel
    v_ego = cs.vEgo
    set_spd = cs.cruiseState.speed
    cruise_available = cs.cruiseState.available  # MAIN ON
    cruise_enabled = cs.cruiseState.enabled      # ENGAGED

    # Compute gas the way carcontroller now does it (using cmd_accel)
    pedal_scale = float(np.interp(v_ego, [0.0, MIN_ACC_SPEED, MIN_ACC_SPEED + PEDAL_TRANSITION], [0.3, 0.4, 0.4]))
    offset_low = params.get_float("RetrofitPedalOffsetStandstill", default=-0.1)
    pedal_offset = float(np.interp(v_ego, [0.0, 2.3, MIN_ACC_SPEED + PEDAL_TRANSITION], [offset_low, 0.0, 0.2]))

    # "Real" gas: what the code sends now (current-frame cmd_accel, with no-target guard)
    if set_spd < 0.1 or not cruise_enabled:
        gas_real = 0.0
    else:
        gas_real = float(np.clip(pedal_scale * (cmd_accel + pedal_offset), 0.0, 0.5))

    # "Old" gas: what would have been sent with pid_out (for comparison)
    gas_old = float(np.clip(pedal_scale * (pid_accel + pedal_offset), 0.0, 0.5))

    gas_real_can = round(gas_real * 255)
    gas_old_can = round(gas_old * 255)

    long_state = str(cc.actuators.longControlState)

    print(f"{long_state:>10s} {lp.aTarget:>+8.3f} {cmd_accel:>+8.3f} {pid_accel:>+8.3f} "
          f"{gas_real_can:>6d} {gas_old_can:>6d} {pedal_offset:>+7.3f} {set_spd * MS_TO_MPH:>6.1f} {v_ego * MS_TO_MPH:>6.1f} "
          f"{'YES' if cruise_available else 'no':>8s} {'YES' if cruise_enabled else 'no':>8s}")
    time.sleep(0.5)

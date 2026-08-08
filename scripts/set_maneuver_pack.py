#!/usr/bin/env python3
"""Set the lateral maneuver pack. Usage: python3 scripts/set_maneuver_pack.py A"""
import sys
from openpilot.common.params import Params

VALID = ["A", "B", "C", "D", "E", "stock", "all"]

if len(sys.argv) != 2 or sys.argv[1] not in VALID:
  print(f"Usage: {sys.argv[0]} <{'|'.join(VALID)}>")
  sys.exit(1)

pack = sys.argv[1]
Params().put("LateralManeuverPack", pack)
print(f"Lateral maneuver pack set to: {pack}")

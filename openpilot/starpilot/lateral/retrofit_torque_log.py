"""TOYOTA_COROLLA_RETROFIT: log the torque values the lateral controller applies.

Scoped to the retrofit and kept in this one file, so it can be dropped if upstream
starts logging the applied values itself.
"""

import math

from opendbc.car.toyota.retrofit import is_retrofit
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque


def supported(CP, LaC) -> bool:
  return is_retrofit(CP) and isinstance(LaC, LatControlTorque)


def write(state, LaC, torque_host) -> None:
  """Fill starpilotLateralState.retrofitAppliedTorque from the controller's own values."""
  applied = state.retrofitAppliedTorque
  params = LaC.torque_params
  applied.latAccelFactor = float(params.latAccelFactor)
  applied.latAccelOffset = float(params.latAccelOffset)
  applied.friction = float(params.friction)
  if torque_host is None:
    applied.source = 'native'
    applied.userFactor = applied.userFriction = math.nan
    return
  applied.source = str(torque_host.last_application.source)
  settings = torque_host.settings
  applied.userFactor = math.nan if settings.user_factor is None else float(settings.user_factor)
  applied.userFriction = math.nan if settings.user_friction is None else float(settings.user_friction)

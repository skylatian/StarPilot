"""TOYOTA_COROLLA_RETROFIT: log why Always On Lateral steering dropped.

Reuses the bounded withdrawal diagnostic that controlsd runs for GM (aol/transition_diagnostic.py):
one aol_lateral_withdrawal swaglog event per drop, 64 per drive. This car never steers at standstill,
so every stop ends lateral; those drops are expected and are not recorded, or ordinary stops would
use up the 64. Kept in this one file so it can be dropped if upstream changes the diagnostic.
"""

from opendbc.car.toyota.retrofit import configured
from openpilot.starpilot.aol.transition_diagnostic import TransitionDiagnostic


class RetrofitTransitionDiagnostic(TransitionDiagnostic):
  def finish(self, entry, gate, *, standstill=False, steer_at_standstill=False, **kwargs):
    if standstill and not steer_at_standstill:
      return
    super().finish(entry, gate, standstill=standstill, steer_at_standstill=steer_at_standstill, **kwargs)


def create(CP, aol_replay: bool):
  return RetrofitTransitionDiagnostic() if aol_replay and configured(CP) else None

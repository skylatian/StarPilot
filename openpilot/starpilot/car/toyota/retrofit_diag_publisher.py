"""Publish TOYOTA_COROLLA_RETROFIT custom-ECU status as starpilotCarState.retrofitDiag.

The status rides on the starpilotCarState companion card already sends (learning evidence,
car GPS). When card has none for a frame, a diagnostics-only message goes out on every
STANDALONE_PUBLISH_DECIMATION-th carState frame (10 Hz) instead of every frame, so the
consumers of the full-rate companion see as few extra messages as possible.
"""
from openpilot.cereal import messaging


def attach(car_state, companion, cs_send):
  """Return the companion to send this frame (possibly None), with retrofitDiag filled in."""
  tracker = getattr(car_state, 'retrofit_diag', None)
  if tracker is None or tracker.state is None:
    return companion
  standalone = companion is None
  if standalone and not tracker.standalone_publish_due:
    return companion
  message = (messaging.new_message('starpilotCarState', valid=bool(cs_send.valid), logMonoTime=int(cs_send.logMonoTime))
             if standalone else companion)
  try:
    if standalone:
      message.starpilotCarState.sourceCarStateMonoTime = int(cs_send.logMonoTime)
    message.starpilotCarState.retrofitDiag = tracker.state
  except Exception:
    return companion  # Diagnostics are optional; never disturb the carState publish.
  return message

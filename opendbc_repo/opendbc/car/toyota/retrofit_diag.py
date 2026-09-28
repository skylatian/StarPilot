"""Status of the TOYOTA_COROLLA_RETROFIT custom ECUs (corolla_emulator repo).

The emulator (0x500), cruise stalk (0x501) and VSS (0x502) ECUs each send a 2 Hz
diagnostic frame; the stalk's own 0x69 frame shows whether it is transmitting at all.
This turns them into StarPilotCarState.retrofitDiag, and counts restarts (boot
counter changes) and CAN controller recoveries so selfdrived can alert on them.

All of these messages are registered with a NaN frequency: they never count toward
canValid, so a silent or old-firmware ECU cannot trigger a CAN error through them.
"""
from opendbc.can import CANParser

STALK_MSG = "CRUISE_STALK"
EMULATOR_DIAG_MSG = "RETROFIT_EMULATOR_DIAG"
STALK_DIAG_MSG = "RETROFIT_STALK_DIAG"
VSS_DIAG_MSG = "RETROFIT_VSS_DIAG"

PT_MESSAGES = [
  (STALK_MSG, float('nan')),
  (EMULATOR_DIAG_MSG, float('nan')),
  (STALK_DIAG_MSG, float('nan')),
  (VSS_DIAG_MSG, float('nan')),
]


def _last_seen_nanos(cp: CANParser, msg: str) -> int:
  return cp.ts_nanos[msg]["CHECKSUM"]


class _EcuTracker:
  def __init__(self, msg: str, ecu: str):
    self.msg = msg
    self.ecu = ecu
    self.boot_count: int | None = None
    self.restarts = 0
    self.prev_recoveries: int | None = None
    self.recovery_events = 0

  def update(self, cp: CANParser, now_nanos: int, out) -> tuple[bool, bool]:
    """Fill one RetrofitEcuDiag; returns (restarted, recovered) for this update."""
    seen_nanos = _last_seen_nanos(cp, self.msg)
    out.seen = seen_nanos > 0
    out.restarts = self.restarts
    out.recoveryEvents = self.recovery_events
    if not out.seen:
      return False, False

    vl = cp.vl[self.msg]
    out.age = max(now_nanos - seen_nanos, 0) * 1e-9

    restarted = False
    boot_count = int(vl["BOOT_COUNT"])
    if self.boot_count is not None and boot_count != self.boot_count:
      self.restarts += 1
      self.prev_recoveries = None  # recovery counter restarts from 0 with the ECU
      restarted = True
    self.boot_count = boot_count

    recovered = False
    recoveries = int(vl["CAN_RECOVERIES"])
    if self.prev_recoveries is not None and recoveries > self.prev_recoveries:
      self.recovery_events += recoveries - self.prev_recoveries
      recovered = True
    self.prev_recoveries = recoveries

    out.bootCount = boot_count
    out.restarts = self.restarts
    out.resetKind = int(vl["RESET_KIND"])
    out.canRecoveries = recoveries
    out.recoveryEvents = self.recovery_events
    out.canErrorFlags = int(vl["CAN_ERROR_FLAGS"])
    out.txFails = int(vl["TX_FAILS"])
    out.loopMaxMs = int(vl["LOOP_MAX_MS"])
    return restarted, recovered


class RetrofitDiagTracker:
  def __init__(self):
    self.emulator = _EcuTracker(EMULATOR_DIAG_MSG, "emulator")
    self.stalk = _EcuTracker(STALK_DIAG_MSG, "stalk")
    self.vss = _EcuTracker(VSS_DIAG_MSG, "vss")
    self.start_nanos = 0
    self.last_restart_ecu = "none"
    self.last_recovery_ecu = "none"

  def update(self, cp: CANParser, fp_ret) -> None:
    now = cp.last_nonempty_nanos
    if self.start_nanos == 0:
      self.start_nanos = now
    diag = fp_ret.init("retrofitDiag")

    for tracker, out in ((self.emulator, diag.emulator), (self.stalk, diag.stalk), (self.vss, diag.vss)):
      restarted, recovered = tracker.update(cp, now, out)
      if restarted:
        self.last_restart_ecu = tracker.ecu
      if recovered:
        self.last_recovery_ecu = tracker.ecu

    # Stalk transmit health from 0x69 itself — works with any stalk firmware.
    stalk_seen = _last_seen_nanos(cp, STALK_MSG)
    diag.stalkFrameAge = max(now - (stalk_seen or self.start_nanos), 0) * 1e-9
    diag.stalkMainOn = bool(cp.vl[STALK_MSG]["MAIN_ON"])

    if diag.stalk.seen:
      stalk = cp.vl[STALK_DIAG_MSG]
      diag.stalk.resetPhase = int(stalk["RESET_PHASE"])
      diag.stalk.recoveryReason = int(stalk["RECOVERY_REASON"])
      diag.stalk.initRetries = int(stalk["INIT_RETRIES"])
      diag.stalkC3Present = bool(stalk["C3_PRESENT"])

    if diag.emulator.seen:
      emulator = cp.vl[EMULATOR_DIAG_MSG]
      diag.emulatorCruiseState = int(emulator["CRUISE_STATE"])
      diag.emulatorStalkPresent = bool(emulator["STALK_PRESENT"])
      diag.emulatorLastTransition = int(emulator["LAST_TRANSITION"])
      diag.emulatorStalkLosses = int(emulator["STALK_LOSSES"])

    if diag.vss.seen:
      vss = cp.vl[VSS_DIAG_MSG]
      diag.vss.recoveryReason = int(vss["RECOVERY_REASON"])
      diag.vssPulses = int(vss["VSS_PULSES"])
      diag.vssForceDrive = bool(vss["FORCE_DRIVE"])

    diag.lastRestartEcu = self.last_restart_ecu
    diag.lastRecoveryEcu = self.last_recovery_ecu

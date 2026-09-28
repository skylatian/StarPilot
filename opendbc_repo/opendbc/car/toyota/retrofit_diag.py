"""Status of the TOYOTA_COROLLA_RETROFIT custom ECUs (corolla_emulator repo).

The emulator (0x500), cruise stalk (0x501) and VSS (0x502) ECUs each send a 2 Hz
diagnostic frame, plus a firmware version frame (0x503-0x505) alternating the
FW_VERSION tag and the compile timestamp; the stalk's own 0x69 frame shows whether
it is transmitting at all.
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
EMULATOR_VERSION_MSG = "RETROFIT_EMULATOR_VERSION"
STALK_VERSION_MSG = "RETROFIT_STALK_VERSION"
VSS_VERSION_MSG = "RETROFIT_VSS_VERSION"

PT_MESSAGES = [(name, float('nan')) for name in (
  STALK_MSG,
  EMULATOR_DIAG_MSG, STALK_DIAG_MSG, VSS_DIAG_MSG,
  EMULATOR_VERSION_MSG, STALK_VERSION_MSG, VSS_VERSION_MSG,
)]

VERSION_CHARS = [f"VERSION_CHAR_{i}" for i in range(1, 8)]
BUILD_FIELDS = ["BUILD_YEAR", "BUILD_MONTH", "BUILD_DAY", "BUILD_HOUR", "BUILD_MINUTE", "BUILD_SECOND"]


def _last_seen_nanos(cp: CANParser, msg: str) -> int:
  return cp.ts_nanos[msg]["CHECKSUM"]


def _frame_age(cp: CANParser, msg: str, now: int, start: int) -> float:
  # Messages carstate already reads (EPS, SAS, ...); vl access registers them if needed.
  cp.vl[msg]
  seen = max(cp.ts_nanos[msg].values(), default=0)
  return max(now - (seen or start), 0) * 1e-9


class _EcuTracker:
  def __init__(self, msg: str, version_msg: str, ecu: str):
    self.msg = msg
    self.version_msg = version_msg
    self.ecu = ecu
    self.firmware_version = ""
    self.build_time = ""
    self.boot_count: int | None = None
    self.restarts = 0
    self.prev_recoveries: int | None = None
    self.recovery_events = 0

  def _update_version(self, cp: CANParser) -> None:
    # Every signal is decoded from every frame (the parser ignores the DBC
    # multiplexer), so pair each frame's PAGE with its own bytes via vl_all.
    frames = cp.vl_all[self.version_msg]
    for i, page in enumerate(frames["PAGE"]):
      if page == 0:
        chars = bytes(int(frames[c][i]) for c in VERSION_CHARS)
        self.firmware_version = chars.split(b"\0")[0].decode("ascii", "replace")
      elif page == 1:
        y, mo, d, h, mi, sec = (int(frames[f][i]) for f in BUILD_FIELDS)
        self.build_time = f"{y:04d}-{mo:02d}-{d:02d} {h:02d}:{mi:02d}:{sec:02d}"

  def update(self, cp: CANParser, now_nanos: int, out) -> tuple[bool, bool]:
    """Fill one RetrofitEcuDiag; returns (restarted, recovered) for this update."""
    self._update_version(cp)
    out.firmwareVersion = self.firmware_version
    out.buildTime = self.build_time

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
    self.emulator = _EcuTracker(EMULATOR_DIAG_MSG, EMULATOR_VERSION_MSG, "emulator")
    self.stalk = _EcuTracker(STALK_DIAG_MSG, STALK_VERSION_MSG, "stalk")
    self.vss = _EcuTracker(VSS_DIAG_MSG, VSS_VERSION_MSG, "vss")
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

    diag.epsFrameAge = _frame_age(cp, "EPS_STATUS", now, self.start_nanos)
    diag.sasFrameAge = _frame_age(cp, "STEER_ANGLE_SENSOR", now, self.start_nanos)
    diag.emulatorFrameAge = _frame_age(cp, "PCM_CRUISE", now, self.start_nanos)
    diag.vssFrameAge = _frame_age(cp, "WHEEL_SPEEDS", now, self.start_nanos)
    diag.epsLkaState = int(cp.vl["EPS_STATUS"]["LKA_STATE"])

    diag.lastRestartEcu = self.last_restart_ecu
    diag.lastRecoveryEcu = self.last_recovery_ecu

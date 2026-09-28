"""Retrofit custom-ECU diagnostic frames (corolla_emulator repo) → StarPilotCarState.retrofitDiag.

The frames are packed here exactly the way the Arduino sketches pack them (byte by byte,
same shifts), so these tests pin the firmware layout to the DBC: a bit moved on either
side fails here.
"""
from types import SimpleNamespace

from cereal import custom
from opendbc.can import CANParser
from opendbc.car import Bus
from opendbc.car.toyota import retrofit_diag
from opendbc.car.toyota.carstate import CarState
from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.values import CAR, DBC

DBC_NAME = DBC[CAR.TOYOTA_COROLLA_RETROFIT][Bus.pt]
NS = 1_000_000_000


def fw_checksum(address: int, data: list[int]) -> int:
  # toyota_checksum() as written in the sketches
  s = len(data) + (address & 0xFF) + (address >> 8) + sum(data[:-1])
  return s & 0xFF


def frame(address: int, data: list[int]) -> tuple[int, bytes, int]:
  data = list(data)
  data[-1] = fw_checksum(address, data)
  return address, bytes(data), 0


def stalk_0x69(event: int, main_on: bool):
  return frame(0x69, [event, int(main_on), 0])


def stalk_diag(boot=1, rolling=0, reset_kind=0, reset_phase=0, recovery_reason=0, c3=True, main=False,
               eflg=0, tx_fails=0, init_retries=0, recoveries=0, loop_ms=0):
  d2 = (reset_phase << 4) | ((recovery_reason & 0x03) << 2) | (0x02 if c3 else 0) | (0x01 if main else 0)
  return frame(0x501, [boot, (rolling << 4) | reset_kind, d2, eflg, tx_fails,
                       (min(init_retries, 15) << 4) | min(recoveries, 15), loop_ms, 0])


def emulator_diag(boot=1, rolling=0, reset_kind=0, cruise_state=0, stalk_present=True, stalk_main=False,
                  transition=0, eflg=0, recoveries=0, stalk_losses=0, tx_fails=0, loop_ms=0):
  d2 = ((cruise_state & 0x03) << 6) | (0x20 if stalk_present else 0) | (0x10 if stalk_main else 0) | (transition & 0x0F)
  return frame(0x500, [boot, (rolling << 4) | reset_kind, d2, eflg,
                       (min(recoveries, 15) << 4) | min(stalk_losses, 15), tx_fails, loop_ms, 0])


def vss_diag(boot=1, rolling=0, reset_kind=0, recovery_reason=0, force_drive=True, recoveries=0,
             eflg=0, tx_fails=0, pulses=0, loop_ms=0):
  d2 = ((recovery_reason & 0x03) << 6) | (0x20 if force_drive else 0) | min(recoveries, 15)
  return frame(0x502, [boot, (rolling << 4) | reset_kind, d2, eflg, tx_fails, pulses, loop_ms, 0])


def version_frame(address: int, page: int, tag: str = "092726a", build=(26, 9, 27, 14, 3, 22)):
  # send_version_page() as written in the sketches: no checksum, page byte first
  data = [page, 0, 0, 0, 0, 0, 0, 0]
  if page == 0:
    data[1:8] = list(tag.encode())
  else:
    data[1:7] = list(build)
  return address, bytes(data), 0


class Harness:
  def __init__(self):
    self.cp = CANParser(DBC_NAME, retrofit_diag.PT_MESSAGES, 0)
    self.tracker = retrofit_diag.RetrofitDiagTracker()
    self.t = NS

  def step(self, frames, dt=0.05):
    self.t += int(dt * NS)
    self.cp.update([(self.t, frames)])
    fp_ret = custom.StarPilotCarState.new_message()
    self.tracker.update(self.cp, fp_ret)
    return fp_ret.retrofitDiag


class TestRetrofitDiag:
  def test_firmware_layout_decodes(self):
    h = Harness()
    d = h.step([
      stalk_0x69(0, True),
      stalk_diag(boot=7, rolling=5, reset_kind=4, reset_phase=5, recovery_reason=3, c3=True, main=True,
                 eflg=0x21, tx_fails=9, init_retries=2, recoveries=3, loop_ms=17),
      emulator_diag(boot=200, rolling=15, reset_kind=0, cruise_state=2, stalk_present=True, stalk_main=True,
                    transition=9, eflg=0x40, recoveries=1, stalk_losses=4, tx_fails=250, loop_ms=31),
      vss_diag(boot=3, recovery_reason=1, force_drive=True, recoveries=2, eflg=0x04, tx_fails=1, pulses=123, loop_ms=4),
    ])

    assert d.stalk.seen and d.emulator.seen and d.vss.seen
    assert (d.stalk.bootCount, d.stalk.resetKind, d.stalk.resetPhase, d.stalk.recoveryReason) == (7, 4, 5, 3)
    assert (d.stalk.canErrorFlags, d.stalk.txFails, d.stalk.initRetries, d.stalk.canRecoveries, d.stalk.loopMaxMs) == (0x21, 9, 2, 3, 17)
    assert d.stalkC3Present and d.stalkMainOn

    assert (d.emulator.bootCount, d.emulatorCruiseState, d.emulatorLastTransition, d.emulatorStalkLosses) == (200, 2, 9, 4)
    assert d.emulatorStalkPresent
    assert (d.emulator.canErrorFlags, d.emulator.canRecoveries, d.emulator.txFails, d.emulator.loopMaxMs) == (0x40, 1, 250, 31)

    assert (d.vss.bootCount, d.vss.recoveryReason, d.vss.canRecoveries, d.vss.canErrorFlags) == (3, 1, 2, 0x04)
    assert (d.vss.txFails, d.vssPulses, d.vss.loopMaxMs) == (1, 123, 4)
    assert d.vssForceDrive

  def test_bad_checksum_is_ignored(self):
    h = Harness()
    addr, dat, bus = stalk_diag(boot=9)
    corrupt = bytes(dat[:-1]) + bytes([(dat[-1] + 1) & 0xFF])
    d = h.step([(addr, corrupt, bus)])
    assert not d.stalk.seen

  def test_restart_counted_once_per_boot_change(self):
    h = Harness()
    d = h.step([stalk_diag(boot=10)])
    assert d.stalk.restarts == 0  # first frame is only a baseline
    d = h.step([stalk_diag(boot=10)])
    assert d.stalk.restarts == 0
    d = h.step([stalk_diag(boot=11, reset_kind=4, reset_phase=5)])
    assert d.stalk.restarts == 1
    assert d.lastRestartEcu == "stalk"
    d = h.step([stalk_diag(boot=11)])
    assert d.stalk.restarts == 1
    d = h.step([stalk_diag(boot=0)])  # EEPROM counter wraps 255 -> 0 like any other change
    assert d.stalk.restarts == 2

  def test_recovery_counted_and_reset_by_reboot(self):
    h = Harness()
    h.step([vss_diag(boot=5, recoveries=0)])
    d = h.step([vss_diag(boot=5, recoveries=2, recovery_reason=1)])
    assert d.vss.recoveryEvents == 2
    assert d.lastRecoveryEcu == "vss"
    # A reboot restarts the ECU's own counter at 0 — not a recovery
    d = h.step([vss_diag(boot=6, recoveries=0)])
    assert d.vss.recoveryEvents == 2 and d.vss.restarts == 1
    d = h.step([vss_diag(boot=6, recoveries=1)])
    assert d.vss.recoveryEvents == 3

  def test_stalk_frame_age(self):
    h = Harness()
    d = h.step([stalk_0x69(0, False)])
    assert d.stalkFrameAge < 0.01
    for _ in range(30):  # 1.5 s of other traffic, no 0x69
      d = h.step([vss_diag()])
    assert 1.4 < d.stalkFrameAge < 1.6

  def test_stalk_never_seen_ages_from_start(self):
    h = Harness()
    for _ in range(25):
      d = h.step([vss_diag()])
    assert d.stalkFrameAge > 1.0

  def test_old_firmware_without_diag_frames(self):
    # 0x69 only (current stalk firmware), no 0x500-0x502: nothing marked seen, no counts
    h = Harness()
    d = h.step([stalk_0x69(0, True)])
    assert not (d.stalk.seen or d.emulator.seen or d.vss.seen)
    assert d.stalk.restarts == 0 and d.lastRestartEcu == "none"
    assert d.stalkMainOn

  def test_diag_messages_never_affect_can_valid(self):
    h = Harness()
    h.step([stalk_diag(), emulator_diag(), vss_diag(), stalk_0x69(0, True)])
    for _ in range(100):  # 5 s of silence from all four
      h.step([(0x7FF, bytes(8), 0)])
    assert h.cp.can_valid

  def test_registered_for_retrofit_only(self):
    toggles = SimpleNamespace(force_torque_controller=False, nnff=False, nnff_lite=False)
    for car, expected in ((CAR.TOYOTA_COROLLA_RETROFIT, True), (CAR.TOYOTA_COROLLA, False)):
      CP = CarInterface.get_params(car, {bus: {} for bus in range(8)}, [], False, False, False, toggles)
      cp = CarState.get_can_parsers(CP)[Bus.pt]
      for name, _ in retrofit_diag.PT_MESSAGES:
        addr = cp.dbc.name_to_msg[name].address
        assert (addr in cp.message_states) == expected, (car, name)
        if expected:
          assert cp.message_states[addr].ignore_alive

  def test_firmware_version_pages(self):
    h = Harness()
    d = h.step([version_frame(0x504, 0, "092726a")])
    assert d.stalk.firmwareVersion == "092726a"
    assert d.stalk.buildTime == ""
    d = h.step([version_frame(0x504, 1, build=(26, 9, 27, 14, 3, 22))])
    assert d.stalk.buildTime == "2026-09-27 14:03:22"
    assert d.stalk.firmwareVersion == "092726a"  # kept from the earlier page
    d = h.step([vss_diag()])  # no version frame in this update: values persist
    assert d.stalk.firmwareVersion == "092726a" and d.stalk.buildTime == "2026-09-27 14:03:22"

  def test_both_pages_in_one_update_and_per_ecu(self):
    h = Harness()
    d = h.step([
      version_frame(0x503, 0, "092726b"), version_frame(0x503, 1, build=(26, 12, 1, 0, 0, 5)),
      version_frame(0x505, 0, "100126z"),
    ])
    assert (d.emulator.firmwareVersion, d.emulator.buildTime) == ("092726b", "2026-12-01 00:00:05")
    assert d.vss.firmwareVersion == "100126z"
    assert d.stalk.firmwareVersion == ""

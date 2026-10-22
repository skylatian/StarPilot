#!/usr/bin/env python3
"""Re-run the TOYOTA_COROLLA_RETROFIT car interface over a logged CAN stream.

Builds CarParams offline, feeds every logged `can` event to CI.update() (what card.state_update()
does), and fails on persistent CAN errors. Runs on the macOS host, where process_replay cannot.

The rlogs were recorded on StarPilot 6.7.x, so they are decoded with the 6.7.8 schema vendored in
cereal_6_7_8/ (copied unchanged from skylatian/StarPilot retrofit-dev-6.7.8-update-sandbox @
38134a41cd). Only `can`, `initData`, `carState` and `starpilotCarState` are read.

When the log has them, the result is also compared sample by sample with the carState and
retrofitDiag that 6.7.x computed on the car from the same CAN, and any difference fails the check
(--no-compare-gate to only report it). Logs recorded on older code can differ for good reasons.

  ./dev python scripts/retrofit/carstate_check.py [rlog or segment dir ...]
"""
import argparse
import bz2
import csv
import math
import os
import sys
from collections import Counter, deque
from pathlib import Path

DEFAULT_FINGERPRINT = "TOYOTA_COROLLA_RETROFIT"

# Pinned so the gate compares against a fixed input: a PASS->FAIL flip means the code changed,
# not the log. 6.7.8 baseline: project_docs/phase3-starpilot-2026-09-16-desktop-host-testing.md
DEFAULT_RLOG = "b22b100698b34d9f_00000256--3472968bc9--1--rlog.zst"

SCHEMA_DIR = Path(__file__).resolve().parent / "cereal_6_7_8"

FAULT_FIELDS = ("steerFaultTemporary", "steerFaultPermanent", "accFaulted", "espDisabled")

# carState fields compared with what the car logged. Floats must match to their tolerance.
COMPARED_BOOLS = ("canValid", "canTimeout", "standstill", "steeringPressed", "brakePressed", "gasPressed",
                  "leftBlinker", "rightBlinker", *FAULT_FIELDS)
COMPARED_FLOATS = ("steeringAngleDeg", "steeringRateDeg", "steeringTorque", "steeringTorqueEps", "vEgo")
COMPARED_CRUISE = ("enabled", "available", "speed")
TOLERANCE = {"vEgo": 0.02}  # m/s; the rest 1e-3
DEFAULT_TOLERANCE = 1e-3
# card drains every queued CAN packet into one CI.update(), so its vEgo filter steps once per batch,
# while this run steps once per packet. That moves vEgo by a few mm/s for a moment, nothing more.
# card drains every queued CAN packet before it publishes, so a logged sample may reflect any of the
# last few packets. A field counts as different only if it matches none of the last LAG_WINDOW samples.
LAG_WINDOW = 3
# Either side can start cold: this run at the start of every log, the car's card at the start of a
# drive (segment 0) or after a restart. Parsers and the vEgo filter settle within ~0.4 s, so each
# side's first second is not compared.
COMPARE_AFTER = 100
# A log ends when loggerd stops, often at a power cut, and the two sides lose CAN a few samples apart.
# The half second before the final dropout (or the end of the log) is not compared either.
END_SKIP = 50

# retrofitDiag fields that are instantaneous (not counted since card started, which predates a segment)
DIAG_ECU_FIELDS = ("seen", "bootCount", "resetKind", "firmwareVersion", "buildTime", "canErrorFlags")
DIAG_FRESH_S = 1.0
DIAG_FIELDS = ("stalkMainOn", "emulatorCruiseState", "emulatorStalkPresent", "epsLkaState", "vssForceDrive")


def repo_root():
  # `./dev python` runs from the host worktree under .host_runtime/, so walk back to the real repo
  parts = Path(__file__).resolve().parts
  return Path(*parts[:parts.index(".host_runtime")]) if ".host_runtime" in parts else Path(__file__).resolve().parents[2]


def default_log_dir():
  if env := os.environ.get("SP_RETROFIT_LOG_DIR"):
    return Path(env)
  return repo_root().parent / "logs"  # logs/ sits next to the repo


def resolve_rlog(given):
  # `./dev python` runs from the host worktree, so resolve relative paths against the repo, then the log dir
  for candidate in (Path(given), repo_root() / given, default_log_dir() / Path(given).name):
    if candidate.is_dir():
      # a synced segment dir (logs/log_dump/<route>--<segment>/)
      for name in ("rlog.zst", "rlog.bz2", "rlog"):
        if (candidate / name).exists():
          return (candidate / name).resolve()
    elif candidate.exists():
      return candidate.resolve()
  raise SystemExit(f"rlog not found: {given} (also looked in {default_log_dir()})")


def baseline_rlog():
  rlog = default_log_dir() / DEFAULT_RLOG
  if not rlog.exists():
    raise SystemExit(
      f"Baseline rlog not found: {rlog}\n" +
      "It is not in git (logs/ lives outside the repo), so on a fresh machine either download it, " +
      "pass a different rlog as an argument, or set SP_RETROFIT_LOG_DIR to where your logs live."
    )
  return rlog


def load_schema():
  import capnp
  # A parser of its own: the 6.7.8 log.capnp has the same file ID as openpilot's cereal
  return capnp.SchemaParser().load(str(SCHEMA_DIR / "log.capnp"), imports=[str(SCHEMA_DIR)])


def read_log_bytes(path: Path) -> tuple[bytes, bool]:
  """Returns (data, complete). Logs cut off by a power loss decode up to the cut."""
  raw = path.read_bytes()
  if path.suffix == ".zst":
    import zstandard
    out = bytearray()
    try:
      with zstandard.ZstdDecompressor().stream_reader(raw) as reader:
        while chunk := reader.read(1 << 20):
          out += chunk
    except zstandard.ZstdError:
      return bytes(out), False
    return bytes(out), True
  if path.suffix == ".bz2":
    return bz2.decompress(raw), True
  return raw, True


def iter_events(schema, data: bytes):
  """Yields (which, event). Stops quietly at a truncated final event."""
  try:
    for ev in schema.Event.read_multiple_bytes(data):
      try:
        yield ev.which(), ev
      except Exception:
        continue  # a union member this schema doesn't know
  except Exception:
    return


def logged_param(init_data, key):
  for entry in init_data.params.entries:
    if entry.key == key:
      return bytes(entry.value)
  return None


def format_ranges(indices, limit=6):
  ranges, start, prev = [], indices[0], indices[0]
  for i in indices[1:]:
    if i != prev + 1:
      ranges.append((start, prev))
      start = i
    prev = i
  ranges.append((start, prev))
  shown = ", ".join(f"{a}" if a == b else f"{a}-{b}" for a, b in ranges[:limit])
  return shown + (f", (+{len(ranges) - limit} more)" if len(ranges) > limit else "")


def carstate_fields(cs):
  """The compared fields of a logged (capnp) or port (opendbc struct) carState."""
  out = {f: bool(getattr(cs, f)) for f in COMPARED_BOOLS}
  out.update({f: float(getattr(cs, f)) for f in COMPARED_FLOATS})
  out.update({f"cruise.{f}": getattr(cs.cruiseState, f) for f in COMPARED_CRUISE})
  out["gearShifter"] = str(cs.gearShifter)
  return out


def logged_diag(diag):
  # An ECU's fields latch since the car's card started, which usually predates the log, and stay
  # latched while its frame is missing or dropped. Compare them only while the car had a fresh frame.
  out = {f"{ecu}.{f}": getattr(getattr(diag, ecu), f) for ecu in ("emulator", "stalk", "vss")
         if getattr(diag, ecu).seen and getattr(diag, ecu).age < DIAG_FRESH_S for f in DIAG_ECU_FIELDS}
  # version pages alternate at 2 Hz, so a card that just started may not have one yet
  out = {k: v for k, v in out.items() if not (k.endswith(("firmwareVersion", "buildTime")) and v == "")}
  out.update({f: getattr(diag, f) for f in DIAG_FIELDS})
  return out


def port_diag(diag):
  out = {f"{ecu}.{f}": diag[ecu][f] for ecu in ("emulator", "stalk", "vss") for f in DIAG_ECU_FIELDS}
  out.update({f: diag[f] for f in DIAG_FIELDS})
  return out


def same(key, a, b):
  if isinstance(a, float) or isinstance(b, float):
    return math.isclose(float(a), float(b), abs_tol=TOLERANCE.get(key, DEFAULT_TOLERANCE))
  return a == b


class Comparison:
  def __init__(self, name):
    self.name = name
    self.logged_seen = 0
    self.compared = []  # sample indices
    self.differences = []  # (sample index, key, logged, port)

  def add(self, index, logged, recent):
    """recent: the port's last LAG_WINDOW samples, newest last"""
    self.logged_seen += 1
    if self.logged_seen <= COMPARE_AFTER:
      return
    self.compared.append(index)
    for key, value in logged.items():
      if not any(same(key, value, port[key]) for port in recent):
        self.differences.append((index, key, value, recent[-1][key]))

  def finish(self, end):
    """end: the first sample of the shutdown dropout at the end of the log (or its length)"""
    self.compared = [i for i in self.compared if i < end - END_SKIP]
    self.differences = [d for d in self.differences if d[0] < end - END_SKIP]

  @property
  def samples(self):
    return len(self.compared)

  @property
  def mismatches(self):
    return Counter(key for _, key, _, _ in self.differences)

  def report(self, sas_offset=None):
    print(f"\n--- port vs logged {self.name}: {self.samples} samples " +
          f"(first {COMPARE_AFTER} of each side and last {END_SKIP} skipped) ---")
    if not self.samples:
      print("  (not in this log)")
      return
    if not self.differences:
      print("  all compared fields match")
      return
    for key, count in sorted(self.mismatches.items()):
      rows = [d for d in self.differences if d[1] == key]
      i, _, logged, port = rows[0]
      print(f"  {key + ':':22}{count} / {self.samples} differ, samples {i}-{rows[-1][0]} " +
            f"(first: logged {logged!r}, port {port!r})")
      if key == "steeringAngleDeg" and sas_offset is not None:
        # a constant gap means the car ran another SAS offset (6.7.x read it live; initData is the boot value)
        gaps = [logged - port for _, _, logged, port in rows]
        if max(gaps) - min(gaps) < 0.2:
          car_offset = sas_offset - sum(gaps) / len(gaps)
          print(f"  {'':22}constant gap: the car used a SAS offset of {car_offset:.1f} deg on these samples " +
                f"(this run: {sas_offset:g}); rerun with --sas-offset {car_offset:.0f}")


def check(rlog: Path, args) -> tuple[list[str], str]:
  """Prints the full report for one log; returns (failures, one-line summary)."""
  from opendbc.car import gen_empty_fingerprint
  from opendbc.car.car_helpers import interfaces
  from opendbc.car.toyota.retrofit import apply_sas_offset, sas_offset_deg

  candidate = args.fingerprint
  if candidate not in interfaces:
    raise SystemExit(f"unknown platform: {candidate}")

  schema = load_schema()
  data, complete = read_log_bytes(rlog)
  # loggerd writes services in arrival order, not time order
  events = sorted(iter_events(schema, data), key=lambda e: e[1].logMonoTime)
  init = next((ev.initData for which, ev in events if which == "initData"), None)

  sas_offset, sas_source = args.sas_offset, "--sas-offset"
  if sas_offset is None:
    raw = logged_param(init, "RetrofitSASOffset") if init is not None else None
    sas_offset = float(raw) if raw else 0.0
    sas_source = "log initData" if raw else "default (not in log)"

  CP = interfaces[candidate].get_params(candidate, gen_empty_fingerprint(), [], args.alpha_long, False, docs=False)
  CI = interfaces[candidate](CP)
  # card applies this at startup through VehicleStartupPreferences.configure_controller
  apply_sas_offset(CI.CS, sas_offset)

  print(f"log:        {rlog}{'' if complete else '  (truncated; decoded up to the cut)'}")
  if init is not None:
    print(f"recorded:   {init.gitBranch} @ {init.gitCommit[:10]}")
  print(f"platform:   {CP.carFingerprint} (opLong={CP.openpilotLongitudinalControl} " +
        f"radarUnavailable={CP.radarUnavailable})")
  print(f"SAS offset: {CI.CS.sas_offset_deg:g} deg (from {sas_source}" +
        f"{'' if sas_offset_deg(sas_offset) == sas_offset else f'; {sas_offset} rejected'})")
  states, diags = [], []
  recent_cs, recent_diag = deque(maxlen=LAG_WINDOW), deque(maxlen=LAG_WINDOW)
  cs_cmp, diag_cmp = Comparison("carState"), Comparison("retrofitDiag")
  for which, ev in events:
    if which == "can":
      frames = [(c.address, bytes(c.dat), c.src) for c in ev.can]
      states.append(CI.update([(ev.logMonoTime, frames)]))
      diags.append(CI.CS.retrofit_diag.state if CI.CS.retrofit_diag is not None else None)
      recent_cs.append(carstate_fields(states[-1]))
      if diags[-1] is not None:
        recent_diag.append(port_diag(diags[-1]))
    elif len(states) < COMPARE_AFTER:
      continue
    elif which == "carState":
      cs_cmp.add(len(states) - 1, carstate_fields(ev.carState), recent_cs)
    elif which == "starpilotCarState" and ev.starpilotCarState._has("retrofitDiag") and recent_diag:
      diag_cmp.add(len(states) - 1, logged_diag(ev.starpilotCarState.retrofitDiag), recent_diag)

  if not states:
    print("\nFAIL: no can messages in log")
    return ["no can messages in log"], f"FAIL  no can messages  {rlog}"

  n = len(states)
  invalid = [i for i, s in enumerate(states) if not s.canValid]
  invalid_set = set(invalid)

  # CAN legitimately drops while the parsers warm up, and again as the log ends mid-shutdown.
  # Only invalidity between those windows indicates a real fault.
  head = 0
  while head in invalid_set:
    head += 1
  # at shutdown canTimeout can lead canValid by a sample, so the tail is the trailing run of either
  tail = 0
  while tail < n - head and (not states[n - 1 - tail].canValid or states[n - 1 - tail].canTimeout):
    tail += 1

  middle = [i for i in invalid if head <= i < n - tail]
  timeouts = sum(1 for s in states if s.canTimeout)
  middle_timeouts = sum(1 for i, s in enumerate(states) if s.canTimeout and head <= i < n - tail)

  print(f"\n--- carState over all {n} samples ---")
  print(f"{'canValid False:':26}{len(invalid)} / {n}  (warmup {head}, tail {tail}, mid-log {len(middle)})")
  if invalid:
    print(f"{'  invalid ranges:':26}{format_ranges(invalid)}")
  print(f"{'canTimeout:':26}{timeouts} / {n}  (mid-log {middle_timeouts})")
  for f in FAULT_FIELDS:
    print(f"{f + ':':26}{sum(1 for s in states if getattr(s, f, False))} / {n}")
  print(f"{'vEgo min/max:':26}{min(s.vEgo for s in states):.2f} / {max(s.vEgo for s in states):.2f}")
  print(f"{'steeringAngleDeg min/max:':26}{min(s.steeringAngleDeg for s in states):.1f} / " +
        f"{max(s.steeringAngleDeg for s in states):.1f}")
  print(f"{'cruiseState.available:':26}{sum(1 for s in states if s.cruiseState.available)} / {n}")
  print(f"{'cruiseState.enabled:':26}{sum(1 for s in states if s.cruiseState.enabled)} / {n}")
  print(f"{'gearShifter:':26}{Counter(str(s.gearShifter) for s in states).most_common()}")

  if (last := next((d for d in reversed(diags) if d is not None), None)) is not None:
    print("\n--- retrofitDiag (port decode, end of log) ---")
    for ecu in ("emulator", "stalk", "vss"):
      d = last[ecu]
      print(f"  {ecu + ':':10}{'seen' if d['seen'] else 'not seen':9} fw {d['firmwareVersion'] or '-':8} " +
            f"boot {d['bootCount']:3}  restarts {d['restarts']}  recoveries {d['recoveryEvents']}")
    print(f"  {'stalk:':10}max 0x69 frame age {max(d['stalkFrameAge'] for d in diags if d is not None):.2f} s")

  cs_cmp.finish(n - tail)
  diag_cmp.finish(n - tail)
  cs_cmp.report(CI.CS.sas_offset_deg)
  diag_cmp.report()

  if args.dump:
    with args.dump.open("w", newline="") as f:
      writer = csv.writer(f)
      cols = [*COMPARED_BOOLS, *COMPARED_FLOATS, *(f"cruise.{c}" for c in COMPARED_CRUISE), "gearShifter"]
      writer.writerow(["sample", *cols])
      for i, s in enumerate(states):
        row = carstate_fields(s)
        writer.writerow([i, *(row[c] for c in cols)])
    print(f"\nwrote {args.dump}")

  failures = []
  if middle:
    failures.append(f"canValid dropped mid-log at {format_ranges(middle)}")
  if head > args.max_warmup:
    failures.append(f"canValid warmup {head} samples exceeds --max-warmup {args.max_warmup}")
  if tail > args.max_tail:
    failures.append(f"canValid tail dropout {tail} samples exceeds --max-tail {args.max_tail}")
  if middle_timeouts:
    failures.append(f"canTimeout on {middle_timeouts} mid-log samples")
  for cmp in (cs_cmp, diag_cmp):
    if cmp.mismatches and args.compare_gate:
      failures.append(f"port {cmp.name} differs from the logged one: {', '.join(sorted(cmp.mismatches))}")

  print()
  for f in failures:
    print(f"FAIL: {f}")
  if not failures:
    print(f"PASS: canValid held for all {n - head - tail} mid-log samples, no mid-log canTimeout"
          + (", matches the logged carState" if cs_cmp.samples else ""))

  faults = "/".join(str(sum(1 for s in states if getattr(s, f, False))) for f in FAULT_FIELDS)
  name = rlog.parent.name if rlog.name.startswith("rlog") else rlog.name
  summary = (f"{'FAIL' if failures else 'PASS'}  n={n} warmup={head} tail={tail} mid={len(middle)} timeouts={timeouts} " +
             f"faults={faults} cs={cs_cmp.samples}/{sum(cs_cmp.mismatches.values())} " +
             f"diag={diag_cmp.samples}/{sum(diag_cmp.mismatches.values())}{'' if complete else ' truncated'}  " +
             f"{init.gitBranch if init is not None else '?'}  {name}")
  return failures, summary


def main():
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("rlogs", nargs="*", metavar="rlog",
                      help=f"rlogs (.zst/.bz2/raw) or segment dirs holding one, default: pinned baseline {DEFAULT_RLOG}")
  parser.add_argument("--fingerprint", default=DEFAULT_FINGERPRINT)
  parser.add_argument("--max-warmup", type=int, default=200,
                      help="samples allowed to be canValid=False at the start (default: 200)")
  parser.add_argument("--max-tail", type=int, default=200,
                      help="samples allowed to be canValid=False at the end, where logs cut off mid-shutdown (default: 200)")
  parser.add_argument("--alpha-long", action=argparse.BooleanOptionalAction, default=True)
  parser.add_argument("--sas-offset", type=float,
                      help="RetrofitSASOffset in degrees (default: the value in the log's initData, else 0)")
  parser.add_argument("--dump", type=Path, help="write the port's per-sample carState to this CSV")
  parser.add_argument("--compare-gate", action=argparse.BooleanOptionalAction, default=True,
                      help="fail when the port's carState/retrofitDiag differs from the logged one (default: on)")
  args = parser.parse_args()

  if not args.rlogs:
    rlogs = [baseline_rlog()]
    print(f"Using pinned baseline rlog: {rlogs[0]}")
  else:
    rlogs = [resolve_rlog(r) for r in args.rlogs]
  if args.dump and len(rlogs) > 1:
    raise SystemExit("--dump takes a single rlog")

  results = []
  for rlog in rlogs:
    if len(rlogs) > 1:
      print(f"\n{'=' * 100}")
    results.append(check(rlog, args))

  if len(rlogs) > 1:
    print(f"\n{'=' * 100}\nsummary (faults = {'/'.join(FAULT_FIELDS)}; cs/diag = compared samples/differences)")
    for _, summary in results:
      print(summary)
    print(f"{sum(1 for failures, _ in results if not failures)} / {len(results)} passed")
  return 1 if any(failures for failures, _ in results) else 0


if __name__ == "__main__":
  sys.exit(main())

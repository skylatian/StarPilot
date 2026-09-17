#!/usr/bin/env python3
"""Re-run the car interface over a logged CAN stream and assert no persistent CAN errors.

Substitute for process_replay, which cannot run on macOS (SocketEventHandle). Mirrors
card.py state_update(): build CP/FPCP offline, then feed logged `can` events to CI.update().
"""
import argparse
import os
import sys
from collections import Counter
from pathlib import Path

DEFAULT_FINGERPRINT = "TOYOTA_COROLLA_RETROFIT"

# Pinned so the gate compares against a fixed input: a PASS->FAIL flip means the code changed,
# not the log. Baseline is recorded in project_docs/phase3-starpilot-2026-09-16-desktop-host-testing.md
DEFAULT_RLOG = "b22b100698b34d9f_00000256--3472968bc9--1--rlog.zst"


def default_log_dir():
  if env := os.environ.get("SP_RETROFIT_LOG_DIR"):
    return Path(env)
  # this runs from the host worktree under .host_runtime/, so walk back to the real repo
  here = Path(__file__).resolve()
  parts = here.parts
  root = Path(*parts[:parts.index(".host_runtime")]) if ".host_runtime" in parts else here.parents[1]
  return root.parent / "logs"


def resolve_rlog(given):
  # `./dev python` runs from the host worktree, so a path relative to the repo will not
  # resolve here. Fall back to matching the filename in the log dir before giving up and
  # passing it through as a route identifier.
  for candidate in (Path(given), default_log_dir() / Path(given).name):
    if candidate.exists():
      return str(candidate.resolve())
  return given


def baseline_rlog():
  log_dir = default_log_dir()
  rlog = log_dir / DEFAULT_RLOG
  if not rlog.exists():
    raise SystemExit(
      f"Baseline rlog not found: {rlog}\n"
      f"It is not in git (logs/ lives outside the repo), so on a fresh machine either download it, "
      f"pass a different rlog as an argument, or set SP_RETROFIT_LOG_DIR to where your logs live."
    )
  return rlog


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


def main():
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("rlog", nargs="?",
                      help="path to an rlog (.zst/.bz2), or any identifier LogReader accepts "
                           f"(default: pinned baseline {DEFAULT_RLOG})")
  parser.add_argument("--fingerprint", default=DEFAULT_FINGERPRINT)
  parser.add_argument("--max-warmup", type=int, default=200,
                      help="samples allowed to be canValid=False at the start (default: 200)")
  parser.add_argument("--max-tail", type=int, default=200,
                      help="samples allowed to be canValid=False at the end, where logs cut off mid-shutdown (default: 200)")
  parser.add_argument("--alpha-long", action=argparse.BooleanOptionalAction, default=True)
  args = parser.parse_args()

  if args.rlog is None:
    args.rlog = str(baseline_rlog())
    print(f"Using pinned baseline rlog: {args.rlog}")
  else:
    args.rlog = resolve_rlog(args.rlog)

  from openpilot.tools.lib.logreader import LogReader
  from openpilot.selfdrive.pandad import can_capnp_to_list
  from openpilot.starpilot.common.starpilot_variables import get_starpilot_toggles
  from opendbc.car import gen_empty_fingerprint
  from opendbc.car.car_helpers import interfaces

  candidate = args.fingerprint
  if candidate not in interfaces:
    raise SystemExit(f"unknown platform: {candidate}")

  toggles = get_starpilot_toggles(read_persisted_force_params=True)
  CI_cls = interfaces[candidate]
  CP = CI_cls.get_params(candidate, gen_empty_fingerprint(), [], args.alpha_long, False,
                         docs=False, starpilot_toggles=toggles)
  FPCP = CI_cls.get_starpilot_params(candidate, gen_empty_fingerprint(), [], CP, toggles)
  CI = CI_cls(CP, FPCP)

  print(f"log:      {args.rlog}")
  print(f"platform: {CP.carFingerprint} (opLong={CP.openpilotLongitudinalControl} "
        f"radarUnavailable={CP.radarUnavailable})")

  cans = [m for m in LogReader(args.rlog) if m.which() == "can"]
  if not cans:
    raise SystemExit("no can messages in log")

  states = []
  for m in cans:
    CS, _ = CI.update(can_capnp_to_list([m.as_builder().to_bytes()]), toggles)
    states.append(CS)

  n = len(states)
  invalid = [i for i, s in enumerate(states) if not s.canValid]
  invalid_set = set(invalid)

  # CAN legitimately drops while the parsers warm up, and again as the log ends mid-shutdown.
  # Only invalidity between those windows indicates a real fault.
  head = 0
  while head in invalid_set:
    head += 1
  tail = 0
  while (n - 1 - tail) in invalid_set:
    tail += 1

  middle = [i for i in invalid if head <= i < n - tail]
  timeouts = sum(1 for s in states if s.canTimeout)
  middle_timeouts = sum(1 for i, s in enumerate(states) if s.canTimeout and head <= i < n - tail)

  print(f"\n--- carState over all {n} samples ---")
  print(f"{'canValid False:':26}{len(invalid)} / {n}  (warmup {head}, tail {tail}, mid-log {len(middle)})")
  if invalid:
    print(f"{'  invalid ranges:':26}{format_ranges(invalid)}")
  print(f"{'canTimeout:':26}{timeouts} / {n}  (mid-log {middle_timeouts})")
  for f in ("steerFaultTemporary", "steerFaultPermanent", "accFaulted", "espDisabled"):
    print(f"{f + ':':26}{sum(1 for s in states if getattr(s, f, False))} / {n}")
  print(f"{'vEgo min/max:':26}{min(s.vEgo for s in states):.2f} / {max(s.vEgo for s in states):.2f}")
  print(f"{'steeringAngleDeg min/max:':26}{min(s.steeringAngleDeg for s in states):.1f} / "
        f"{max(s.steeringAngleDeg for s in states):.1f}")
  print(f"{'cruiseState.available:':26}{sum(1 for s in states if s.cruiseState.available)} / {n}")
  print(f"{'cruiseState.enabled:':26}{sum(1 for s in states if s.cruiseState.enabled)} / {n}")
  print(f"{'gearShifter:':26}{Counter(str(s.gearShifter) for s in states).most_common()}")

  failures = []
  if middle:
    failures.append(f"canValid dropped mid-log at {format_ranges(middle)}")
  if head > args.max_warmup:
    failures.append(f"canValid warmup {head} samples exceeds --max-warmup {args.max_warmup}")
  if tail > args.max_tail:
    failures.append(f"canValid tail dropout {tail} samples exceeds --max-tail {args.max_tail}")
  if middle_timeouts:
    failures.append(f"canTimeout on {middle_timeouts} mid-log samples")

  print()
  if failures:
    for f in failures:
      print(f"FAIL: {f}")
    return 1

  print(f"PASS: canValid held for all {n - head - tail} mid-log samples, no mid-log canTimeout")
  return 0


if __name__ == "__main__":
  sys.exit(main())

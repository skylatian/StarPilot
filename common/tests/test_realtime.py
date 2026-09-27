import ast
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from openpilot.common import realtime
from openpilot.common.basedir import BASEDIR

SCHED_FIFO, SCHED_RR, SCHED_OTHER = 1, 2, 0


def _fake_sched(monkeypatch, policy):
  calls = {}
  monkeypatch.setattr(realtime.os, "SCHED_FIFO", SCHED_FIFO, raising=False)
  monkeypatch.setattr(realtime.os, "SCHED_RR", SCHED_RR, raising=False)
  monkeypatch.setattr(realtime.os, "SCHED_OTHER", SCHED_OTHER, raising=False)
  monkeypatch.setattr(realtime.os, "sched_param", lambda priority: ("param", priority), raising=False)
  monkeypatch.setattr(realtime.os, "sched_getscheduler", lambda pid: policy, raising=False)
  monkeypatch.setattr(realtime.os, "sched_setscheduler", lambda pid, pol, param: calls.update(sched=(pid, pol, param)), raising=False)
  monkeypatch.setattr(realtime.os, "sched_setaffinity", lambda pid, cores: calls.update(affinity=(pid, set(cores))), raising=False)
  return calls


@pytest.mark.parametrize("policy", [SCHED_FIFO, SCHED_RR])
def test_drop_realtime_priority_moves_realtime_caller_to_background_cores(monkeypatch, policy):
  calls = _fake_sched(monkeypatch, policy)

  realtime.drop_realtime_priority()

  assert calls["sched"] == (0, SCHED_OTHER, ("param", 0))
  assert calls["affinity"] == (0, {0, 1, 2, 3})


def test_drop_realtime_priority_leaves_normal_caller_alone(monkeypatch):
  # e.g. The Galaxy's web server, or the UI on a desktop host: nothing to undo, and no pinning to 0-3.
  calls = _fake_sched(monkeypatch, SCHED_OTHER)

  realtime.drop_realtime_priority()

  assert calls == {}


def test_drop_realtime_priority_keeps_policy_change_when_affinity_fails(monkeypatch):
  calls = _fake_sched(monkeypatch, SCHED_FIFO)

  def no_affinity(pid, cores):
    raise OSError("cpuset")

  monkeypatch.setattr(realtime.os, "sched_setaffinity", no_affinity, raising=False)
  realtime.drop_realtime_priority()

  assert calls["sched"] == (0, SCHED_OTHER, ("param", 0))


def test_drop_realtime_priority_tolerates_missing_or_refused_sched_calls(monkeypatch):
  def unsupported(*args):
    raise AttributeError("no sched_* on this platform")

  monkeypatch.setattr(realtime.os, "sched_getscheduler", unsupported, raising=False)
  realtime.drop_realtime_priority()

  def refused(*args):
    raise OSError("EPERM")

  _fake_sched(monkeypatch, SCHED_FIFO)
  monkeypatch.setattr(realtime.os, "sched_setscheduler", refused, raising=False)
  realtime.drop_realtime_priority()


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="SCHED_FIFO and affinity are Linux-only")
def test_child_of_realtime_parent_runs_normal_off_parent_core():
  """The real thing: a FIFO parent pinned to one core, with and without the preexec_fn."""
  script = textwrap.dedent("""
    import os, subprocess, sys
    from openpilot.common.realtime import drop_realtime_priority
    try:
      os.sched_setscheduler(0, os.SCHED_FIFO, os.sched_param(1))
    except PermissionError:
      print("SKIP"); sys.exit(0)
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    probe = [sys.executable, "-c", "import os; print(os.sched_getscheduler(0), sorted(os.sched_getaffinity(0)))"]
    print(subprocess.run(probe, capture_output=True, text=True).stdout.strip())
    print(subprocess.run(probe, capture_output=True, text=True, preexec_fn=drop_realtime_priority).stdout.strip())
  """)
  out = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True, cwd=BASEDIR).stdout.split("\n")
  if out[0] == "SKIP":
    pytest.skip("needs CAP_SYS_NICE to become SCHED_FIFO")

  inherited, dropped = out[0], out[1]
  assert inherited.startswith(f"{os.SCHED_FIFO} ")
  assert dropped.startswith(f"{os.SCHED_OTHER} ")
  cores = sorted(set(realtime.BACKGROUND_CORES) & os.sched_getaffinity(0)) or None
  if cores:
    assert dropped == f"{os.SCHED_OTHER} {cores}"


# Subprocesses started from realtime processes (the UI is SCHED_FIFO 50 on core 5, starpilot_process
# SCHED_FIFO 51 on core 5). Each one is long-running or CPU-heavy, so each must pass
# preexec_fn=drop_realtime_priority. Keyed by function so an upstream merge that rewrites the call shows up here.
REALTIME_SPAWN_SITES = {
  "selfdrive/ui/layouts/settings/developer.py": ["_rebuild_worker"],
  "selfdrive/ui/layouts/settings/software.py": ["_run_worker"],
  "selfdrive/ui/layouts/settings/starpilot/sounds.py": ["_init_sound_player"],
  "selfdrive/ui/layouts/settings/starpilot/system_settings.py": ["_on_create_backup", "_on_restore_backup"],
  "system/ui/lib/application.py": ["init_window"],  # RECORD=1 screen recorder (libx264)
  "starpilot/assets/theme_manager.py": ["_git_list_tree", "_git_show_bytes"],
  "starpilot/common/starpilot_utilities.py": ["run_cmd"],
  "starpilot/system/the_galaxy/utilities.py": ["_start_dashboard_background_analysis"],
}
SPAWN_CALLS = {"Popen", "run", "call", "check_call", "check_output"}


def _spawn_calls(func):
  for node in ast.walk(func):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in SPAWN_CALLS \
       and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess":
      yield node


@pytest.mark.parametrize("path", sorted(REALTIME_SPAWN_SITES))
def test_realtime_spawn_sites_drop_realtime_priority(path):
  tree = ast.parse((Path(BASEDIR) / path).read_text())
  functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
               and node.name in REALTIME_SPAWN_SITES[path]]
  calls = [call for func in functions for call in _spawn_calls(func)]

  assert calls, f"no subprocess call found in {REALTIME_SPAWN_SITES[path]} of {path}; update REALTIME_SPAWN_SITES"
  for call in calls:
    preexec = {kw.arg: kw.value for kw in call.keywords}.get("preexec_fn")
    assert isinstance(preexec, ast.Name) and preexec.id == "drop_realtime_priority", \
      f"{path}:{call.lineno} starts a subprocess from a realtime process without preexec_fn=drop_realtime_priority"


def test_dashboard_refresh_thread_drops_realtime_priority():
  # starpilot_process runs this in a worker thread every 60 s offroad: ~0.7 s of CPU above the UI otherwise.
  tree = ast.parse((Path(BASEDIR) / "starpilot/starpilot_process.py").read_text())
  func = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "refresh_dashboard_analysis")
  first = func.body[0]
  assert isinstance(first, ast.Expr) and isinstance(first.value, ast.Call) and getattr(first.value.func, "id", None) == "drop_realtime_priority"

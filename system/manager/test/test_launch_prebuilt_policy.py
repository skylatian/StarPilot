from pathlib import Path
import re


LAUNCH_SCRIPT = Path(__file__).parents[3] / "launch_chffrplus.sh"


def test_prebuilt_marker_is_the_only_build_gate():
  script = LAUNCH_SCRIPT.read_text()

  assert "UsePrebuilt" not in script
  assert "prebuilt_runtime_compatible" not in script
  assert len(re.findall(r"\./build\.py", script)) == 1
  assert re.search(r'if \[ ! -f "\$DIR/prebuilt" \]; then\s+sp_launch_timing "build_start"\s+\./build\.py', script)


DEVELOPER_PANEL = Path(__file__).parents[3] / "selfdrive" / "ui" / "layouts" / "settings" / "developer.py"


def test_full_rebuild_button_bypasses_the_scons_cache():
  # Dropping .sconsign.dblite only clears scons' local up-to-date decisions; the CacheDir
  # still serves prebuilt artifacts, so without --cache-disable a "Full Rebuild" can copy
  # stale objects into place with fresh mtimes (this shipped a params_pyx.so whose key
  # table predated the Retrofit params).
  src = DEVELOPER_PANEL.read_text()
  cmd = re.search(r'FULL_REBUILD_CMD = "([^"]+)"', src)
  assert cmd, "FULL_REBUILD_CMD not found"
  assert "--cache-disable" in cmd.group(1)
  assert "rm -f .sconsign.dblite" in cmd.group(1)

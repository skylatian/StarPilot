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


def test_rebuild_buttons_differ_only_in_cache_use():
  # Dropping .sconsign.dblite only clears scons' local up-to-date decisions; the CacheDir
  # still serves already-built artifacts, so without --cache-disable a rebuild can copy
  # stale objects into place with fresh mtimes (this shipped a params_pyx.so whose key
  # table predated the Retrofit params). The cache is what makes the plain Rebuild fast,
  # so keep both: quick by default, --cache-disable when the artifacts are suspect.
  src = DEVELOPER_PANEL.read_text()
  quick = re.search(r'^REBUILD_CMD = "([^"]+)"', src, re.M)
  full = re.search(r'^FULL_REBUILD_CMD = "([^"]+)"', src, re.M)
  assert quick and full, "REBUILD_CMD / FULL_REBUILD_CMD not found"

  assert "--cache-disable" not in quick.group(1)
  assert "--cache-disable" in full.group(1)
  for cmd in (quick.group(1), full.group(1)):
    assert "rm -f .sconsign.dblite" in cmd
  # the two must stay otherwise identical, so the only variable is the cache
  assert full.group(1).replace(" --cache-disable", "") == quick.group(1)

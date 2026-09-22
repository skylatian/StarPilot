import os
import subprocess
import threading

from openpilot.common.basedir import BASEDIR
from openpilot.common.params import Params
from openpilot.system.hardware import HARDWARE
from openpilot.selfdrive.ui.widgets.ssh_key import ssh_key_item
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.widgets import Widget
from openpilot.system.ui.widgets.list_view import button_item, toggle_item
from openpilot.system.ui.widgets.scroller_tici import Scroller
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult

# Description constants
DESCRIPTIONS = {
  'enable_adb': tr_noop(
    "ADB (Android Debug Bridge) allows connecting to your device over USB or over the network. " +
    "See https://docs.comma.ai/how-to/connect-to-comma for more info."
  ),
  'ssh_key': tr_noop(
    "Warning: This grants SSH access to all public keys in your GitHub settings. Never enter a GitHub username " +
    "other than your own. A comma employee will NEVER ask you to add their GitHub username."
  ),
  'alpha_longitudinal': tr_noop(
    "<b>WARNING: openpilot longitudinal control is in alpha for this car and will disable Automatic Emergency Braking (AEB).</b><br><br>" +
    "On this car, openpilot defaults to the car's built-in ACC instead of openpilot's longitudinal control. " +
    "Enable this to switch to openpilot longitudinal control. Enabling Experimental mode is recommended when enabling openpilot longitudinal control alpha. " +
    "Changing this setting will restart openpilot if the car is powered on."
  ),
  'use_prebuilt': tr_noop(
    "When enabled (default), the device skips source compilation on boot if a prebuilt artifact exists. " +
    "Disable this if you plan to edit code and rebuild on-device."
  ),
  'rebuild': tr_noop(
    "Recompile changed code, then reboot. Required after param or panda safety changes when " +
    "\"Use Prebuilt Binaries\" is off. May reuse cached build artifacts, so it is much faster — try this first."
  ),
  'full_rebuild': tr_noop(
    "Recompile everything from source, ignoring the build cache, then reboot. Use this when a plain Rebuild " +
    "did not take effect — e.g. a setting will not apply, or a param is missing from the compiled table. " +
    "Takes ~20 minutes on Comma 3."
  ),
}

# The difference between these two is the scons CacheDir (SConstruct), and it matters:
# removing .sconsign.dblite drops only scons' local up-to-date decisions, NOT the cache.
# Without --cache-disable, scons recomputes a build signature and, on a cache hit, copies
# the artifact out of the cache instead of compiling it -- so a "rebuild" can write fresh
# mtimes with stale content. A C3 build once shipped a params_pyx.so whose key table
# predated the Retrofit params, where every put_float on one raised UnknownKeyName while
# get_float silently returned 0.0. The cache is what makes REBUILD_CMD quick, so keep it
# as the default path and reach for FULL_REBUILD_CMD when the artifacts are suspect.
REBUILD_CMD = "rm -f .sconsign.dblite && scons -j4 2>&1"
FULL_REBUILD_CMD = "rm -f .sconsign.dblite && scons --cache-disable -j4 2>&1"
FULL_REBUILD_REBOOT_DELAY = 2.5


class DeveloperLayout(Widget):
  def __init__(self):
    super().__init__()
    self._params = Params()
    self._params.put_bool("LongitudinalManeuverMode", False)

    # Build items and keep references for callbacks/state updates
    self._adb_toggle = toggle_item(
      lambda: tr("Enable ADB"),
      description=lambda: tr(DESCRIPTIONS["enable_adb"]),
      initial_state=self._params.get_bool("AdbEnabled"),
      callback=self._on_enable_adb,
      enabled=ui_state.is_offroad,
    )

    # SSH enable toggle + SSH key management
    self._ssh_toggle = toggle_item(
      lambda: tr("Enable SSH"),
      description="",
      initial_state=self._params.get_bool("SshEnabled"),
      callback=self._on_enable_ssh,
    )
    self._ssh_keys = ssh_key_item(lambda: tr("SSH Keys"), description=lambda: tr(DESCRIPTIONS["ssh_key"]))

    self._use_prebuilt_toggle = toggle_item(
      lambda: tr("Use Prebuilt Binaries"),
      description=lambda: tr(DESCRIPTIONS["use_prebuilt"]),
      initial_state=self._params.get_bool("UsePrebuilt"),
      callback=self._on_use_prebuilt,
      enabled=ui_state.is_offroad,
    )

    # Rebuild / Full Rebuild: recompile then reboot. Car-agnostic, always available here.
    # Only one may run at a time; _rebuild_running names which, so status lands on its own row.
    self._rebuild_running: str | None = None
    self._rebuild_status = ""
    self._rebuild_last_line = ""
    self._rebuild_item = self._make_rebuild_item("rebuild", tr_noop("Rebuild"), REBUILD_CMD)
    self._full_rebuild_item = self._make_rebuild_item("full_rebuild", tr_noop("Full Rebuild"), FULL_REBUILD_CMD)

    self._joystick_toggle = toggle_item(
      lambda: tr("Joystick Debug Mode"),
      description="",
      initial_state=self._params.get_bool("JoystickDebugMode"),
      callback=self._on_joystick_debug_mode,
      enabled=ui_state.is_offroad,
    )

    self._alpha_long_toggle = toggle_item(
      lambda: tr("openpilot Longitudinal Control (Alpha)"),
      description=lambda: tr(DESCRIPTIONS["alpha_longitudinal"]),
      initial_state=self._params.get_bool("AlphaLongitudinalEnabled"),
      callback=self._on_alpha_long_enabled,
      enabled=lambda: not ui_state.engaged,
    )

    self._ui_debug_toggle = toggle_item(
      lambda: tr("UI Debug Mode"),
      description="",
      initial_state=self._params.get_bool("ShowDebugInfo"),
      callback=self._on_enable_ui_debug,
    )
    # Only apply the param when it is set, so SHOW_FPS=1 / the debug env flags survive construction.
    if self._params.get_bool("ShowDebugInfo"):
      self._on_enable_ui_debug(True)

    self._scroller = Scroller([
      self._adb_toggle,
      self._ssh_toggle,
      self._ssh_keys,
      self._use_prebuilt_toggle,
      self._rebuild_item,
      self._full_rebuild_item,
      self._joystick_toggle,
      self._alpha_long_toggle,
      self._ui_debug_toggle,
    ], line_separator=True, spacing=0)

    # Toggles should be not available to change in onroad state
    ui_state.add_offroad_transition_callback(self._update_toggles)

  def _render(self, rect):
    self._scroller.render(rect)

  def show_event(self):
    self._scroller.show_event()
    self._update_toggles()

  def _update_toggles(self):
    ui_state.update_params()

    # CP gating
    if ui_state.CP is not None:
      alpha_avail = ui_state.CP.alphaLongitudinalAvailable
      if not alpha_avail:
        self._alpha_long_toggle.set_visible(False)
        self._params.remove("AlphaLongitudinalEnabled")
      else:
        self._alpha_long_toggle.set_visible(True)

    else:
      self._alpha_long_toggle.set_visible(False)

    # TODO: make a param control list item so we don't need to manage internal state as much here
    # refresh toggles from params to mirror external changes
    for key, item in (
      ("AdbEnabled", self._adb_toggle),
      ("SshEnabled", self._ssh_toggle),
      ("UsePrebuilt", self._use_prebuilt_toggle),
      ("JoystickDebugMode", self._joystick_toggle),
      ("AlphaLongitudinalEnabled", self._alpha_long_toggle),
      ("ShowDebugInfo", self._ui_debug_toggle),
    ):
      item.action_item.set_state(self._params.get_bool(key))

  def _on_enable_ui_debug(self, state: bool):
    self._params.put_bool("ShowDebugInfo", state)
    gui_app.set_show_touches(state)
    gui_app.set_show_fps(state)

  def _on_enable_adb(self, state: bool):
    self._params.put_bool("AdbEnabled", state)

  def _on_enable_ssh(self, state: bool):
    self._params.put_bool("SshEnabled", state)

  def _on_use_prebuilt(self, state: bool):
    self._params.put_bool("UsePrebuilt", state)

  def _make_rebuild_item(self, key: str, label: str, cmd: str):
    return button_item(
      lambda: tr(label),
      lambda: self._rebuild_status if self._rebuild_running == key else tr("BUILD"),
      description=lambda: (self._rebuild_last_line if self._rebuild_running == key and self._rebuild_last_line
                           else tr(DESCRIPTIONS[key])),
      callback=lambda: self._on_rebuild(key, cmd),
      enabled=lambda: ui_state.is_offroad() and self._rebuild_running is None,
    )

  def _on_rebuild(self, key: str, cmd: str):
    if self._rebuild_running is not None:
      return

    prompt = (tr("This will recompile everything from source, ignoring the build cache, and reboot. "
                 "Takes ~20 minutes. Continue?") if key == "full_rebuild"
              else tr("This will recompile changed code and reboot. Continue?"))

    def confirm_callback(result: int):
      if result == DialogResult.CONFIRM:
        self._start_rebuild(key, cmd)

    gui_app.push_widget(ConfirmDialog(prompt, tr("Rebuild"), callback=confirm_callback))

  def _start_rebuild(self, key: str, cmd: str):
    self._rebuild_running = key
    self._rebuild_status = tr("Cleaning...")
    self._rebuild_last_line = ""
    threading.Thread(target=self._rebuild_worker, args=(cmd,), daemon=True).start()

  def _rebuild_worker(self, cmd: str):
    # Runs off the UI thread; only touches the status strings the list item reads each frame.
    env = dict(os.environ, SCONS_PROGRESS="1")
    try:
      proc = subprocess.Popen(["bash", "-c", cmd], cwd=BASEDIR, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
      assert proc.stdout is not None
      for line in proc.stdout:
        line = line.strip()
        if line:
          self._rebuild_last_line = line
          self._rebuild_status = ("..." + line[-20:]) if len(line) > 23 else line
      exit_code = proc.wait()
    except Exception as e:
      self._rebuild_last_line = str(e)
      exit_code = -1

    if exit_code == 0:
      self._rebuild_status = "Build complete! Rebooting..."
      threading.Timer(FULL_REBUILD_REBOOT_DELAY, HARDWARE.reboot).start()
    else:
      self._rebuild_status = f"Build failed (exit {exit_code})"
      self._rebuild_running = None

  def _on_joystick_debug_mode(self, state: bool):
    self._params.put_bool("JoystickDebugMode", state)
    self._params.put_bool("LongitudinalManeuverMode", False)

  def _on_alpha_long_enabled(self, state: bool):
    if state:
      def confirm_callback(result: int):
        if result == DialogResult.CONFIRM:
          self._params.put_bool("AlphaLongitudinalEnabled", True)
          self._params.put_bool("OnroadCycleRequested", True)
          self._update_toggles()
        else:
          self._alpha_long_toggle.action_item.set_state(False)

      # show confirmation dialog
      content = (f"<h1>{self._alpha_long_toggle.title}</h1><br>" +
                 f"<p>{self._alpha_long_toggle.description}</p>")

      gui_app.push_widget(ConfirmDialog(content, tr("Enable"), rich=True, callback=confirm_callback))

    else:
      self._params.put_bool("AlphaLongitudinalEnabled", False)
      self._params.put_bool("OnroadCycleRequested", True)
      self._update_toggles()

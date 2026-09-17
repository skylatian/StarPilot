"""Screenshot tour: walk every settings page of the big UI and save one PNG per page.

Enabled by UI_SCREENSHOT_DIR (see system/ui/lib/application.py), driven from ui.py's render loop:

  UI_SCREENSHOT_DIR=/tmp/shots FINGERPRINT=TOYOTA_COROLLA_RETROFIT ./c3

Pages are reached by calling the layouts' own navigation methods, not by clicking, so a page
shows exactly what a user would land on (top of the page, no scroll). Each PNG gets a sibling
NNN_<name>.text.json with every text draw of that exact frame (see scripts/ui_text_lint.py). After the pages, one sample
of each dialog type is opened over a representative page (never confirmed).
Optional UI_SCREENSHOT_FILTER=substr keeps only pages whose name contains substr.
"""
import json
import os
import re
import time
from collections.abc import Callable, Iterator

from openpilot.common.swaglog import cloudlog
from openpilot.system.ui.lib.application import gui_app

SETTLE_SECONDS = float(os.getenv("UI_SCREENSHOT_SETTLE", "0.8"))

# Sub-pages that are only built when their tile is tapped: (panel key, builder method, args).
LAZY_SUB_PAGES = [
  ("LONGITUDINAL", "_show_slc_offsets_category", ()),
  *[("LONGITUDINAL", "_show_personality_profile_category", (p,)) for p in ("Traffic", "Aggressive", "Standard", "Relaxed")],
  *[("LONGITUDINAL", "_show_weather_offsets_category", args) for args in
    (("LowVisibility", "Low Visibility"), ("Rain", "Rain"), ("RainStorm", "Rainstorms"), ("Snow", "Snow"))],  # titles as in longitudinal.py
]

Step = tuple[str, Callable[[], None]]


def _slug(name: str) -> str:
  return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _steps(main_layout) -> Iterator[Step]:
  from openpilot.selfdrive.ui.layouts.settings.settings import PanelType
  from openpilot.selfdrive.ui.layouts.settings.starpilot.main_panel import StarPilotLayout, StarPilotPanelType

  yield "home", lambda: main_layout._set_mode_for_state()

  for panel_type in PanelType:
    yield f"settings/{panel_type.name}", lambda pt=panel_type: main_layout.open_settings(pt)

  main_layout.open_settings(PanelType.STARPILOT)
  sp: StarPilotLayout = StarPilotLayout.active_instance

  # Hub folders (e.g. Driving Controls -> Navigation & Maps).
  def folders(nodes: list[dict], path: list[dict]) -> Iterator[Step]:
    for node in nodes:
      if "children" not in node:
        continue
      trail = path + [node]

      def open_trail(trail=trail):
        sp.reset_to_root()
        for folder in trail:
          sp._open_folder(folder)
      yield "starpilot/" + "/".join(_slug(f["title"]) for f in trail), open_trail
      yield from folders(node["children"], trail)

  yield from folders(sp.CATEGORIES, [])

  # Open a panel the way a tap does: through its hub folders, with the real leaf node (breadcrumbs read it).
  leaves: dict[str, tuple[list[dict], dict]] = {}

  def find_leaves(nodes: list[dict], path: list[dict]) -> None:
    for node in nodes:
      if "children" in node:
        find_leaves(node["children"], path + [node])
      elif "panel" in node:
        leaves.setdefault(node["panel"], (path, node))
  find_leaves(sp.CATEGORIES, [])

  def open_leaf(key: str) -> None:
    trail, leaf = leaves[key]
    sp.reset_to_root()
    for folder in trail:
      sp._open_folder(folder)
    sp._open_leaf(leaf)

  for key, sp_type in sp.PANEL_TYPE_MAP.items():
    if key not in leaves or (key == "RETROFIT" and not sp._is_retrofit):
      continue
    panel = sp._panels[sp_type].instance

    def open_panel(key=key):
      open_leaf(key)
    yield f"starpilot/{key.lower()}", open_panel

    for sub_name in list(getattr(panel, "_sub_panels", {})):
      def open_sub(open_panel=open_panel, panel=panel, sub_name=sub_name):
        open_panel()
        panel._navigate_to(sub_name)
      yield f"starpilot/{key.lower()}/{sub_name}", open_sub

  for key, method, args in LAZY_SUB_PAGES:
    panel = sp._panels[StarPilotPanelType[key]].instance
    if not hasattr(panel, method):
      continue

    def open_lazy(key=key, panel=panel, method=method, args=args):
      open_leaf(key)
      getattr(panel, method)(*args)
    yield f"starpilot/{key.lower()}/{_slug(method.removeprefix('_show_').removesuffix('_category'))}_{_slug(args[0]) if args else ''}".rstrip("_"), open_lazy

  yield from _dialog_steps(main_layout, sp, open_leaf)

  # Leave the UI where it started.
  yield "", lambda: (sp.reset_to_root(), main_layout._set_mode_for_state())


def _dialog_steps(main_layout, sp, open_leaf: Callable[[str], None]) -> Iterator[Step]:
  """One sample of each dialog type, opened over a representative page. Nothing is confirmed, so no params change."""
  import os as _os
  from openpilot.common.basedir import BASEDIR
  from openpilot.selfdrive.ui.layouts.onboarding import TrainingGuide
  from openpilot.selfdrive.ui.layouts.settings.device import GalaxyQRDialog
  from openpilot.selfdrive.ui.layouts.settings.settings import PanelType
  from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import AetherSliderDialog
  from openpilot.selfdrive.ui.layouts.settings.starpilot.main_panel import StarPilotPanelType
  from openpilot.selfdrive.ui.layouts.settings.starpilot.system_settings import AetherBackupsCareDialog
  from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog, alert_dialog
  from openpilot.system.ui.widgets.html_render import HtmlModal
  from openpilot.system.ui.lib.application import FontWeight
  from openpilot.system.ui.lib.multilang import multilang
  from openpilot.system.ui.widgets.keyboard import Keyboard
  from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog

  panel = lambda t: sp._panels[t].instance  # noqa: E731

  def over_device(push):
    def action():
      main_layout.open_settings(PanelType.DEVICE)
      push()
    return action

  def over_panel(key: str, push):
    def action():
      main_layout.open_settings(PanelType.STARPILOT)
      open_leaf(key)
      push()
    return action

  def keyboard():
    kb = Keyboard(min_text_size=6, password_mode=True, show_password_toggle=True)
    kb.set_title("Set Galaxy Password", "Set a password to secure your Galaxy access. Min 6 characters.")
    gui_app.push_widget(kb)

  yield "dialog/confirm", over_device(lambda: gui_app.push_widget(
    ConfirmDialog("Are you sure you want to reset calibration?", "Reset")))
  yield "dialog/confirm_rich", over_panel("DRIVING_MODEL", lambda: gui_app.push_widget(ConfirmDialog(
    "<h1>Experimental Mode</h1><br><p>openpilot defaults to driving in chill mode. Experimental mode enables alpha-level "
    "features that aren't ready for chill mode. Experimental features are listed below.</p>", "Enable", rich=True)))
  yield "dialog/alert", over_panel("DRIVING_MODEL", lambda: gui_app.push_widget(
    alert_dialog("Cannot download models while driving.")))
  yield "dialog/option_long_list", over_device(lambda: gui_app.push_widget(
    MultiOptionDialog("Select a language", list(multilang.languages), next(iter(multilang.languages)), option_font_weight=FontWeight.UNIFONT)))
  yield "dialog/option_short_list", over_panel("LONGITUDINAL", panel(StarPilotPanelType.LONGITUDINAL)._show_acceleration_profile_selector)
  yield "dialog/option_colors", over_panel("VISUALS", lambda: panel(StarPilotPanelType.VISUALS)._show_color_selector("LaneLinesColor"))
  yield "dialog/slider", over_panel("LONGITUDINAL", lambda: gui_app.push_widget(AetherSliderDialog(
    "Below Speed", 0, 100, 1, 35, lambda *_: None, presets=[0, 20, 35, 55, 75], unit=" mph")))
  yield "dialog/keyboard", over_device(keyboard)
  yield "dialog/button_combo", over_panel("VEHICLE", lambda: panel(StarPilotPanelType.VEHICLE)._show_button_combo_dialog("combo:distance"))
  yield "dialog/action_picker", over_panel("VEHICLE", lambda: panel(StarPilotPanelType.VEHICLE)._show_action_picker("LKASButtonControl"))
  yield "dialog/galaxy_qr", over_device(lambda: gui_app.push_widget(GalaxyQRDialog("https://galaxy.firestar.link/example")))
  yield "dialog/html_modal", over_device(lambda: gui_app.push_widget(
    HtmlModal(_os.path.join(BASEDIR, "selfdrive/assets/offroad/fcc.html"))))
  yield "dialog/training_guide", over_device(lambda: gui_app.push_widget(TrainingGuide(completed_callback=gui_app.pop_widget)))
  yield "dialog/backups_care", over_panel("SYSTEM", lambda: gui_app.push_widget(
    AetherBackupsCareDialog(panel(StarPilotPanelType.SYSTEM))))
  yield "dialog/download_manager", over_panel("VISUALS", panel(StarPilotPanelType.VISUALS)._show_boot_logo_manager)


class ScreenshotTour:
  def __init__(self, main_layout, out_dir: str):
    self._out_dir = out_dir
    self._filter = os.getenv("UI_SCREENSHOT_FILTER", "")
    self._steps = _steps(main_layout)
    # UI debug mode (ShowDebugInfo param) outlines every widget in red and draws an FPS counter; keep it out of review shots.
    gui_app.set_show_touches(False)
    gui_app.set_show_fps(False)
    self._index = 0
    self._shot_at = 0.0
    self._path: str | None = None
    self._logging = False
    self.done = False
    self.saved: list[str] = []
    os.makedirs(out_dir, exist_ok=True)

  def _advance(self) -> None:
    for name, action in self._steps:
      if name and self._filter and self._filter not in name:
        continue
      try:
        if len(gui_app._nav_stack) > 1:
          gui_app.pop_widgets_to(gui_app._nav_stack[0], instant=True)
        action()
      except Exception:
        cloudlog.exception(f"screenshot tour: failed to open {name!r}")
        print(f"screenshot tour: FAILED to open {name}")
        continue
      if not name:
        continue
      self._index += 1
      self._path = os.path.join(self._out_dir, f"{self._index:03d}_{name.replace('/', '__')}.png")
      self._shot_at = time.monotonic() + SETTLE_SECONDS
      return
    self.done = True

  def update(self) -> None:
    """Call once per rendered frame."""
    if self.done or gui_app.screenshot_pending():
      return
    if self._path is None:
      self._advance()
      return
    if time.monotonic() < self._shot_at:
      return
    if not self._logging:
      # Record text draws of the next frame; that same frame is the one captured below.
      gui_app.start_text_log()
      self._logging = True
      return
    self._logging = False
    with open(self._path.removesuffix(".png") + ".text.json", "w") as f:
      json.dump(gui_app.take_text_log(), f, indent=0, ensure_ascii=False)
    gui_app.request_screenshot(self._path)
    self.saved.append(self._path)
    print(f"screenshot tour: {self._path}")
    self._path = None

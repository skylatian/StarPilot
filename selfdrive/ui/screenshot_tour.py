"""Screenshot tour: walk every settings page of the big UI and save one PNG per page.

Enabled by UI_SCREENSHOT_DIR (see system/ui/lib/application.py), driven from ui.py's render loop:

  UI_SCREENSHOT_DIR=/tmp/shots FINGERPRINT=TOYOTA_COROLLA_RETROFIT ./c3

Pages are reached by calling the layouts' own navigation methods, not by clicking, so a page
shows exactly what a user would land on (top of the page, no scroll, no dialog open).
Optional UI_SCREENSHOT_FILTER=substr keeps only pages whose name contains substr.
"""
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
  *[("LONGITUDINAL", "_show_weather_offsets_category", (s, s)) for s in ("LowVisibility", "Rain", "RainStorm", "Snow")],
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

  # Leave the UI where it started.
  yield "", lambda: (sp.reset_to_root(), main_layout._set_mode_for_state())


class ScreenshotTour:
  def __init__(self, main_layout, out_dir: str):
    self._out_dir = out_dir
    self._filter = os.getenv("UI_SCREENSHOT_FILTER", "")
    self._steps = _steps(main_layout)
    self._index = 0
    self._shot_at = 0.0
    self._path: str | None = None
    self.done = False
    self.saved: list[str] = []
    os.makedirs(out_dir, exist_ok=True)

  def _advance(self) -> None:
    for name, action in self._steps:
      if name and self._filter and self._filter not in name:
        continue
      try:
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
    if time.monotonic() >= self._shot_at:
      gui_app.request_screenshot(self._path)
      self.saved.append(self._path)
      print(f"screenshot tour: {self._path}")
      self._path = None

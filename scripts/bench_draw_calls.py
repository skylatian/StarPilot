#!/usr/bin/env python3
"""Count raylib draw calls per frame for a settings page.

The 2026-09-17 freeze investigation caught the UI stalled 5.2s inside
rl.draw_circle() in an AetherGrid tile background. That is a GPU submit point,
so the question this answers is: how many submits does one frame of that page
actually make? Draw-call count is platform independent -- unlike wall-clock on
the Mac, it is the same number the C3 executes.

  ./dev python scripts/bench_draw_calls.py [page]

page: starpilot (default) | home | device
"""
import os
import sys
import collections

os.environ.setdefault("SCALE", "0.5")

import pyray as rl

COUNTS: collections.Counter = collections.Counter()
_ENABLED = [False]

# Every raylib entry point that submits geometry. Anything not wrapped here is
# invisible to the count, so keep this list in sync with what the UI actually calls.
WRAPPED = [
  "draw_rectangle", "draw_rectangle_rec", "draw_rectangle_pro", "draw_rectangle_lines",
  "draw_rectangle_lines_ex", "draw_rectangle_rounded", "draw_rectangle_rounded_lines",
  "draw_rectangle_rounded_lines_ex", "draw_rectangle_gradient_v", "draw_rectangle_gradient_h",
  "draw_circle", "draw_circle_v", "draw_circle_lines", "draw_circle_sector", "draw_ring",
  "draw_line", "draw_line_ex", "draw_line_v", "draw_triangle", "draw_poly",
  "draw_texture", "draw_texture_v", "draw_texture_ex", "draw_texture_pro", "draw_texture_npatch",
  "draw_text", "draw_text_ex",
]


def _install():
  for name in WRAPPED:
    orig = getattr(rl, name, None)
    if orig is None:
      continue

    def make(n, f):
      def wrapper(*a, **k):
        if _ENABLED[0]:
          COUNTS[n] += 1
        return f(*a, **k)
      return wrapper
    setattr(rl, name, make(name, orig))


_install()

from openpilot.system.ui.lib.application import gui_app


def main():
  page = sys.argv[1] if len(sys.argv) > 1 else "starpilot"
  gui_app.init_window("bench")

  from openpilot.selfdrive.ui.layouts.main import MainLayout
  from openpilot.selfdrive.ui.layouts.settings.settings import PanelType

  layout = MainLayout()
  # MainState.SETTINGS lives on the layout; drive it through the layout's own API
  from openpilot.selfdrive.ui.layouts.main import MainState
  layout._current_mode = MainState.SETTINGS
  settings = layout._layouts[MainState.SETTINGS]

  if page == "starpilot":
    settings.set_current_panel(PanelType.STARPILOT)
  elif page == "device":
    settings.set_current_panel(PanelType.DEVICE)

  frames = []
  n = 0
  for _ in gui_app.render():
    n += 1
    if n < 15:          # let layout/animation settle before counting
      COUNTS.clear()
      continue
    COUNTS.clear()
    _ENABLED[0] = True
    layout.render(rl.Rectangle(0, 0, gui_app.width, gui_app.height))
    _ENABLED[0] = False
    frames.append(sum(COUNTS.values()))
    if n >= 45:
      break

  total = sorted(COUNTS.items(), key=lambda kv: -kv[1])
  print(f"\n=== page: {page} ===")
  print(f"draw calls per frame: min={min(frames)} max={max(frames)} median={sorted(frames)[len(frames)//2]}")
  print("\nlast frame, by primitive:")
  for k, v in total:
    if v:
      print(f"  {v:6d}  {k}")
  gui_app.request_close()


if __name__ == "__main__":
  main()

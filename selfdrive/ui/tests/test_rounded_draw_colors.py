import pyray as rl
import pytest

from openpilot.selfdrive.ui.layouts.settings.starpilot import aethergrid


@pytest.fixture
def drawn(monkeypatch):
  calls = []
  monkeypatch.setattr(aethergrid.rl, "draw_rectangle_rounded", lambda rect, roundness, segments, color: calls.append(color))
  monkeypatch.setattr(aethergrid.rl, "draw_rectangle_rounded_lines_ex", lambda *args: calls.append(args[-1]), raising=False)
  monkeypatch.setattr(aethergrid.rl, "draw_rectangle_rounded_lines", lambda *args: calls.append(args[-1]), raising=False)
  return calls


# pyray's named colors are plain tuples, not rl.Color: the slider dialog draws its thumb with
# rl.WHITE, and reading .a off it crashed the UI whenever any slider dialog opened.
@pytest.mark.parametrize("color", [rl.WHITE, (255, 255, 255, 255), rl.Color(255, 255, 255, 255)])
@pytest.mark.parametrize("draw", [aethergrid.draw_rounded_fill, aethergrid.draw_rounded_stroke])
def test_rounded_draws_accept_tuple_and_struct_colors(drawn, draw, color):
  draw(rl.Rectangle(0, 0, 46, 93), color, radius_px=23)
  assert drawn, "an opaque color must be drawn"


@pytest.mark.parametrize("color", [(255, 255, 255, 0), rl.Color(255, 255, 255, 0)])
@pytest.mark.parametrize("draw", [aethergrid.draw_rounded_fill, aethergrid.draw_rounded_stroke])
def test_rounded_draws_skip_transparent_colors(drawn, draw, color):
  draw(rl.Rectangle(0, 0, 46, 93), color, radius_px=23)
  assert drawn == []

from __future__ import annotations

import math
from dataclasses import dataclass

import pyray as rl

from openpilot.common.params import Params
from openpilot.system.ui.lib.application import FontWeight, gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import DialogResult, Widget
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog

from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import _SettingsPage
from openpilot.selfdrive.ui.layouts.settings.starpilot.aethergrid import (
  AetherListColors,
  AetherSettingsView,
  AetherSliderDialog,
  DEFAULT_PANEL_STYLE,
  SettingRow,
  SettingSection,
  draw_rounded_fill,
  draw_rounded_stroke,
  format_adjustor_value,
)


# ═══════════════════════════════════════════════════════════════
# Tune parameter specs
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TuneParam:
  key: str
  label: str
  default: float
  min: float
  max: float
  step: float
  desc: str


NONLINEAR_PARAMS = [
  TuneParam("RetrofitNonlinearStrength", tr_noop("Sigmoid Strength"), 0.0, 0.0, 1.0, 0.05,
            tr_noop("Blend between linear (0) and full sigmoid (1). Increase if the wheel oscillates or whips back in turns; " +
                    "decrease if steering feels sluggish entering corners. At 0, behavior is identical to stock linear.")),
  TuneParam("RetrofitNonlinearSaturation", tr_noop("Saturation"), 2.5, 0.5, 5.0, 0.1,
            tr_noop("How quickly the torque curve flattens at large inputs. Increase if oscillation only happens in sharp turns; " +
                    "decrease if the car understeers mid-corner.")),
  TuneParam("RetrofitNonlinearBias", tr_noop("L/R Bias"), 0.0, -1.0, 1.0, 0.05,
            tr_noop("Compensate for asymmetric EPS response. Positive = more torque going left, negative = more going right.")),
]

ABCD_PARAMS = [
  TuneParam("RetrofitNonlinearLeftA", tr_noop("Left A (steepness)"), 2.5, 0.1, 8.0, 0.1,
            tr_noop("Sigmoid steepness for left turns. Higher = saturates sooner.")),
  TuneParam("RetrofitNonlinearLeftB", tr_noop("Left B (amplitude)"), 1.0, 0.0, 3.0, 0.05,
            tr_noop("Sigmoid amplitude for left turns. Higher = more nonlinear contribution.")),
  TuneParam("RetrofitNonlinearLeftC", tr_noop("Left C (linear)"), 0.2, 0.0, 1.0, 0.01,
            tr_noop("Linear slope for left turns. The unsaturated floor of response.")),
  TuneParam("RetrofitNonlinearLeftD", tr_noop("Left D (offset)"), 0.0, -0.2, 0.2, 0.01,
            tr_noop("Constant offset for left turns. Usually 0.")),
  TuneParam("RetrofitNonlinearRightA", tr_noop("Right A (steepness)"), 2.5, 0.1, 8.0, 0.1,
            tr_noop("Sigmoid steepness for right turns. Higher = saturates sooner.")),
  TuneParam("RetrofitNonlinearRightB", tr_noop("Right B (amplitude)"), 1.0, 0.0, 3.0, 0.05,
            tr_noop("Sigmoid amplitude for right turns. Higher = more nonlinear contribution.")),
  TuneParam("RetrofitNonlinearRightC", tr_noop("Right C (linear)"), 0.2, 0.0, 1.0, 0.01,
            tr_noop("Linear slope for right turns. The unsaturated floor of response.")),
  TuneParam("RetrofitNonlinearRightD", tr_noop("Right D (offset)"), 0.0, -0.2, 0.2, 0.01,
            tr_noop("Constant offset for right turns. Usually 0.")),
]

FF_PARAMS = [
  TuneParam("RetrofitTuneFFGain", tr_noop("FF Gain"), 0.0, 0.0, 0.5, 0.01,
            tr_noop("How much extra steering effort to add in the boost zone. Higher = more aggressive mid-corner steering. 0 = no boost.")),
  TuneParam("RetrofitTuneFFOnset", tr_noop("FF Onset"), 0.18, 0.0, 2.0, 0.02,
            tr_noop("How hard you need to be turning before the boost kicks in. Lower = starts in gentler curves.")),
  TuneParam("RetrofitTuneFFOnsetWidth", tr_noop("Onset Width"), 0.08, 0.01, 1.0, 0.01,
            tr_noop("How gradually the boost ramps in. Smaller = snaps on quickly, larger = fades in smoothly.")),
  TuneParam("RetrofitTuneFFCutoff", tr_noop("FF Cutoff"), 1.10, 0.1, 3.0, 0.05,
            tr_noop("How hard you need to be turning before the boost fades out. Higher = stays active into sharper turns.")),
  TuneParam("RetrofitTuneFFCutoffWidth", tr_noop("Cutoff Width"), 0.30, 0.01, 2.0, 0.05,
            tr_noop("How gradually the boost fades at the cutoff. Smaller = drops off abruptly, larger = tapers out gradually.")),
]

TURN_PARAMS = [
  TuneParam("RetrofitTuneUnwindBoost", tr_noop("Unwind Boost"), 0.0, 0.0, 1.0, 0.05,
            tr_noop("Actively pushes the wheel back toward center when exiting a turn, for cars with weak self-centering. " +
                    "Start at 0.15-0.30 and increase if the car still feels lazy returning to straight.")),
  TuneParam("RetrofitTuneUnwindTaper", tr_noop("Unwind Taper"), 0.0, 0.0, 1.0, 0.05,
            tr_noop("How much to back off steering when straightening out. Higher = pulls back more, preventing overshoot past center. " +
                    "Too high can make turn exits feel jerky.")),
  TuneParam("RetrofitTuneTurnInBoost", tr_noop("Turn-In Boost"), 0.0, 0.0, 1.0, 0.05,
            tr_noop("Extra steering effort when initiating a turn. 0 = none (default for dual PS). Increase if the car feels sluggish entering curves.")),
  TuneParam("RetrofitTuneTransitionSpeed", tr_noop("Transition Speed"), 10.0, 1.0, 30.0, 1.0,
            tr_noop("Speed (m/s) below which the turn dynamics effects are strongest; above it they gradually fade. 10 = ~22 mph.")),
  TuneParam("RetrofitTunePhaseScale", tr_noop("Phase Scale"), 0.10, 0.01, 1.0, 0.01,
            tr_noop("How quickly the system detects you are entering or exiting a turn. Smaller = reacts to smaller steering changes.")),
  TuneParam("RetrofitTuneFrictionLatRise", tr_noop("Friction Lat Rise"), 0.20, 0.01, 2.0, 0.02,
            tr_noop("How much turning activates the friction adjustments. Smaller = even gentle curves, larger = only harder turns.")),
  TuneParam("RetrofitTuneFrictionJerkRise", tr_noop("Friction Jerk Rise"), 0.24, 0.01, 2.0, 0.02,
            tr_noop("How much a sudden steering change activates the friction adjustments. Smaller = quick flicks count, larger = only sustained turning.")),
  TuneParam("RetrofitTuneTurnInThresholdReduction", tr_noop("TI Thresh. Reduction"), 0.0, 0.0, 0.5, 0.02,
            tr_noop("Adds extra resistance when entering a turn, helping the wheel hold its position. Useful if the wheel feels loose when starting to turn.")),
  TuneParam("RetrofitTuneUnwindThresholdIncrease", tr_noop("UW Thresh. Increase"), 0.0, 0.0, 1.0, 0.05,
            tr_noop("Reduces resistance when straightening out, letting the wheel return freely. Useful if the wheel feels sticky returning to center.")),
  TuneParam("RetrofitTuneTurnInFrictionBoost", tr_noop("TI Friction Boost"), 0.0, 0.0, 0.5, 0.01,
            tr_noop("Extra friction compensation when entering turns. Increase if the car understeers slightly at the start of turns.")),
  TuneParam("RetrofitTuneUnwindFrictionReduction", tr_noop("UW Friction Reduction"), 0.0, 0.0, 1.0, 0.05,
            tr_noop("Less friction compensation when straightening out. Increase if the car overshoots when exiting turns.")),
]

CENTER_PARAMS = [
  TuneParam("RetrofitTuneCenterTaperMax", tr_noop("Taper Max"), 0.0, 0.0, 0.5, 0.02,
            tr_noop("How much to reduce steering when going mostly straight. 0 = disabled, 0.20 = 20% quieter. Increase if you see jitter on highways.")),
  TuneParam("RetrofitTuneCenterTaperLat", tr_noop("Lat Threshold"), 0.14, 0.01, 1.0, 0.02,
            tr_noop("How far from perfectly straight the taper still applies. Higher = stays active during gentle curves.")),
  TuneParam("RetrofitTuneCenterTaperLatWidth", tr_noop("Lat Width"), 0.04, 0.01, 0.5, 0.01,
            tr_noop("How gradually the taper blends in/out as you start turning. Smaller = sharp cutoff, larger = smooth transition.")),
  TuneParam("RetrofitTuneCenterTaperSpeed", tr_noop("Speed Threshold"), 14.0, 1.0, 35.0, 1.0,
            tr_noop("Speed above which the taper activates (m/s). 14 = ~31 mph.")),
  TuneParam("RetrofitTuneCenterTaperSpeedWidth", tr_noop("Speed Width"), 2.5, 0.1, 10.0, 0.5,
            tr_noop("How gradually the taper ramps in as you speed up. Smaller = snaps on at the threshold, larger = fades in over a wider range.")),
]


@dataclass(frozen=True)
class KPPoint:
  speed: float
  key: str
  default: float
  y_min: float
  y_max: float


# Mirrors KP_INTERP / RETROFIT_KP_INTERP_DEFAULTS in latcontrol_torque.py (baked at init, offroad only).
KP_POINTS = [
  KPPoint(1.0, "RetrofitTuneKP1", 250.0, 0.1, 300.0),
  KPPoint(1.5, "RetrofitTuneKP1_5", 120.0, 0.1, 200.0),
  KPPoint(2.0, "RetrofitTuneKP2", 65.0, 0.1, 150.0),
  KPPoint(3.0, "RetrofitTuneKP3", 30.0, 0.1, 100.0),
  KPPoint(5.0, "RetrofitTuneKP5", 11.5, 0.1, 50.0),
  KPPoint(7.5, "RetrofitTuneKP7_5", 5.5, 0.1, 30.0),
  KPPoint(10.0, "RetrofitTuneKP10", 3.5, 0.1, 20.0),
  KPPoint(15.0, "RetrofitTuneKP15", 2.0, 0.1, 10.0),
  KPPoint(30.0, "RetrofitTuneKP30", 0.6, 0.1, 5.0),
]


# ═══════════════════════════════════════════════════════════════
# Math (mirrors opendbc/car/toyota/interface.py and latcontrol_vehicle_tunes.py)
# ═══════════════════════════════════════════════════════════════

RETROFIT_BASE_LAT_ACCEL_FACTOR = 4.05


def _sigmoid(x: float) -> float:
  if x >= 0:
    z = math.exp(-x)
    return 1.0 / (1.0 + z)
  z = math.exp(x)
  return z / (1.0 + z)


def user_params_to_abcd(strength: float, saturation: float, bias: float) -> tuple[list[float], list[float]]:
  """Same conversion as interface.py:_user_params_to_abcd — kept local so the UI does not import car code."""
  linear_slope = 1.0 / RETROFIT_BASE_LAT_ACCEL_FACTOR
  c_floor = 0.05
  b_base = 1.0 * strength
  c_base = linear_slope * (1.0 - strength) + c_floor * strength
  left = [saturation, b_base * (1.0 + bias * 0.3), c_base, 0.0]
  right = [saturation, b_base * (1.0 - bias * 0.3), c_base, 0.0]
  return left, right


def siglin_torque(lat_accel: float, left: list[float], right: list[float]) -> float:
  a, b, c, d = left if lat_accel >= 0 else right
  sig_input = a * lat_accel
  sig = math.copysign(_sigmoid(abs(sig_input)) - 0.5, sig_input) if sig_input != 0 else 0.0
  return (sig * b) + (lat_accel * c) + d


def ff_window_scale(lat_accel: float, gain: float, onset: float, onset_w: float, cutoff: float, cutoff_w: float) -> float:
  onset_weight = _sigmoid((lat_accel - onset) / max(onset_w, 0.01))
  cutoff_weight = _sigmoid((cutoff - lat_accel) / max(cutoff_w, 0.01))
  return 1.0 + gain * onset_weight * cutoff_weight


def turn_dynamics_multiplier(phase: float, turn_in_boost: float, unwind_boost: float, unwind_taper: float) -> float:
  turn_in_weight = max(phase, 0.0)
  unwind_weight = max(-phase, 0.0)
  boost = 1.0 + (turn_in_boost * turn_in_weight)
  taper = 1.0 - (unwind_taper * unwind_weight)
  return boost * max(taper, 0.0) + unwind_boost * unwind_weight


def center_taper_scale(lat_accel: float, v_ego: float, taper_max: float, lat: float, lat_w: float, speed: float, speed_w: float) -> float:
  speed_weight = _sigmoid((v_ego - speed) / max(speed_w, 0.1))
  center_weight = _sigmoid((lat - abs(lat_accel)) / max(lat_w, 0.01))
  return 1.0 - taper_max * speed_weight * center_weight


# ═══════════════════════════════════════════════════════════════
# Plot widgets
# ═══════════════════════════════════════════════════════════════

_PLOT_BG = rl.Color(16, 16, 20, 255)
_GRID = rl.Color(255, 255, 255, 18)
_REFERENCE = rl.Color(255, 255, 255, 40)
_CURVE = rl.Color(0x58, 0xD6, 0x8D, 255)
_STOCK = rl.Color(140, 140, 150, 255)
_MARK_A = rl.Color(120, 120, 220, 255)
_MARK_B = rl.Color(220, 110, 110, 255)
_MARK_C = rl.Color(210, 200, 100, 255)
_DRAG = rl.Color(0xFF, 0xA5, 0x00, 255)
_CURVE_SAMPLES = 140


class _PlotWidget(Widget):
  """Rounded panel with a plot area, axis helpers, and per-page math in ``_draw_plot``.

  Subclasses implement ``reload()`` (re-read Params) and ``_draw_plot(plot)``.
  Axes may be linear or log10 (``log_x`` / ``log_y``).
  """

  PAD_L, PAD_R, PAD_T, PAD_B = 74, 26, 22, 70
  AXIS_TITLE_DY = 40  # below the tick labels (drawn at +8, ~25 px tall after FONT_SCALE)
  x_min, x_max, y_min, y_max = 0.0, 1.0, 0.0, 1.0
  log_x = False
  log_y = False

  def __init__(self):
    super().__init__()
    self._plot = rl.Rectangle(0, 0, 0, 0)
    self._font = None
    self._font_bold = None

  def reload(self):
    """Re-read Params. Called on show and after every edit."""

  def show_event(self):
    super().show_event()
    self.reload()

  # ── coordinate helpers ──

  def _fonts(self):
    if self._font is None:
      self._font = gui_app.font(FontWeight.NORMAL)
      self._font_bold = gui_app.font(FontWeight.BOLD)
    return self._font, self._font_bold

  def _norm(self, value: float, lo: float, hi: float, log: bool) -> float:
    if log:
      value, lo, hi = math.log10(max(value, 1e-9)), math.log10(lo), math.log10(hi)
    return (value - lo) / (hi - lo)

  def sx(self, x: float) -> float:
    return self._plot.x + self._norm(x, self.x_min, self.x_max, self.log_x) * self._plot.width

  def sy(self, y: float) -> float:
    return self._plot.y + (1.0 - self._norm(y, self.y_min, self.y_max, self.log_y)) * self._plot.height

  def y_from_screen(self, sy: float) -> float:
    frac = 1.0 - (sy - self._plot.y) / max(self._plot.height, 1.0)
    if self.log_y:
      lo, hi = math.log10(self.y_min), math.log10(self.y_max)
      return 10 ** (lo + frac * (hi - lo))
    return self.y_min + frac * (self.y_max - self.y_min)

  # ── drawing helpers ──

  def _text(self, text: str, x: float, y: float, size: int = 20, color: rl.Color = AetherListColors.MUTED, bold: bool = False, center: bool = False):
    font, font_bold = self._fonts()
    f = font_bold if bold else font
    if center:
      x -= measure_text_cached(f, text, size).x / 2
    rl.draw_text_ex(f, text, rl.Vector2(round(x), round(y)), size, 0, color)

  def _line(self, x0: float, y0: float, x1: float, y1: float, color: rl.Color, thick: float = 1.0):
    rl.draw_line_ex(rl.Vector2(x0, y0), rl.Vector2(x1, y1), thick, color)

  def _dashed(self, x0: float, y0: float, x1: float, y1: float, color: rl.Color, thick: float = 1.0, dash: float = 10.0):
    length = math.hypot(x1 - x0, y1 - y0)
    if length <= 0:
      return
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    pos = 0.0
    while pos < length:
      end = min(pos + dash, length)
      self._line(x0 + ux * pos, y0 + uy * pos, x0 + ux * end, y0 + uy * end, color, thick)
      pos += dash * 2

  def _polyline(self, points: list[tuple[float, float]], color: rl.Color, thick: float = 3.0):
    for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
      self._line(x0, y0, x1, y1, color, thick)

  def _curve(self, fn, color: rl.Color = _CURVE, thick: float = 3.0, samples: int = _CURVE_SAMPLES):
    """Plot y = fn(x) across the x range, clipped to the plot area vertically."""
    pts = []
    for i in range(samples + 1):
      frac = i / samples
      if self.log_x:
        x = 10 ** (math.log10(self.x_min) + frac * (math.log10(self.x_max) - math.log10(self.x_min)))
      else:
        x = self.x_min + frac * (self.x_max - self.x_min)
      y = min(max(self.sy(fn(x)), self._plot.y), self._plot.y + self._plot.height)
      pts.append((self.sx(x), y))
    self._polyline(pts, color, thick)

  def _grid_x(self, values: list[float], labels: list[str] | None = None):
    plot = self._plot
    for i, v in enumerate(values):
      x = self.sx(v)
      self._line(x, plot.y, x, plot.y + plot.height, _GRID)
      if labels is not None:
        self._text(labels[i], x, plot.y + plot.height + 8, 20, center=True)

  def _grid_y(self, values: list[float], labels: list[str] | None = None):
    plot = self._plot
    for i, v in enumerate(values):
      y = self.sy(v)
      self._line(plot.x, y, plot.x + plot.width, y, _GRID)
      if labels is not None:
        font, _ = self._fonts()
        w = measure_text_cached(font, labels[i], 20).x
        self._text(labels[i], plot.x - 10 - w, y - 11, 20)

  def _arrow(self, tip_x: float, y: float, direction: int, color: rl.Color, size: float = 12.0):
    """Filled triangle pointing left (direction=-1) or right (+1) with its tip at tip_x."""
    base_x = tip_x - direction * size
    top, bottom = rl.Vector2(base_x, y - size / 2), rl.Vector2(base_x, y + size / 2)
    tip = rl.Vector2(tip_x, y)
    # raylib wants counter-clockwise vertex order
    if direction > 0:
      rl.draw_triangle(top, bottom, tip, color)
    else:
      rl.draw_triangle(top, tip, bottom, color)

  def _axis_title(self, text: str):
    plot = self._plot
    self._text(text, plot.x + plot.width / 2, plot.y + plot.height + self.AXIS_TITLE_DY, 18, center=True)

  def _legend(self, items: list[tuple[str, rl.Color, bool]], x: float | None = None, y: float | None = None):
    """items: (label, color, dashed)."""
    plot = self._plot
    x = plot.x + 14 if x is None else x
    y = plot.y + 12 if y is None else y
    font, _ = self._fonts()
    for label, color, dashed in items:
      if dashed:
        self._dashed(x, y + 8, x + 28, y + 8, color, 2.0, 6.0)
      else:
        self._line(x, y + 8, x + 28, y + 8, color, 3.0)
      self._text(label, x + 36, y - 2, 18, AetherListColors.SUBTEXT)
      x += 36 + measure_text_cached(font, label, 18).x + 26

  # ── render ──

  def _render(self, rect: rl.Rectangle):
    draw_rounded_fill(rect, AetherListColors.PANEL_BG, radius_px=26)
    draw_rounded_stroke(rect, AetherListColors.PANEL_BORDER, radius_px=26)
    self._plot = rl.Rectangle(rect.x + self.PAD_L, rect.y + self.PAD_T,
                              max(rect.width - self.PAD_L - self.PAD_R, 1.0),
                              max(rect.height - self.PAD_T - self.PAD_B, 1.0))
    rl.draw_rectangle_rec(self._plot, _PLOT_BG)
    self._draw_plot(self._plot)

  def _draw_plot(self, plot: rl.Rectangle):
    raise NotImplementedError


class SigmoidCurvePreview(_PlotWidget):
  """Torque vs. lateral accel for the sigmoid-linear model, against the stock linear line."""

  x_min, x_max, y_min, y_max = -3.0, 3.0, -0.8, 0.8

  def __init__(self):
    super().__init__()
    self._left, self._right = user_params_to_abcd(0.0, 2.5, 0.0)
    self._advanced = False

  def reload(self):
    p = Params()
    self._advanced = p.get_bool("RetrofitNonlinearAdvanced")
    if self._advanced:
      self._left = [p.get_float(k, default=d) for k, d in (("RetrofitNonlinearLeftA", 2.5), ("RetrofitNonlinearLeftB", 1.0),
                                                            ("RetrofitNonlinearLeftC", 0.2), ("RetrofitNonlinearLeftD", 0.0))]
      self._right = [p.get_float(k, default=d) for k, d in (("RetrofitNonlinearRightA", 2.5), ("RetrofitNonlinearRightB", 1.0),
                                                             ("RetrofitNonlinearRightC", 0.2), ("RetrofitNonlinearRightD", 0.0))]
    else:
      self._left, self._right = user_params_to_abcd(p.get_float("RetrofitNonlinearStrength", default=0.0),
                                                    p.get_float("RetrofitNonlinearSaturation", default=2.5),
                                                    p.get_float("RetrofitNonlinearBias", default=0.0))

  def _draw_plot(self, plot: rl.Rectangle):
    self._grid_x([-2, -1, 0, 1, 2], ["-2", "-1", "0", "1", "2"])
    self._grid_y([-0.5, -0.25, 0.0, 0.25, 0.5], ["-0.5", "-0.25", "0", "0.25", "0.5"])
    self._axis_title(tr("torque vs. lat accel (m/s²)"))
    slope = 1.0 / RETROFIT_BASE_LAT_ACCEL_FACTOR
    self._dashed(self.sx(self.x_min), self.sy(self.x_min * slope), self.sx(self.x_max), self.sy(self.x_max * slope), _STOCK, 2.0)
    self._curve(lambda x: siglin_torque(x, self._left, self._right))
    self._legend([(tr("stock linear"), _STOCK, True), (tr("raw ABCD") if self._advanced else tr("sigmoid"), _CURVE, False)])


class FFWindowPreview(_PlotWidget):
  x_min, x_max, y_min, y_max = 0.0, 2.0, 0.98, 1.08

  def __init__(self):
    super().__init__()
    self._gain, self._onset, self._onset_w, self._cutoff, self._cutoff_w = 0.0, 0.18, 0.08, 1.10, 0.30

  def reload(self):
    p = Params()
    self._gain = p.get_float("RetrofitTuneFFGain", default=0.0)
    self._onset = p.get_float("RetrofitTuneFFOnset", default=0.18)
    self._onset_w = p.get_float("RetrofitTuneFFOnsetWidth", default=0.08)
    self._cutoff = p.get_float("RetrofitTuneFFCutoff", default=1.10)
    self._cutoff_w = p.get_float("RetrofitTuneFFCutoffWidth", default=0.30)

  def _draw_plot(self, plot: rl.Rectangle):
    xs = [0.0, 0.4, 0.8, 1.2, 1.6, 2.0]
    self._grid_x(xs, [f"{v:.1f}" for v in xs])
    ys = [0.98, 1.0, 1.02, 1.04, 1.06, 1.08]
    self._grid_y(ys, [f"{v:.2f}" for v in ys])
    self._axis_title(tr("FF scale vs. |lat accel|"))
    self._dashed(plot.x, self.sy(1.0), plot.x + plot.width, self.sy(1.0), _REFERENCE, 1.0)
    for value, color, label in ((self._onset, _MARK_A, tr("onset")), (self._cutoff, _MARK_B, tr("cutoff"))):
      x = self.sx(min(max(value, self.x_min), self.x_max))
      self._dashed(x, plot.y, x, plot.y + plot.height, color, 1.0, 6.0)
      self._text(label, x + 8, plot.y + 12, 18, color)
    self._curve(lambda la: ff_window_scale(la, self._gain, self._onset, self._onset_w, self._cutoff, self._cutoff_w))
    self._legend([(tr("FF scale"), _CURVE, False)], x=plot.x + plot.width - 150)


class TurnDynamicsPreview(_PlotWidget):
  x_min, x_max, y_min, y_max = -1.0, 1.0, 0.3, 1.3

  def __init__(self):
    super().__init__()
    self._turn_in_boost, self._unwind_boost, self._unwind_taper = 0.0, 0.0, 0.0

  def reload(self):
    p = Params()
    self._turn_in_boost = p.get_float("RetrofitTuneTurnInBoost", default=0.0)
    self._unwind_boost = p.get_float("RetrofitTuneUnwindBoost", default=0.0)
    self._unwind_taper = p.get_float("RetrofitTuneUnwindTaper", default=0.0)
    self.y_max = max(1.3 + self._unwind_boost, 1.3 + self._turn_in_boost, 1.3)

  def _draw_plot(self, plot: rl.Rectangle):
    xs = [-1.0, -0.5, 0.0, 0.5, 1.0]
    self._grid_x(xs, [f"{v:.1f}" for v in xs])
    ys = []
    v = 0.4
    while v < self.y_max - 0.05:
      ys.append(round(v, 2))
      v += 0.2
    self._grid_y(ys, [f"{v:.1f}" for v in ys])
    self._dashed(plot.x, self.sy(1.0), plot.x + plot.width, self.sy(1.0), _REFERENCE, 1.0)
    self._dashed(self.sx(0.0), plot.y, self.sx(0.0), plot.y + plot.height, _REFERENCE, 1.0)
    # Phase direction labels on the axis-title row; arrows are drawn since the font has no arrow glyphs.
    font, _ = self._fonts()
    y = plot.y + plot.height + self.AXIS_TITLE_DY
    unwind, turn_in = tr("unwind"), tr("turn-in")
    self._arrow(plot.x + 6, y + 12, -1, _MARK_B)
    self._text(unwind, plot.x + 26, y, 18, _MARK_B)
    turn_in_w = measure_text_cached(font, turn_in, 18).x
    self._text(turn_in, plot.x + plot.width - 26 - turn_in_w, y, 18, _CURVE)
    self._arrow(plot.x + plot.width - 6, y + 12, 1, _CURVE)
    self._curve(lambda phase: turn_dynamics_multiplier(phase, self._turn_in_boost, self._unwind_boost, self._unwind_taper))
    self._legend([(tr("FF multiplier"), _CURVE, False)], x=plot.x + plot.width - 180)


class CenterTaperPreview(_PlotWidget):
  x_min, x_max, y_min, y_max = 0.0, 0.5, 0.70, 1.02
  SPEEDS = ((10.0, _MARK_A, "10 m/s"), (15.0, _MARK_C, "15 m/s"), (20.0, _CURVE, "20 m/s"))

  def __init__(self):
    super().__init__()
    self._max, self._lat, self._lat_w, self._speed, self._speed_w = 0.0, 0.14, 0.04, 14.0, 2.5

  def reload(self):
    p = Params()
    self._max = p.get_float("RetrofitTuneCenterTaperMax", default=0.0)
    self._lat = p.get_float("RetrofitTuneCenterTaperLat", default=0.14)
    self._lat_w = p.get_float("RetrofitTuneCenterTaperLatWidth", default=0.04)
    self._speed = p.get_float("RetrofitTuneCenterTaperSpeed", default=14.0)
    self._speed_w = p.get_float("RetrofitTuneCenterTaperSpeedWidth", default=2.5)

  def _draw_plot(self, plot: rl.Rectangle):
    xs = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
    self._grid_x(xs, [f"{v:.1f}" for v in xs])
    ys = [0.75, 0.80, 0.85, 0.90, 0.95, 1.0]
    self._grid_y(ys, [f"{v:.2f}" if v in (0.8, 0.9, 1.0) else "" for v in ys])
    self._axis_title(tr("output scale vs. |lat accel|"))
    for v_ego, color, _ in self.SPEEDS:
      self._curve(lambda la, v=v_ego: center_taper_scale(la, v, self._max, self._lat, self._lat_w, self._speed, self._speed_w), color, 2.0)
    self._legend([(label, color, False) for _, color, label in self.SPEEDS], y=plot.y + plot.height - 30)


class KPCurveEditor(_PlotWidget):
  """Draggable KP-vs-speed curve on log/log axes; each drag release writes its Params key."""

  x_min, x_max, y_min, y_max = 0.8, 36.0, 0.1, 320.0
  log_x = True
  log_y = True
  HIT_RADIUS = 50.0

  def __init__(self):
    super().__init__()
    self._values = [pt.default for pt in KP_POINTS]
    self._drag: int | None = None

  def reload(self):
    p = Params()
    self._values = [p.get_float(pt.key, default=pt.default) for pt in KP_POINTS]

  def reset_defaults(self):
    p = Params()
    for pt in KP_POINTS:
      p.put_float(pt.key, pt.default)
    self.reload()

  def _screen_points(self) -> list[tuple[float, float]]:
    return [(self.sx(pt.speed), self.sy(v)) for pt, v in zip(KP_POINTS, self._values, strict=True)]

  def _draw_plot(self, plot: rl.Rectangle):
    self._grid_x([pt.speed for pt in KP_POINTS], [f"{pt.speed:g}" for pt in KP_POINTS])
    self._grid_y([0.1, 0.3, 1, 3, 10, 30, 100, 300], ["0.1", "", "1", "", "10", "", "100", ""])
    self._axis_title(tr("KP vs. speed (m/s)"))
    pts = self._screen_points()
    self._polyline(pts, _CURVE, 3.0)
    for i, (x, y) in enumerate(pts):
      dragging = i == self._drag
      radius = 16 if dragging else 12
      rl.draw_circle_v(rl.Vector2(x, y), radius, _DRAG if dragging else _CURVE)
      label = f"{self._values[i]:.3g}"
      label_y = y - radius - 26
      if label_y < plot.y + 4:
        label_y = y + radius + 6
      self._text(label, x, label_y, 20, AetherListColors.HEADER, bold=True, center=True)

  # ── dragging ──

  def _handle_mouse_press(self, mouse_pos):
    best, best_d2 = None, self.HIT_RADIUS * self.HIT_RADIUS
    for i, (x, y) in enumerate(self._screen_points()):
      d2 = (mouse_pos.x - x) ** 2 + (mouse_pos.y - y) ** 2
      if d2 < best_d2:
        best, best_d2 = i, d2
    self._drag = best

  def _handle_mouse_event(self, mouse_event):
    if self._drag is None:
      return
    if mouse_event.left_released:
      self._commit()
      return
    pt = KP_POINTS[self._drag]
    self._values[self._drag] = min(max(self.y_from_screen(mouse_event.pos.y), pt.y_min), pt.y_max)

  def _handle_mouse_release(self, mouse_pos):
    self._commit()

  def _commit(self):
    if self._drag is None:
      return
    Params().put_float(KP_POINTS[self._drag].key, self._values[self._drag])
    self._drag = None


# ═══════════════════════════════════════════════════════════════
# Pages
# ═══════════════════════════════════════════════════════════════

class _RetrofitSubPage(_SettingsPage):
  """A page owned by StarPilotRetrofitLayout. Navigation requests are forwarded to the
  parent unchanged so the parent (and main_panel's stack) own the current page — a sub-page
  never tracks its own ``_current_sub_panel``, which would otherwise block re-entry."""

  @property
  def _header_title(self) -> str:
    # The breadcrumb reads the sub-panel's _header_title; ours lives on the wrapped view.
    return getattr(self._manager_view, "_header_title", "")

  def _navigate_to(self, sub_panel: str):
    if self._navigate_callback:
      self._navigate_callback(sub_panel)

  def _slider(self, p: TuneParam, on_done=None):
    """Slider dialog for a TuneParam; the default value is offered as a preset chip (= reset)."""
    def on_close(res, val):
      if res == DialogResult.CONFIRM:
        Params().put_float(p.key, float(val))
        if on_done:
          on_done()
    current = Params().get_float(p.key, default=p.default)
    gui_app.push_widget(AetherSliderDialog(tr(p.label), p.min, p.max, p.step, current, on_close,
                                           presets=[p.default], color=self.SLIDER_COLOR))

  def _value_row(self, p: TuneParam, on_done=None) -> SettingRow:
    return SettingRow(
      p.key, "value", p.label,
      subtitle=p.desc,
      get_value=lambda: format_adjustor_value(self._params.get_float(p.key), step=p.step),
      on_click=lambda: self._slider(p, on_done),
    )


class _PreviewPage(_RetrofitSubPage):
  """A plot widget above an AetherSettingsView list."""

  GAP = 14
  MIN_LIST_HEIGHT = 300

  def __init__(self, preview: _PlotWidget, sections: list[SettingSection], *, header_title: str, header_subtitle: str = "",
               preview_height: int = 300):
    super().__init__()
    self._preview = preview
    self._preview_height = preview_height
    self._manager_view = AetherSettingsView(
      self, sections,
      header_title=header_title,
      header_subtitle=header_subtitle,
      panel_style=DEFAULT_PANEL_STYLE,
    )

  def _render(self, rect):
    preview_h = min(self._preview_height, max(rect.height - self.MIN_LIST_HEIGHT, 120))
    self._preview.render(rl.Rectangle(rect.x, rect.y, rect.width, preview_h))
    list_y = rect.y + preview_h + self.GAP
    self._manager_view.render(rl.Rectangle(rect.x, list_y, rect.width, max(rect.height - preview_h - self.GAP, 1)))

  def show_event(self):
    super().show_event()
    self._preview.show_event()

  def hide_event(self):
    super().hide_event()
    self._preview.hide_event()

  def refresh(self):
    self._preview.reload()


class StarPilotRetrofitTuningLayout(_RetrofitSubPage):
  def __init__(self):
    super().__init__()
    self._build_view()

  def _build_view(self):
    sections = [
      SettingSection(tr_noop("Pedal"), [
        SettingRow(
          "RetrofitPedalOffsetStandstill",
          "value",
          tr_noop("Standstill Pedal Offset"),
          subtitle=tr_noop(
            "Low-speed deadband before pedal scaling. Less negative = gas sooner from a stop."
          ),
          get_value=lambda: f"{self._params.get_float('RetrofitPedalOffsetStandstill'):.2f}m/s²",
          on_click=lambda: self._show_slider(
            "RetrofitPedalOffsetStandstill",
            -0.5,
            0.2,
            step=0.05,
            unit="m/s²",
            value_type="float",
          ),
        ),
      ]),
    ]
    self._manager_view = AetherSettingsView(
      self,
      sections,
      header_title=tr_noop("Retrofit Tuning"),
      header_subtitle=tr_noop("Pedal and retrofit-specific adjustments."),
      panel_style=DEFAULT_PANEL_STYLE,
    )


class StarPilotNonlinearSteeringLayout(_PreviewPage):
  def __init__(self):
    preview = SigmoidCurvePreview()
    sections = [
      SettingSection(tr_noop("Model"), [
        SettingRow(
          "RetrofitNonlinearSteering", "toggle", tr_noop("Enable Nonlinear Steering"),
          subtitle=tr_noop("Replace the linear torque model with a sigmoid-linear curve: high response for small corrections, " +
                           "capped torque at large inputs. Requires offroad cycle."),
          get_state=lambda: self._params.get_bool("RetrofitNonlinearSteering"),
          set_state=lambda s: self._params.put_bool("RetrofitNonlinearSteering", s),
        ),
      ]),
      SettingSection(tr_noop("Shape"), [self._value_row(p, self.refresh) for p in NONLINEAR_PARAMS]),
      SettingSection(tr_noop("Advanced"), [
        SettingRow(
          "RetrofitNonlinearAdvancedNav", "value", tr_noop("Advanced (Raw ABCD)"),
          subtitle=tr_noop("Direct control of the sigmoid-linear parameters. When enabled, overrides Strength/Saturation/Bias."),
          get_value=lambda: tr_noop("On") if self._params.get_bool("RetrofitNonlinearAdvanced") else tr_noop("Configure"),
          on_click=self._open_advanced,
        ),
      ]),
    ]
    super().__init__(preview, sections, header_title=tr_noop("Nonlinear Steering"),
                     header_subtitle=tr_noop("Sigmoid-linear torque model for dual power steering."), preview_height=320)

  def _open_advanced(self):
    p = Params()
    if not p.get_bool("RetrofitNonlinearAdvanced"):
      # Seed raw ABCD from the user-facing shape so the advanced page starts on the same curve.
      left, right = user_params_to_abcd(p.get_float("RetrofitNonlinearStrength", default=0.0),
                                        p.get_float("RetrofitNonlinearSaturation", default=2.5),
                                        p.get_float("RetrofitNonlinearBias", default=0.0))
      for side, values in (("Left", left), ("Right", right)):
        for suffix, value in zip("ABCD", values, strict=True):
          p.put_float(f"RetrofitNonlinear{side}{suffix}", value)
    self._navigate_to("nonlinear_advanced")


class StarPilotNonlinearAdvancedLayout(_PreviewPage):
  def __init__(self):
    preview = SigmoidCurvePreview()

    def set_advanced(state: bool):
      self._params.put_bool("RetrofitNonlinearAdvanced", state)
      self.refresh()

    sections = [
      SettingSection(tr_noop("Mode"), [
        SettingRow(
          "RetrofitNonlinearAdvanced", "toggle", tr_noop("Use Raw ABCD Parameters"),
          subtitle=tr_noop("When ON, the values below define the torque curve. When OFF, Strength/Saturation/Bias are used."),
          get_state=lambda: self._params.get_bool("RetrofitNonlinearAdvanced"),
          set_state=set_advanced,
        ),
      ]),
      SettingSection(tr_noop("Left (positive lat accel)"), [self._value_row(p, self.refresh) for p in ABCD_PARAMS[:4]]),
      SettingSection(tr_noop("Right (negative lat accel)"), [self._value_row(p, self.refresh) for p in ABCD_PARAMS[4:]]),
    ]
    super().__init__(preview, sections, header_title=tr_noop("Raw ABCD"),
                     header_subtitle=tr_noop("a = steepness, b = amplitude, c = linear slope, d = offset."), preview_height=320)


class StarPilotControllerTuneLayout(_RetrofitSubPage):
  """Hub for the four tune groups."""

  def __init__(self):
    super().__init__()
    sections = [
      SettingSection(tr_noop("Gains"), [
        SettingRow(
          "tune_kp", "value", tr_noop("KP Curve (offroad)"),
          subtitle=tr_noop("How aggressively the car corrects steering errors at each speed. Lower = gentler; higher = snappier but can oscillate. " +
                           "Requires offroad cycle."),
          get_value=lambda: tr_noop("Edit"), navigate_to="tune_kp",
        ),
      ]),
      SettingSection(tr_noop("Live"), [
        SettingRow(
          "tune_ff", "value", tr_noop("FF Window"),
          subtitle=tr_noop("Extra steering effort in mid-range turns, tapering off for gentle and sharp turns. Takes effect immediately."),
          get_value=lambda: tr_noop("Edit"), navigate_to="tune_ff",
        ),
        SettingRow(
          "tune_turn", "value", tr_noop("Turn Dynamics"),
          subtitle=tr_noop("How steering behaves entering and exiting turns, and how the wheel resists small movements. Takes effect immediately."),
          get_value=lambda: tr_noop("Edit"), navigate_to="tune_turn",
        ),
        SettingRow(
          "tune_center", "value", tr_noop("Center Taper"),
          subtitle=tr_noop("Calms steering on straight highways by reducing output when driving mostly straight at speed. Takes effect immediately."),
          get_value=lambda: tr_noop("Edit"), navigate_to="tune_center",
        ),
      ]),
    ]
    self._manager_view = AetherSettingsView(
      self, sections,
      header_title=tr_noop("Controller Tune"),
      header_subtitle=tr_noop("Vehicle-specific lateral tuning constants."),
      panel_style=DEFAULT_PANEL_STYLE,
    )


class StarPilotKPCurveLayout(_PreviewPage):
  def __init__(self):
    preview = KPCurveEditor()
    sections = [
      SettingSection("", [
        SettingRow(
          "kp_reset", "action", tr_noop("Reset All KP"),
          subtitle=tr_noop("Restore the nine default gains."),
          action_text=tr_noop("RESET"), on_click=self._confirm_reset,
        ),
      ]),
    ]
    super().__init__(preview, sections, header_title=tr_noop("KP Curve"),
                     header_subtitle=tr_noop("Drag points to adjust. Requires offroad cycle."), preview_height=520)

  def _confirm_reset(self):
    def on_result(res):
      if res == DialogResult.CONFIRM:
        self._preview.reset_defaults()
    gui_app.push_widget(ConfirmDialog(tr("Reset all KP values to defaults?"), tr("Reset"), callback=on_result))


class _TuneGroupLayout(_PreviewPage):
  def __init__(self, preview: _PlotWidget, params: list[TuneParam], *, header_title: str, header_subtitle: str, section_title: str):
    rows: list[SettingRow] = []
    super().__init__(preview, [SettingSection(section_title, rows)], header_title=header_title, header_subtitle=header_subtitle)
    rows.extend(self._value_row(p, self.refresh) for p in params)


class StarPilotFFWindowLayout(_TuneGroupLayout):
  def __init__(self):
    super().__init__(FFWindowPreview(), FF_PARAMS, header_title=tr_noop("FF Window"),
                     header_subtitle=tr_noop("Mid-range feedforward boost. Live."), section_title=tr_noop("Window"))


class StarPilotTurnDynamicsLayout(_TuneGroupLayout):
  def __init__(self):
    super().__init__(TurnDynamicsPreview(), TURN_PARAMS, header_title=tr_noop("Turn Dynamics"),
                     header_subtitle=tr_noop("Turn-in / unwind shaping and friction phases. Live."), section_title=tr_noop("Dynamics"))


class StarPilotCenterTaperLayout(_TuneGroupLayout):
  def __init__(self):
    super().__init__(CenterTaperPreview(), CENTER_PARAMS, header_title=tr_noop("Center Taper"),
                     header_subtitle=tr_noop("Output reduction near straight at speed. Live."), section_title=tr_noop("Taper"))


class StarPilotRetrofitLayout(_SettingsPage):
  def __init__(self):
    super().__init__()
    self._active = False
    self._sub_panels = {
      "tuning": StarPilotRetrofitTuningLayout(),
      "nonlinear": StarPilotNonlinearSteeringLayout(),
      "nonlinear_advanced": StarPilotNonlinearAdvancedLayout(),
      "tune": StarPilotControllerTuneLayout(),
      "tune_kp": StarPilotKPCurveLayout(),
      "tune_ff": StarPilotFFWindowLayout(),
      "tune_turn": StarPilotTurnDynamicsLayout(),
      "tune_center": StarPilotCenterTaperLayout(),
    }
    self._wire_sub_panels()
    self._build_view()

  # All pages are siblings here so main_panel's panel stack gives hub → detail → back-to-hub.
  # Fire hide/show on the pages as the current one changes so previews re-read Params;
  # main_panel only calls set_current_sub_panel(), which the base class treats as a bare assignment.

  def _switch_child(self, name: str):
    prev = self._current_sub_panel
    if prev == name:
      return
    if self._active and prev in self._sub_panels:
      self._sub_panels[prev].hide_event()
    self._current_sub_panel = name
    if self._active and name in self._sub_panels:
      self._sub_panels[name].show_event()

  def _navigate_to(self, sub_panel: str):
    if sub_panel != self._current_sub_panel:
      self._switch_child(sub_panel)
      if self._navigate_callback:
        self._navigate_callback(sub_panel)

  def set_current_sub_panel(self, sub_panel: str):
    self._switch_child(sub_panel)

  def show_event(self):
    self._active = True
    super().show_event()

  def hide_event(self):
    self._active = False
    super().hide_event()

  def _build_view(self):
    sections = [
      SettingSection(tr_noop("Controls"), [
        SettingRow(
          "RetrofitPauseSteering",
          "toggle",
          tr_noop("Pause Steering"),
          subtitle=tr_noop(
            "Disable openpilot steering while driving. Longitudinal can stay active if engaged."
          ),
          get_state=lambda: self._params.get_bool("RetrofitPauseSteering"),
          set_state=lambda s: self._params.put_bool("RetrofitPauseSteering", s),
        ),
      ]),
      SettingSection(tr_noop("Steering"), [
        SettingRow(
          "RetrofitSASOffset",
          "value",
          tr_noop("SAS Offset"),
          subtitle=tr_noop(
            "Corrects a physically misaligned steering angle sensor. " +
            "Set to the raw angle your SAS reports when wheels are straight."
          ),
          get_value=lambda: f"{self._params.get_float('RetrofitSASOffset'):.0f}°",
          on_click=lambda: self._show_slider(
            "RetrofitSASOffset",
            -180,
            180,
            step=1,
            unit="°",
            value_type="float",
          ),
        ),
        SettingRow(
          "RetrofitNonlinearNav",
          "value",
          tr_noop("Nonlinear Steering"),
          subtitle=tr_noop("Sigmoid-linear torque model for dual power steering. Caps torque at large corrections."),
          get_value=lambda: tr_noop("On") if self._params.get_bool("RetrofitNonlinearSteering") else tr_noop("Configure"),
          navigate_to="nonlinear",
        ),
        SettingRow(
          "RetrofitTuneNav",
          "value",
          tr_noop("Controller Tune"),
          subtitle=tr_noop("KP gain curve, FF window, turn dynamics, and center taper. Most values take effect immediately."),
          get_value=lambda: tr_noop("Configure"),
          navigate_to="tune",
        ),
      ]),
      SettingSection(tr_noop("Longitudinal"), [
        SettingRow(
          "RetrofitTuningNav",
          "value",
          tr_noop("Pedal Tuning"),
          subtitle=tr_noop("Interceptor pedal mapping for standstill launch and creep."),
          get_value=lambda: tr_noop("Configure"),
          navigate_to="tuning",
        ),
      ]),
    ]
    self._manager_view = AetherSettingsView(
      self,
      sections,
      header_title=tr_noop("Retrofit Options"),
      header_subtitle=tr_noop("Comma Pedal and CAN emulator retrofit configurations."),
      panel_style=DEFAULT_PANEL_STYLE,
    )

#!/usr/bin/env python3
"""Measure text layout problems from a screenshot tour.

Reads every NNN_<page>.text.json written by the tour (UI_SCREENSHOT_DIR, selfdrive/ui/screenshot_tour.py)
— one entry per text draw of the exact frame saved as the matching PNG — and writes <dir>/text_lint.md
with measured facts per page. Facts, not verdicts: a reviewer confirms each one against the image.

  ./dev python scripts/ui_text_lint.py <shots_dir>

Also reports small touch targets from the matching NNN_<page>.targets.json when present.

Coordinates are logical device pixels (2160x1080), same as the PNGs. Text inside render-texture caches
is not seen, so a page can have visible text with no log entry.
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

SCREEN_W, SCREEN_H = 2160, 1080
H_CLIP_TOLERANCE = 2      # px past the clip rect before horizontal clipping is reported
OVERLAP_MIN_FRACTION = 0.25
NEAR_MISS_PX = (1.5, 12)  # left edges this far apart look like they were meant to align
SIZE_NEAR_MISS = (0.5, 2.0)  # sizes are FONT_SCALE-scaled (~2.5px apart per unscaled step), so only flag <2px drift
TINY_SIZE = 28
SMALL_TARGET_PX = 100  # touch targets narrower or shorter than this (~6 mm on the C3) are reported
MAX_ITEMS_PER_CHECK = 6


def _visible(e: dict) -> bool:
  if e["alpha"] == 0 or not e["text"].strip():
    return False
  x0, y0, x1, y1 = e["x"], e["y"], e["x"] + e["w"], e["y"] + e["h"]
  if x1 <= 0 or y1 <= 0 or x0 >= SCREEN_W or y0 >= SCREEN_H:
    return False
  if e["clip"]:
    cx, cy, cw, ch = e["clip"]
    if x1 <= cx or x0 >= cx + cw or y1 <= cy or y0 >= cy + ch:
      return False
  return True


def _label(e: dict) -> str:
  t = e["text"].replace("\n", " ")
  return f"\"{t[:40]}{'…' if len(t) > 40 else ''}\" @({e['x']:.0f},{e['y']:.0f}) size {e['size']:g}"


def _intersection(a: dict, b: dict) -> float:
  w = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
  h = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
  return w * h if w > 0 and h > 0 else 0.0


def lint_page(entries: list[dict], targets: list[dict] | None = None) -> list[str]:
  vis = [e for e in entries if _visible(e)]
  out: list[str] = []

  def section(title: str, items: list[str]):
    if items:
      extra = f" (+{len(items) - MAX_ITEMS_PER_CHECK} more)" if len(items) > MAX_ITEMS_PER_CHECK else ""
      out.append(f"- **{title}**{extra}: " + "; ".join(items[:MAX_ITEMS_PER_CHECK]))

  # 1. Missing glyphs (render as '?' or a box).
  section("missing glyphs", [f"{_label(e)} missing {''.join(e['missing_glyphs'])!r}" for e in vis if e["missing_glyphs"]])

  # 2. Horizontal clipping by the active scissor rect, or running off screen.
  clipped = []
  for e in vis:
    x1 = e["x"] + e["w"]
    if e["clip"]:
      cx, _, cw, _ = e["clip"]
      over = max(cx - e["x"], x1 - (cx + cw))
      if over > H_CLIP_TOLERANCE:
        clipped.append(f"{_label(e)} cut by {over:.0f}px (clip x {cx:.0f}–{cx + cw:.0f})")
    elif e["x"] < 0 or x1 > SCREEN_W:
      clipped.append(f"{_label(e)} runs off screen")
  section("text clipped horizontally", clipped)

  # 3. Overlapping text boxes (different strings; ignores shadow/duplicate draws at the same spot).
  overlaps = []
  for i, a in enumerate(vis):
    for b in vis[i + 1:]:
      if a["text"] == b["text"] and abs(a["x"] - b["x"]) < 6 and abs(a["y"] - b["y"]) < 6:
        continue
      inter = _intersection(a, b)
      smaller = min(a["w"] * a["h"], b["w"] * b["h"]) or 1
      if inter / smaller >= OVERLAP_MIN_FRACTION:
        overlaps.append(f"{_label(a)} overlaps {_label(b)} ({inter / smaller:.0%})")
  section("overlapping text", overlaps)

  # 4. Tiny text on a touchscreen.
  section("small text", [_label(e) for e in vis if e["size"] < TINY_SIZE])

  # 5. Near-miss font sizes (a type scale that drifted, e.g. 46 vs 48).
  sizes = Counter(e["size"] for e in vis)
  ordered = sorted(sizes)
  near_sizes = [f"{a:g}px ×{sizes[a]} vs {b:g}px ×{sizes[b]}" for a, b in zip(ordered, ordered[1:], strict=False)
                if SIZE_NEAR_MISS[0] < b - a < SIZE_NEAR_MISS[1]]
  section("near-identical font sizes", near_sizes)

  # 6. Left edges that almost align, among text of the same size (each edge used 2+ times).
  by_size: dict[float, Counter] = defaultdict(Counter)
  for e in vis:
    by_size[e["size"]][round(e["x"])] += 1
  near_edges = []
  for size, xs in sorted(by_size.items()):
    common = sorted(x for x, n in xs.items() if n >= 2)
    for a, b in zip(common, common[1:], strict=False):
      if NEAR_MISS_PX[0] < b - a <= NEAR_MISS_PX[1]:
        near_edges.append(f"size {size:g}: x={a} ×{xs[a]} vs x={b} ×{xs[b]}")
  section("left edges off by a few px", near_edges)

  # 7. Uneven vertical rhythm: same size + same left edge column, 3+ items, gaps that vary.
  columns: dict[tuple, list[float]] = defaultdict(list)
  for e in vis:
    columns[(e["size"], round(e["x"]))].append(e["y"])
  rhythm = []
  for (size, x), ys in sorted(columns.items()):
    ys = sorted(set(round(y) for y in ys))
    if len(ys) < 3:
      continue
    gaps = [b - a for a, b in zip(ys, ys[1:], strict=False)]
    if max(gaps) - min(gaps) > 6:
      rhythm.append(f"size {size:g} column x={x}: y gaps {gaps}")
  section("uneven vertical spacing (may be intentional, e.g. rows with/without subtitles)", rhythm)

  # 8. Small touch targets (NNN_<page>.targets.json: tappable widgets and hand-drawn button rects).
  seen, small = set(), []
  for t in targets or []:
    key = (round(t["x"]), round(t["y"]), round(t["w"]), round(t["h"]))
    if key in seen or t["y"] >= SCREEN_H or t["y"] + t["h"] <= 0 or t["x"] >= SCREEN_W or t["x"] + t["w"] <= 0:
      continue
    seen.add(key)
    if min(t["w"], t["h"]) < SMALL_TARGET_PX:
      small.append(f"`{t['name']}` {key[2]}x{key[3]} at ({key[0]},{key[1]})")
  section(f"touch targets under {SMALL_TARGET_PX}px on a side", small)

  summary = f"{len(vis)} visible text draws, {len(sizes)} font sizes: {', '.join(f'{s:g}' for s in ordered)}"
  return [summary] + out


def main():
  ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  ap.add_argument("shots_dir", type=Path)
  args = ap.parse_args()

  pages = sorted(args.shots_dir.glob("*.text.json"))
  if not pages:
    raise SystemExit(f"no *.text.json files in {args.shots_dir}")

  lines = ["# Text layout lint", "",
           "Measured from the text draws of the exact frame saved as each PNG. Coordinates are 2160x1080 device px.",
           "These are facts to verify against the image, not confirmed bugs.", ""]
  flagged = 0
  for path in pages:
    targets_path = path.with_name(path.name.removesuffix(".text.json") + ".targets.json")
    targets = json.loads(targets_path.read_text()) if targets_path.exists() else None
    result = lint_page(json.loads(path.read_text()), targets)
    flagged += len(result) > 1
    lines += [f"## {path.name.removesuffix('.text.json')}.png", result[0], *result[1:], ""]

  out = args.shots_dir / "text_lint.md"
  out.write_text("\n".join(lines))
  print(f"{len(pages)} pages, {flagged} with findings -> {out}")


if __name__ == "__main__":
  main()

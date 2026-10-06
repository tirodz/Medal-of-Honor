#!/usr/bin/env python3
"""Render a shaped Arabic string with an SFN font and print ASCII art.

Usage: render_sample.py <font.sfn> "<text>"
Used as a static proof that the injected glyphs lay out correctly (RTL,
connected forms, advances) without needing the emulator.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))
from tools.arabic import process  # noqa: E402
from tools.pal4 import decode  # noqa: E402
from tools.sfn import SfnFont  # noqa: E402
from tools.sfn_build import SfnBuilder  # noqa: E402


def render(font_path, text, scale=1):
    b = SfnBuilder(open(font_path, "rb").read())
    f = b.font
    atlas = decode(b.atlas, b.atlas_w, b.atlas_h)
    px = atlas.load()
    by_code = {}
    for c in f.chars:
        by_code.setdefault(c.code, c)
    visual = process(text)
    cells = []           # (x, y, value)
    pen = 0
    max_y = 0
    for ch in visual:
        c = by_code.get(ord(ch))
        if c is None:
            pen += 6
            continue
        if c.width and c.height:
            for y in range(c.height):
                for x in range(c.width):
                    v = px[c.u + x, c.v + y]
                    if v:
                        cells.append((pen + c.x_offset + x, c.y_offset + y, v))
        pen += max(1, c.advance)
        max_y = max(max_y, c.y_offset + c.height)
    if not cells:
        return []
    W = max(x for x, _, _ in cells) + 1
    H = max_y + 2
    grid = [[" " for _ in range(W)] for _ in range(H)]
    for x, y, v in cells:
        if 0 <= y < H and 0 <= x < W:
            grid[y][x] = "#" if v >= 8 else ("+" if v >= 3 else ".")
    return ["".join(r) for r in grid]


if __name__ == "__main__":
    font_path = sys.argv[1]
    text = sys.argv[2] if len(sys.argv) > 2 else "دمّر مدفعية العدو"
    for line in render(font_path, text):
        print(line)

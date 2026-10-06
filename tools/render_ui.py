#!/usr/bin/env python3
"""Renderer-faithful Arabic preview using the *injected* SFN glyphs.

This is NOT a TTF preview.  It decodes the actual 4bpp atlas from a built SFN
font and lays glyphs out with the game's own metrics:

    pen_x starts at 0 (the engine positions the run; the UI centres or
    right-aligns the whole box)
    glyph pixels are blitted at (pen_x + x_offset, y_offset)
    pen_x advances by `advance` (advance_x), not by the bitmap width

Direction handling mirrors the shipped pipeline: `arabic.process()` performs
shaping + bidi and returns the string already in *visual* (left-to-right)
order, so the renderer walks it left-to-right with no further reversal.

The palette is the linear ramp index i -> intensity i*17 (0..255), so glyph
antialiasing is preserved.  Output is a PNG so the pixels can be inspected.
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))
from tools.arabic import process  # noqa: E402
from tools.pal4 import decode  # noqa: E402
from tools.sfn_build import SfnBuilder  # noqa: E402


class SfnRenderer:
    def __init__(self, raw, name=""):
        self.b = SfnBuilder(raw)
        self.name = name or os.path.basename(getattr(self.b, "path", "") or "")
        self.atlas = decode(self.b.atlas, self.b.atlas_w, self.b.atlas_h)
        self._px = self.atlas.load()
        self.by_code = {}
        for c in self.b.font.chars:
            self.by_code.setdefault(c.code, c)
        self.kern = self._parse_kerning(raw)

    def _parse_kerning(self, raw):
        """Map (prev, next) -> delta for the version>=310 4-byte entries."""
        if not self.b.kio:
            return {}
        import struct
        nk = struct.unpack_from("<I", raw, self.b.kio)[0]
        k = {}
        pos = self.b.kio + 4
        for _ in range(nk):
            prev = struct.unpack_from("<H", raw, pos)[0]
            val = raw[pos + 2]
            nxt = raw[pos + 3]
            k[(prev, nxt)] = val - 256 if val > 127 else val
            pos += 4
        return k

    def missing(self, text):
        visual = process(text)
        return sorted({ch for ch in visual
                       if ord(ch) not in self.by_code and ch != " "})

    def measure(self, text):
        visual = process(text)
        pen = 0
        prev = None
        for ch in visual:
            c = self.by_code.get(ord(ch))
            if c is None:
                pen += 6
                continue
            pen += max(0, c.advance)
            prev = c.code
        return pen

    def render(self, text, pad=2):
        """Return an 'L' (grayscale) PIL image of the shaped, visual-order text."""
        visual = process(text)
        cells = []
        pen = 0
        prev = None
        max_y = 0
        for ch in visual:
            c = self.by_code.get(ord(ch))
            if c is None:
                pen += 6
                prev = None
                continue
            if prev is not None:
                pen += self.kern.get((prev, c.code), 0)
            if c.width and c.height:
                for y in range(c.height):
                    for x in range(c.width):
                        v = self._px[c.u + x, c.v + y]
                        if v:
                            cells.append((pen + c.x_offset + x, c.y_offset + y, v))
            pen += max(0, c.advance)
            max_y = max(max_y, c.y_offset + c.height)
            prev = c.code
        if not cells:
            return Image.new("L", (1, 1))
        w = max(x for x, _, _ in cells) + 1 + pad
        h = max_y + pad
        img = Image.new("L", (max(1, w), max(1, h)))
        p = img.load()
        for x, y, v in cells:
            if 0 <= x < w and 0 <= y < h:
                p[x, y] = min(255, v * 17)
        return img


def _fonts():
    """Yield (label, raw_bytes) for every built font (standalone + VIV)."""
    import glob
    from tools.viv import Viv
    for p in sorted(glob.glob(os.path.join(HERE, "build/fonts/*.SFN"))):
        yield os.path.basename(p), open(p, "rb").read()
    for p in sorted(glob.glob(os.path.join(HERE, "build/fonts/REALF*"))):
        for e in Viv.parse(p).entries:
            if e.name.lower().endswith(".sfn"):
                yield os.path.basename(p) + "::" + e.name, e.data


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("font", nargs="?", default="build/fonts/SUBFNT.SFN")
    ap.add_argument("text", nargs="?", default="دمّر مدفعية العدو.")
    ap.add_argument("--png", help="write PNG instead of ASCII")
    a = ap.parse_args()
    r = SfnRenderer(open(a.font, "rb").read(), a.font)
    print("missing glyphs:", r.missing(a.text))
    img = r.render(a.text)
    if a.png:
        img.resize((img.width * 3, img.height * 3), Image.NEAREST).save(a.png)
        print("wrote", a.png)
    else:
        px = img.load()
        for y in range(img.height):
            print("".join("#" if px[x, y] >= 128 else ("+" if px[x, y] >= 40 else
                          ("." if px[x, y] > 0 else " ")) for x in range(img.width)))

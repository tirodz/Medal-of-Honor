#!/usr/bin/env python3
"""Renderer-faithful diagnostic for the SFN atlas-geometry bug.

The PS2 font renderer sizes/clips the glyph texture using the geometry stored
in the EA *image entry* (the 28-byte tail that precedes the shape header), not
the shape header itself.  When the atlas is grown to hold the appended Arabic
glyphs but that tail is left at the original (smaller) height, every glyph whose
`v` is >= the stale height is dropped - which is exactly all of the Arabic
glyphs, while the original Latin glyphs (v < stale height) still draw.  The
result is the "Latin fine, Arabic fragmented" runtime corruption.

This tool renders a phrase twice: once honouring the stale entry height (the
broken build) and once with the corrected height (the fix), so the two can be
compared without PCSX2.

    python3 tools/diag_atlas_clip.py [font.SFN] "phrase"
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))

from PIL import Image, ImageDraw  # noqa: E402
from tools.arabic import process  # noqa: E402
from tools.pal4 import decode  # noqa: E402
from tools.sfn_build import SfnBuilder  # noqa: E402


def entry_geometry(raw):
    b = SfnBuilder(raw)
    e = b.image_entry
    if len(e) < 28:
        return None
    return {"blk": struct.unpack_from("<I", e, len(e) - 28)[0],
            "px": struct.unpack_from("<I", e, len(e) - 20)[0],
            "w": struct.unpack_from("<I", e, len(e) - 8)[0],
            "h": struct.unpack_from("<I", e, len(e) - 4)[0]}


def render(raw, text, clip_h=None):
    b = SfnBuilder(raw)
    atlas = decode(b.atlas, b.atlas_w, b.atlas_h)
    px = atlas.load()
    by = {c.code: c for c in b.font.chars}
    visual = process(text)
    pen = 0
    cells = []
    max_y = 0
    for ch in visual:
        c = by.get(ord(ch))
        if c is None:
            pen += 6
            continue
        for y in range(c.height):
            for x in range(c.width):
                v = px[c.u + x, c.v + y]
                if not v:
                    continue
                if clip_h is not None and (c.v + y) >= clip_h:
                    continue
                cells.append((pen + c.x_offset + x, c.y_offset + y, v))
        pen += max(0, c.advance)
        max_y = max(max_y, c.y_offset + c.height)
    img = Image.new("L", (max(1, pen + 4), max(1, max_y + 4)))
    p = img.load()
    for x, y, v in cells:
        if 0 <= x < img.width and 0 <= y < img.height:
            p[x, y] = min(255, v * 17)
    return img


def strip(imgs, labels, scale=3):
    W = max(i.width for i in imgs) * scale + 8
    H = sum(i.height * scale + 22 for i in imgs)
    out = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(out)
    y = 0
    for img, lab in zip(imgs, labels):
        d.text((4, y + 4), lab, fill=(0, 0, 0))
        y += 20
        big = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
        out.paste(big.convert("RGB"), (4, y))
        y += big.height + 2
    return out


def main():
    font = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "build/fonts/SUBFNT.SFN")
    text = sys.argv[2] if len(sys.argv) > 2 else "القائمة الرئيسية"
    pristine = sys.argv[3] if len(sys.argv) > 3 else None
    raw = open(font, "rb").read()
    g = entry_geometry(raw)
    # The failed build left the image entry at the pristine (smaller) height, so
    # read that height from the pristine font to reproduce the runtime clipping.
    stale = g["h"]
    if pristine:
        pg = entry_geometry(open(pristine, "rb").read())
        if pg:
            stale = pg["h"]
    print("font:", os.path.basename(font))
    print("built image-entry geometry:", g)
    print("clip height used for the BROKEN render:", stale)
    broken = render(raw, text, clip_h=stale)
    fixed = render(raw, text, clip_h=None)
    out = os.path.join(HERE, "build/qa", "atlas_clip_" + os.path.basename(font) + ".png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    strip([broken, fixed], ["BROKEN: engine clipped at stale height %d" % stale,
                            "FIXED: entry height synced to atlas"], 3).save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()

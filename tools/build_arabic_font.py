#!/usr/bin/env python3
"""Inject Arabic glyphs into an EA SFN raster font.

The Arabic text processor emits Unicode contextual presentation forms
(U+FE70..U+FEFF).  For each required code point we rasterize the glyph from a
TrueType Arabic font, quantise it to the font's 4bpp grayscale palette and
append it to the glyph atlas with a matching Character12 entry.

Metrics follow the engine convention: a glyph is drawn at
    (pen_x + x_offset, line_top + y_offset)
with the engine baseline at `ascent` pixels below the line top.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from pal4 import decode, encode  # noqa: E402
from sfn import CharEntry, SfnFont  # noqa: E402
from sfn_build import SfnBuilder  # noqa: E402

ALEF = "\uFE8D"  # isolated alef, a full-height vertical stroke
# glyphs whose ink bottom sits exactly on the baseline (used to locate it)
BASELINE_GLYPHS = "HEFLTIKNMBD R P".replace(" ", "") + "xzvw0123456789"


def _baseline(font):
    """Pixel row of the baseline, derived from flat-bottom Latin glyphs."""
    from collections import Counter
    c = Counter()
    for ch in BASELINE_GLYPHS:
        for g in font.chars:
            if g.code == ord(ch) and g.height:
                c[g.y_offset + g.height] += 1
    if not c:
        return font.ascent or 12
    return c.most_common(1)[0][0]


def _cap_height(font):
    """Height of a Latin capital, used as the Arabic size reference."""
    for code in ("H", "A", "E"):
        m = [c for c in font.chars if c.code == ord(code) and c.height]
        if m:
            return max(c.height for c in m)
    return font.ascent or 12


def _pick_size(ttf_path, target_height):
    best, best_d = 16, 1 << 30
    for p in range(8, 48):
        f = ImageFont.truetype(ttf_path, p)
        img = Image.new("L", (80, 80), 0)
        ImageDraw.Draw(img).text((20, 60), ALEF, font=f, fill=255, anchor="ls")
        bbox = img.getbbox()
        if not bbox:
            continue
        h = bbox[3] - bbox[1]
        d = abs(h - target_height)
        if d < best_d:
            best, best_d = p, d
    return best


def rasterize_glyph(font, ch, baseline, ttf_ascent, descent):
    """Return (bitmap 'L' 0..15, advance, x_offset, y_offset) or None.

    `baseline` is the engine row (y_offset+height of a flat-bottom Latin glyph)
    that the TrueType baseline is mapped onto, so Arabic sits on the same line
    as the Latin text.  Descenders are allowed to extend past that row.
    """
    pad = 10
    canvas_w = int(font.getlength(ch)) + pad * 2 + 4
    canvas_h = baseline + descent + pad * 2 + 8
    img = Image.new("L", (canvas_w, canvas_h), 0)
    ImageDraw.Draw(img).text((pad, pad + ttf_ascent), ch, font=font, fill=255, anchor="ls")
    bbox = img.getbbox()
    if bbox is None:
        return None
    x0, y0, x1, y1 = bbox
    ink = img.crop(bbox).point(lambda v: round(v * 15 / 255))
    if ink.width > 255 or ink.height > 255:
        return None
    advance = min(255, max(1, round(font.getlength(ch))))
    x_offset = min(255, max(0, x0 - pad))
    y_offset = baseline + y0 - (pad + ttf_ascent)
    if y_offset < 0 or y_offset > 255:
        return None
    return ink, advance, x_offset, y_offset


def build(raw, ttf_path, code_points, size=None, row_pitch=None, logger=print):
    b = SfnBuilder(raw)
    existing = {c.code for c in b.font.chars}
    need = [c for c in sorted(set(code_points)) if c not in existing and c != 0xFEFF]
    if not need:
        return raw, []
    ascent, descent = b.font.ascent, b.font.descent
    # The baseline row can exceed the u8 y_offset field in the large display
    # fonts (their Latin glyphs use a >255 row).  Clamp so Arabic still fits;
    # it then sits a few pixels high in those four fonts.
    baseline = min(_baseline(b.font), 255)
    cap = max(1, _cap_height(b.font))
    px = size or _pick_size(ttf_path, cap)
    glyphs = {}
    while px >= 8:
        ttf = ImageFont.truetype(ttf_path, px)
        ttf_ascent, _ = ttf.getmetrics()
        glyphs = {}
        ok = True
        for cp in need:
            r = rasterize_glyph(ttf, chr(cp), baseline, ttf_ascent, descent)
            if r is None:
                ok = False
                break
            glyphs[cp] = r
        if ok:
            break
        px -= 1  # a form is too tall for the u8 height field: shrink globally
    if not glyphs:
        return raw, []

    pitch = row_pitch or (max(g[0].height for g in glyphs.values()) + 2)
    W = b.atlas_w
    rows = []
    new_chars = []
    strip = Image.new("L", (W, pitch), 0)
    cur_u = 0
    base_v = b.atlas_h
    placed = []

    def flush():
        nonlocal strip, cur_u, base_v
        data = encode(strip)
        rows.extend(data[i:i + W // 2] for i in range(0, len(data), W // 2))
        base_v += pitch
        strip = Image.new("L", (W, pitch), 0)
        cur_u = 0

    for cp, (ink, advance, xo, yo) in glyphs.items():
        gw, gh = ink.size
        if cur_u + gw > W:
            flush()
        strip.paste(ink, (cur_u, 0))
        new_chars.append(CharEntry(code=cp, width=gw, height=gh, u=cur_u,
                                   v=base_v, advance=advance,
                                   x_offset=xo, y_offset=yo))
        placed.append(cp)
        cur_u += gw + 1
    flush()
    if rows and not any(rows[-1]):
        rows.pop()
    out = b.add_glyphs(new_chars, rows)
    return out, placed


if __name__ == "__main__":
    from tools.viv import Viv
    v = Viv.parse("extracted/MOH4/DATA/SHARED/UI/FE/REALFONT.VIV")
    raw = v.get("Trajan Pro_18.sfn").data
    ttf = "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"
    out, placed = build(raw, ttf, list(range(0xFE70, 0xFF00)))
    print("placed", len(placed), "size", len(raw), "->", len(out))
    f = SfnFont.parse_bytes(out)
    b = SfnBuilder(out)
    img = decode(b.atlas, b.atlas_w, b.atlas_h)
    px = img.load()
    for cp in [0xFE8D, 0xFEE3, 0xFED3, 0xFEAA, 0xFEE6]:
        c = [c for c in f.chars if c.code == cp][0]
        print(f"U+{cp:04X} w={c.width} h={c.height} adv={c.advance} yo={c.y_offset}")
        for y in range(c.v, c.v + c.height):
            print("".join("#" if px[c.u + x, y] >= 8 else ("." if px[c.u + x, y] < 2 else "+")
                          for x in range(c.u, c.u + c.width)))

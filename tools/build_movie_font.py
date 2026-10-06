#!/usr/bin/env python3
"""Build a byte-addressed Arabic movie-subtitle font.

The movie subtitle engine reads its strings from the .LOC files, which are
plain 8-bit, NUL-terminated tables (see the strlen loop at ELF 0x2986a0:
`lb`/`beqz`).  A code point above 0xFF therefore cannot survive the round
trip, so the contextual Arabic forms used by the movie translations are
assigned the unused high-byte slots 0x80..0xFF of the subtitle font.

The Latin glyphs 0x20..0x7F are preserved verbatim; the original Latin-1
range 0x80..0xFF is dropped because (a) the English/other movie strings never
rely on it once the subtitles are Arabic and (b) the character table must stay
sorted ascending by code, which the remap preserves.

Usage:  python3 tools/build_movie_font.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from build_arabic_font import (  # noqa: E402
    _baseline, _cap_height, _pick_size, rasterize_glyph,
)
from sfn import SfnFont, CharEntry  # noqa: E402
from sfn_build import SfnBuilder  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(HERE, "build", "fonts")

# The movie player loads one of the standalone DATA/*.SFN fonts; the exact one
# is not named in the executable, so every standalone font carries the Arabic
# byte codes.  The VIV-embedded fonts are front-end only (16-bit) and are left
# alone.  SUBFNT is the subtitle font and is the primary target.
MOVIE_FONTS = [
    "SUBFNT.SFN", "OBJFONT.SFN", "DBFNT.SFN", "COMICFNT.SFN",
    "TPRO10.SFN", "TPRO10B.SFN", "TPRO12.SFN", "TPRO12B.SFN",
]

# byte slots handed out to Arabic contextual forms
FIRST_SLOT, LAST_SLOT = 0x80, 0xFF


def load_forms():
    """Return the sorted list of Arabic presentation forms the movie needs."""
    import json
    import importlib.util
    import tools.arabic as ar

    rows = json.load(open(os.path.join(HERE, "translations", "loc_strings.json")))
    spec = importlib.util.spec_from_file_location(
        "loc_ar", os.path.join(HERE, "translations", "loc_ar.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    forms = set()
    for r in rows:
        ar_txt = mod.AR.get(r["id"])
        if not ar_txt:
            continue
        for ch in ar.process(ar_txt):
            o = ord(ch)
            if 0x0600 <= o <= 0x06FF or 0xFB50 <= o <= 0xFEFF:
                forms.add(o)
    return sorted(forms)


def build_byte_font(raw, ttf_path, forms):
    """Return (new_bytes, mapping form->byte), or (None, None) if no room."""
    b = SfnBuilder(raw)
    font = b.font
    # overwrite the (unused-by-subtitles) Latin-1 glyph slots in place so the
    # character table keeps its size, order and kerning indices
    slots = [c.code for c in font.chars if FIRST_SLOT <= c.code <= LAST_SLOT]
    if len(forms) > len(slots):
        return None, None
    mapping = {cp: slots[i] for i, cp in enumerate(forms)}

    baseline = _baseline(font)
    cap = max(1, _cap_height(font))
    px = _pick_size(ttf_path, cap)
    glyphs = {}
    while px >= 8:
        ttf = ImageFont.truetype(ttf_path, px)
        ttf_ascent, _ = ttf.getmetrics()
        glyphs = {}
        ok = True
        for cp in forms:
            r = rasterize_glyph(ttf, chr(cp), baseline, ttf_ascent, font.descent)
            if r is None:
                ok = False
                break
            glyphs[cp] = r
        if ok:
            break
        px -= 1
    if not glyphs:
        raise SystemExit("could not rasterise any Arabic form")

    pitch = max(g[0].height for g in glyphs.values()) + 2
    W = b.atlas_w
    new_rows = []
    strip = Image.new("L", (W, pitch), 0)
    cur_u = 0
    base_v = b.atlas_h
    replacements = {}
    from pal4 import encode

    def flush():
        nonlocal strip, cur_u, base_v
        data = encode(strip)
        new_rows.extend(data[i:i + W // 2] for i in range(0, len(data), W // 2))
        base_v += pitch
        strip = Image.new("L", (W, pitch), 0)
        cur_u = 0

    for cp in forms:
        ink, adv, xo, yo = glyphs[cp]
        gw, gh = ink.size
        if cur_u + gw > W:
            flush()
        strip.paste(ink, (cur_u, 0))
        replacements[mapping[cp]] = CharEntry(
            code=mapping[cp], width=gw, height=gh, u=cur_u, v=base_v,
            advance=adv, x_offset=xo, y_offset=yo)
        cur_u += gw + 1
    flush()
    if new_rows and not any(new_rows[-1]):
        new_rows.pop()

    out = b.replace_glyphs(replacements, new_rows)
    return out, mapping


def main():
    ttf = os.path.join(HERE, "build", "fonts_src", "NotoSansArabic-Regular.ttf")
    if not os.path.exists(ttf):
        raise SystemExit("Arabic TTF not found: " + ttf)
    forms = load_forms()
    print(f"movie needs {len(forms)} contextual forms -> bytes "
          f"0x{FIRST_SLOT:02X}..0x{FIRST_SLOT + len(forms) - 1:02X}")
    os.makedirs(OUT_DIR, exist_ok=True)
    import json
    from build_arabic_font import build as build16

    # UI/front-end code points from the shaped translation DB
    db = json.load(open(os.path.join(HERE, "translations", "ar_final.json")))
    ui_cps = sorted({ord(c) for s in db.values() for c in s if ord(c) > 0x7F})

    all_maps = {}
    for name in MOVIE_FONTS:
        # always start from the pristine extracted font so this script is
        # idempotent (build_fonts.py output must not be re-consumed)
        raw = open(os.path.join(HERE, "extracted/MOH4/DATA", name), "rb").read()
        out16, _ = build16(raw, ttf, ui_cps)          # 16-bit Arabic (UI text)
        out, mapping = build_byte_font(out16, ttf, forms)  # byte Arabic (movies)
        if out is None:
            print(f"  {name}: only {len([c for c in SfnFont.parse_bytes(raw).chars if FIRST_SLOT <= c.code <= LAST_SLOT])}"
                  f" high slots -> byte remap skipped (not the movie font)")
            with open(os.path.join(OUT_DIR, name), "wb") as f:
                f.write(out16)
            continue
        with open(os.path.join(OUT_DIR, name), "wb") as f:
            f.write(out)
        f2 = SfnFont.parse_bytes(out)
        codes = {c.code for c in f2.chars}
        have16 = sum(1 for c in codes if c > 0xFF)
        have8 = sum(1 for c in codes if FIRST_SLOT <= c <= LAST_SLOT)
        print(f"  {name}: {len(raw)} -> {len(out)} bytes, nchars={f2.num_chars}, "
              f"16-bit glyphs={have16}, byte glyphs={have8}")
        all_maps[name] = {str(k): v for k, v in mapping.items()}
    with open(os.path.join(OUT_DIR, "movie_byte_map.json"), "w") as f:
        json.dump(all_maps["SUBFNT.SFN"], f, indent=1)
    print("wrote", OUT_DIR)


if __name__ == "__main__":
    main()

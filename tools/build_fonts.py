#!/usr/bin/env python3
"""Build the Arabic-extended versions of every SFN font used by the game.

The set of required code points is derived from the shaped translation DB
(translations/ar_final.json): Arabic presentation forms plus Arabic-block
punctuation/digits.  Each font is loaded from its source (a standalone .SFN or
an entry inside a VIV), the missing glyphs are rasterized from the chosen
TrueType Arabic face and appended to the atlas, and the result is written to
build/fonts/.  A report is printed with per-font coverage.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))
from tools.sfn_build import SfnBuilder  # noqa: E402
from tools.build_arabic_font import build  # noqa: E402
from tools.viv import Viv  # noqa: E402

TTF = os.environ.get("AR_TTF", os.path.join(HERE, "build", "fonts_src", "NotoSansArabic-Regular.ttf"))
OUTDIR = os.path.join(HERE, "build", "fonts")


def needed_codepoints(db_path):
    db = json.load(open(db_path))
    cps = set()
    for s in db.values():
        for ch in s:
            o = ord(ch)
            if o > 0x7F:
                cps.add(o)
    return sorted(cps)


def sources():
    """Yield (label, kind, path, entry_name) for every SFN in the game."""
    for p in sorted(glob.glob(os.path.join(HERE, "extracted", "**", "*.VIV"), recursive=True)):
        try:
            v = Viv.parse(p)
        except Exception:
            continue
        for e in v.entries:
            if e.name.lower().endswith((".sfn", ".ffn", ".xfn")):
                yield f"{os.path.basename(p)}::{e.name}", "viv", p, e.name
    for p in sorted(glob.glob(os.path.join(HERE, "extracted", "**", "*.SFN"), recursive=True)):
        yield os.path.basename(p), "file", p, None


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    cps = needed_codepoints(os.path.join(HERE, "translations", "ar_final.json"))
    print(f"required code points: {len(cps)}")
    results = []
    for label, kind, path, ename in sources():
        if kind == "viv":
            raw = Viv.parse(path).get(ename).data
        else:
            raw = open(path, "rb").read()
        b = SfnBuilder(raw)
        if b.rebuild() != raw:
            results.append((label, "ROUNDTRIP-FAIL", 0, 0, 0))
            continue
        out, placed = build(raw, TTF, cps)
        fb = SfnBuilder(out)
        present = {c.code for c in fb.font.chars}
        missing = [c for c in cps if c not in present and c != 0xFEFF]
        over = [c for c in fb.font.chars if c.u + c.width > fb.atlas_w or c.v + c.height > fb.atlas_h]
        safe = os.path.basename(label).replace(" ", "_").replace("::", "__")
        with open(os.path.join(OUTDIR, safe), "wb") as f:
            f.write(out)
        status = "OK" if not missing and not over else "WARN"
        results.append((label, status, len(present), len(missing), len(over)))
    print(f"{'font':46s} {'status':6s} {'nch':>5s} {'miss':>5s} {'over':>5s}")
    for label, st, nch, miss, over in results:
        print(f"{label:46s} {st:6s} {nch:5d} {miss:5d} {over:5d}")
    bad = [r for r in results if r[1] != "OK"]
    print(f"\nfonts={len(results)} not-OK={len(bad)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Static verification of the built (Arabic) resources.

Runtime testing needs PCSX2 + a PS2 BIOS, which this environment does not have,
so instead every built resource is decoded back and checked against the
translation database, and representative UI/subtitle strings are rasterized
with the actual injected fonts to a contact sheet.

Outputs: build/qa/*.png and build/qa/verify.json
"""
import glob
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))

import tools.arabic as ar  # noqa: E402
from tools.loc import Loc  # noqa: E402
from tools.viv import Viv  # noqa: E402
from tools.sfn import SfnFont  # noqa: E402
from tools.render_ui import SfnRenderer  # noqa: E402

TREE = os.path.join(HERE, "build", "tree")
QA = os.path.join(HERE, "build", "qa")
FONTS = os.path.join(HERE, "build", "fonts")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verify_strings():
    """Every built STRINGS.VIV must still parse and contain Arabic forms."""
    import xml.etree.ElementTree as ET
    results = []
    for p in sorted(glob.glob(os.path.join(TREE, "**", "STRINGS*.VIV"), recursive=True)):
        v = Viv.parse(p)
        arabic = 0
        total = 0
        for e in v.entries:
            txt = e.data.decode("utf-16-le")
            try:
                root_el = ET.fromstring(txt)
            except ET.ParseError:
                results.append((os.path.relpath(p, TREE), -1, -1))
                continue
            for s in list(root_el.iter("localstring")) + list(root_el.iter("globalstring")):
                total += 1
                val = ""
                for c in s:
                    if c.tag == "english":
                        val = c.get("value", "")
                if ar.has_arabic(val):
                    arabic += 1
        results.append((os.path.relpath(p, TREE), total, arabic))
    return results


def verify_locs():
    """Built movie LOCs must decode back to the translated shaped text."""
    bmap = {int(k): v for k, v in json.load(open(os.path.join(FONTS, "movie_byte_map.json"))).items()}
    rev = {v: k for k, v in bmap.items()}
    AR = _load(os.path.join(HERE, "translations", "loc_ar.py"), "loc_ar").AR
    rows = json.load(open(os.path.join(HERE, "translations", "loc_strings.json")))
    by_movie = {}
    for r in rows:
        by_movie.setdefault(r["movie"], {})[r["index"]] = r["id"]
    ok = bad = 0
    details = []
    for p in sorted(glob.glob(os.path.join(TREE, "**", "MOVIES", "LOC", "*.LOC"), recursive=True)):
        movie = os.path.splitext(os.path.basename(p))[0]
        loc = Loc(open(p, "rb").read())
        for idx, sid in by_movie.get(movie, {}).items():
            raw = loc.blocks[0]["strings"][idx]
            decoded = "".join(chr(rev[b]) if b >= 0x80 else chr(b) for b in raw.encode("latin1"))
            expect = ar.process(AR[sid])
            if decoded == expect:
                ok += 1
            else:
                bad += 1
                details.append((movie, sid, decoded, expect))
    return ok, bad, details


def render_sheets():
    os.makedirs(QA, exist_ok=True)
    from PIL import Image
    # UI sample from the shared string table
    v = Viv.parse(os.path.join(TREE, "MOH4/DATA/SHARED/STRINGS.VIV"))
    import xml.etree.ElementTree as ET
    vals = []
    for e in v.entries:
        root_el = ET.fromstring(e.data.decode("utf-16-le"))
        for s in list(root_el.iter("localstring")) + list(root_el.iter("globalstring")):
            for c in s:
                if c.tag == "english":
                    val = c.get("value", "")
                    if ar.has_arabic(val):
                        vals.append(val)
    r = SfnRenderer(open(os.path.join(FONTS, "SUBFNT.SFN"), "rb").read(), "SUBFNT")
    sheet = _contact(vals[:22], r, os.path.join(QA, "ui_arabic_sample.png"))
    # movie subtitles
    bmap = {int(k): v for k, v in json.load(open(os.path.join(FONTS, "movie_byte_map.json"))).items()}
    AR = _load(os.path.join(HERE, "translations", "loc_ar.py"), "loc_ar").AR
    mv = []
    for sid in list(AR)[:20]:
        shaped = ar.process(AR[sid])
        mv.append("".join(chr(bmap.get(ord(c), ord(c))) for c in shaped))
    _contact(mv, r, os.path.join(QA, "movie_subtitle_sample.png"))
    return sheet


def _contact(strings, renderer, path):
    from PIL import Image
    imgs = []
    for s in strings:
        try:
            imgs.append(renderer.render(s))
        except Exception:
            continue
    if not imgs:
        return None
    W = max(i.width for i in imgs) + 8
    H = sum(i.height + 4 for i in imgs) + 8
    sheet = Image.new("L", (W, H), 0)
    y = 4
    for i in imgs:
        sheet.paste(i, (4, y))
        y += i.height + 4
    sheet.save(path)
    return path


def main():
    s = verify_strings()
    tot = sum(t for _, t, _ in s)
    ara = sum(a for _, _, a in s)
    print(f"STRINGS.VIV files: {len(s)}  entries={tot}  arabic={ara}")
    ok, bad, det = verify_locs()
    print(f"movie LOC decode: ok={ok} bad={bad}")
    for d in det[:10]:
        print("  MISMATCH", d)
    render_sheets()
    print("wrote QA sheets to", QA)
    json.dump({"strings_files": len(s), "strings_entries": tot, "strings_arabic": ara,
               "loc_ok": ok, "loc_bad": bad}, open(os.path.join(QA, "verify.json"), "w"), indent=1)


if __name__ == "__main__":
    main()

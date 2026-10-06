#!/usr/bin/env python3
"""Build the modified game tree: inject Arabic strings and fonts.

Reads translations/ar_final.json (shaped, visually-ordered Arabic) and:
  * rewrites the `english` value of every matching entry in each STRINGS.VIV
  * replaces each SFN font with the Arabic-extended build in build/fonts/
Writes the modified files under build/tree/<same relative path>, leaving the
extracted/ tree untouched.  Prints a size report so ISO headroom is known.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))
from tools.inject_strings import patch_xml  # noqa: E402
from tools.viv import Viv  # noqa: E402

TREE = os.path.join(HERE, "build", "tree")
FONTS = os.path.join(HERE, "build", "fonts")


def rel(path):
    return os.path.relpath(path, os.path.join(HERE, "extracted"))


def main():
    tr = json.load(open(os.path.join(HERE, "translations", "ar_final.json")))
    scaleform = json.load(open(os.path.join(HERE, "translations", "ar_scaleform_final.json")))
    report = []
    # --- strings ---------------------------------------------------------
    pats = ["STRINGS.VIV", "STRINGMP.VIV"]
    string_files = []
    for pat in pats:
        string_files += glob.glob(os.path.join(HERE, "extracted", "**", pat), recursive=True)
    for p in sorted(set(string_files)):
        v = Viv.parse(p)
        changed = 0
        for e in v.entries:
            txt = e.data.decode("utf-16-le")
            # Front-end/HUD strings are rendered through Scaleform/GFx. They
            # must stay in logical order so Scaleform can perform its own BiDi
            # pass; gameplay text keeps the pre-visualized LTR path.
            merged = dict(tr)
            merged.update({k: v for k, v in scaleform.items() if k in tr})
            patched = patch_xml(txt, merged)
            if patched != txt:
                e.data = patched.encode("utf-16-le")
                e.size = len(e.data)
                changed += 1
        out = v.build()
        dest = os.path.join(TREE, rel(p))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "wb").write(out)
        report.append((rel(p), os.path.getsize(p), len(out), changed))

    # --- fonts -----------------------------------------------------------
    for p in sorted(glob.glob(os.path.join(HERE, "extracted", "**", "*.VIV"), recursive=True)):
        try:
            v = Viv.parse(p)
        except Exception:
            continue  # e.g. LOADING.VIV, which uses a different container
        changed = 0
        for e in v.entries:
            if not e.name.lower().endswith((".sfn", ".ffn", ".xfn")):
                continue
            fp = os.path.join(FONTS, os.path.basename(p).replace(" ", "_") + "__" + e.name.replace(" ", "_"))
            if os.path.exists(fp):
                e.data = open(fp, "rb").read()
                e.size = len(e.data)
                changed += 1
        if changed:
            out = v.build()
            dest = os.path.join(TREE, rel(p))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "wb").write(out)
            report.append((rel(p), os.path.getsize(p), len(out), changed))

    for p in sorted(glob.glob(os.path.join(HERE, "extracted", "**", "*.SFN"), recursive=True)):
        name = os.path.basename(p)
        fp = os.path.join(FONTS, name)
        if os.path.exists(fp):
            dest = os.path.join(TREE, rel(p))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            data = open(fp, "rb").read()
            open(dest, "wb").write(data)
            report.append((rel(p), os.path.getsize(p), len(data), 1))

    # --- save-game dialogs (UTF-16 .LOC) ---------------------------------
    from tools.inject_savegame import load, localize  # noqa: E402
    sg = load("savegame_ar.py")
    for fn, table in (("SG_MISC.LOC", sg.SG_MISC), ("SAVEGAME.LOC", sg.SAVEGAME)):
        src = os.path.join(HERE, "extracted", "MOH4", "DATA", "SAVEGAME", fn)
        out, changed = localize(src, table)
        dest = os.path.join(TREE, "MOH4", "DATA", "SAVEGAME", fn)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "wb").write(out)
        report.append((rel(src), os.path.getsize(src), len(out), changed))

    # --- movie subtitles / title cards (8-bit .LOC) ----------------------
    for p in sorted(glob.glob(os.path.join(HERE, "build", "movies", "LOC", "*.LOC"))):
        name = os.path.basename(p)
        src = os.path.join(HERE, "extracted", "MOH4", "DATA", "SHARED", "MOVIES", "LOC", name)
        dest = os.path.join(TREE, rel(src))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        data = open(p, "rb").read()
        open(dest, "wb").write(data)
        report.append((rel(src), os.path.getsize(src), len(data), 1))

    print(f"{'file':52s} {'orig':>10s} {'new':>10s} {'delta':>8s} {'chg':>4s}")
    tot_o = tot_n = 0
    for r, o, n, c in report:
        print(f"{r:52s} {o:10d} {n:10d} {n-o:+8d} {c:4d}")
        tot_o += o; tot_n += n
    print(f"{'TOTAL':52s} {tot_o:10d} {tot_n:10d} {tot_n-tot_o:+8d}")
    grow = [(r, n - o) for r, o, n, c in report if n > o]
    print("\nfiles that grew:", len(grow), "total growth", sum(d for _, d in grow))


if __name__ == "__main__":
    main()

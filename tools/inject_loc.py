#!/usr/bin/env python3
"""Translate the movie .LOC subtitle blocks into Arabic and inject them.

English block 0 of each movie LOC is replaced with the byte-encoded Arabic
form of every translated string.  The contextual Arabic forms are addressed
through the byte map produced by tools/build_movie_font.py (slots 0x80..0xFF
of SUBFNT.SFN / OBJFONT.SFN), because the movie engine consumes 8-bit,
NUL-terminated strings.

Output: build/movies/LOC/<name>.LOC  (plus a QA summary)
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

SRC = os.path.join(HERE, "extracted/MOH4/DATA/SHARED/MOVIES/LOC")
OUT = os.path.join(HERE, "build/movies/LOC")
MAP = os.path.join(HERE, "build/fonts/movie_byte_map.json")


def load_ar():
    spec = importlib.util.spec_from_file_location(
        "loc_ar", os.path.join(HERE, "translations", "loc_ar.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.AR


def encode(text, bmap):
    """Shaped Arabic -> bytes using the movie font's byte map."""
    out = bytearray()
    for ch in text:
        o = ord(ch)
        if o in bmap:
            out.append(bmap[o])
        elif o < 0x80:
            out.append(o)
        else:
            raise ValueError(f"unmappable code point U+{o:04X} in {text!r}")
    return bytes(out)


def main():
    bmap = {int(k): v for k, v in json.load(open(MAP)).items()}
    AR = load_ar()
    rows = json.load(open(os.path.join(HERE, "translations", "loc_strings.json")))
    by_movie = {}
    for r in rows:
        by_movie.setdefault(r["movie"], {})[r["index"]] = r["id"]

    os.makedirs(OUT, exist_ok=True)
    total = injected = 0
    for path in sorted(glob.glob(os.path.join(SRC, "*.LOC"))):
        movie = os.path.splitext(os.path.basename(path))[0]
        loc = Loc(open(path, "rb").read())
        blocks = [list(b["strings"]) for b in loc.blocks]
        for idx, sid in by_movie.get(movie, {}).items():
            total += 1
            ar_txt = AR.get(sid)
            if not ar_txt:
                continue
            shaped = ar.process(ar_txt)
            blocks[0][idx] = encode(shaped, bmap).decode("latin1")
            injected += 1
        raw = Loc.build(blocks)
        # sanity: block 0 must decode and stay 8-bit
        chk = Loc(raw)
        assert len(chk.blocks) == len(loc.blocks)
        dst = os.path.join(OUT, os.path.basename(path))
        with open(dst, "wb") as f:
            f.write(raw)
        print(f"  {movie}: {len(loc.blocks)} blocks, {len(by_movie.get(movie, {}))} "
              f"strings, {len(raw)} bytes")
    print(f"injected {injected}/{total} movie strings -> {OUT}")


if __name__ == "__main__":
    main()

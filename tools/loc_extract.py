#!/usr/bin/env python3
"""Extract translatable English strings from the movie .LOC files.

Writes translations/loc_strings.json: a list of
    {"id", "movie", "index", "english"}
Only block 0 (English) is used.  Empty / whitespace-only slots and slots
that are pure Latin title-card text are still emitted so the whole block can
be rebuilt verbatim.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.loc import Loc  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOC_DIR = os.path.join(HERE, "extracted/MOH4/DATA/SHARED/MOVIES/LOC")
OUT = os.path.join(HERE, "translations/loc_strings.json")


def main():
    rows = []
    for path in sorted(glob.glob(os.path.join(LOC_DIR, "*.LOC"))):
        movie = os.path.splitext(os.path.basename(path))[0]
        loc = Loc(open(path, "rb").read())
        for i, s in enumerate(loc.blocks[0]["strings"]):
            if s.strip():
                rows.append({"id": f"LOC_{movie}_{i:03d}", "movie": movie,
                             "index": i, "english": s})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print(f"wrote {len(rows)} strings from {len(set(r['movie'] for r in rows))} movies -> {OUT}")


if __name__ == "__main__":
    main()

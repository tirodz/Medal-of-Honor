#!/usr/bin/env python3
"""Reconstruct the full strings behind MoH:EA .LOC suffix-sharing tables.

Each entry's offset points into the shared pool, so many entries are byte
suffixes of a longer string (used for progressive text reveal).  To localize
we translate only the maximal strings and then, for every index, take the
matching tail of its maximal Arabic string -- preserving the exact reveal
granularity.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))
from tools.mohsub import Loc  # noqa: E402


def maximal_map(strings):
    """For each index, return (root_index, chars_from_end) where the entry is
    a suffix of the root string."""
    roots = []
    for i, s in enumerate(strings):
        # s is a proper suffix of some longer entry?
        is_suffix = False
        for j, t in enumerate(strings):
            if j != i and len(t) > len(s) and t.endswith(s):
                is_suffix = True
                break
        if not is_suffix:
            roots.append(i)
    out = {}
    for i, s in enumerate(strings):
        # choose the shortest root that has s as a suffix (the tightest)
        best = None
        for r in roots:
            t = strings[r]
            if t.endswith(s) or t == s:
                if best is None or len(t) < len(strings[best]):
                    best = r
        out[i] = (best, len(s))
    return out, roots


if __name__ == "__main__":
    for p in ("MOH4/DATA/SAVEGAME/SAVEGAME.LOC", "MOH4/DATA/SAVEGAME/SG_MISC.LOC"):
        loc = Loc(open(os.path.join(HERE, "extracted", p), "rb").read())
        for si, sec in enumerate(loc.sections):
            m, roots = maximal_map(sec)
            print(f"== {p} sec{si}: {len(sec)} entries, {len(roots)} roots")
            for r in roots:
                print(f"   root[{r}] = {sec[r]!r}")

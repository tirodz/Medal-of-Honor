#!/usr/bin/env python3
"""Localize the save-game .LOC tables (UTF-16) into Arabic.

Unlike the movie .LOC tables (8-bit Latin-1, no room for Arabic), the
save-game tables store UTF-16 strings and are used directly by the renderer,
so they can carry Arabic.

The tables share string suffixes in a single pool: many index entries are byte
suffixes of a longer string (progressive reveal).  We translate only the
maximal strings ("parts"), rebuild the pool with the shaped Arabic, and
recompute every index offset so the suffix relationships and reveal
granularity are preserved.
"""
import bisect
import importlib.util
import os
import struct
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))
from tools.arabic import process  # noqa: E402

SAVEGAME_DIR = os.path.join(HERE, "extracted", "MOH4", "DATA", "SAVEGAME")


def load(name):
    spec = importlib.util.spec_from_file_location(
        name[:-3], os.path.join(HERE, "translations", name))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def split_parts(pool):
    parts, starts = [], []
    p = 0
    while p < len(pool):
        e = p
        while pool[e:e + 2] != b"\x00\x00":
            e += 2
        starts.append(p)
        parts.append(pool[p:e].decode("utf-16-le"))
        p = e + 2
    return parts, starts


def build_loc(parts, entry_offsets, section_off, section_header):
    """Rebuild pool + offset table, keeping every entry's (part, charpos)."""
    body = bytearray()
    starts, cur = [], 0
    for s in parts:
        starts.append(cur)
        body += s.encode("utf-16-le") + b"\x00\x00"
        cur += len(s.encode("utf-16-le")) + 2
    new_offsets = []
    for part_idx, charpos in entry_offsets:
        new_offsets.append(starts[part_idx] + charpos * 2)
    sec = bytearray(section_header)               # b'LOCL'
    sec += struct.pack("<I", 16 + 4 * len(new_offsets) + len(body))
    sec += struct.pack("<I", 0)
    sec += struct.pack("<I", len(new_offsets))
    for off in new_offsets:
        sec += struct.pack("<I", off)
    sec += body
    return bytes(sec)


def localize(path, table):
    raw = open(path, "rb").read()
    o = struct.unpack_from("<I", raw, 16)[0]
    n = struct.unpack_from("<I", raw, o + 12)[0]
    base = o + 16 + 4 * n
    parts, starts = split_parts(raw[base:])
    # map every index offset -> (part, charpos)
    entry_offsets = []
    for j in range(n):
        off = struct.unpack_from("<I", raw, o + 16 + 4 * j)[0]
        pi = bisect.bisect_right(starts, off) - 1
        entry_offsets.append((pi, (off - starts[pi]) // 2))
    # translate maximal parts
    changed = 0
    for idx, ar in table.items():
        if 0 <= idx < len(parts) and parts[idx].strip():
            parts[idx] = process(ar)
            changed += 1
    new_sec = build_loc(parts, entry_offsets, o, raw[o:o + 4])
    head = bytearray(raw[:o])
    struct.pack_into("<I", head, 16, o)           # single section
    return bytes(head) + new_sec, changed


def main():
    sg = load("savegame_ar.py")
    jobs = [("SG_MISC.LOC", sg.SG_MISC), ("SAVEGAME.LOC", sg.SAVEGAME)]
    for fn, table in jobs:
        src = os.path.join(SAVEGAME_DIR, fn)
        out, changed = localize(src, table)
        dest = os.path.join(HERE, "build", "tree", "MOH4", "DATA", "SAVEGAME", fn)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "wb").write(out)
        print(f"{fn:14s} translated {changed:3d} parts  {os.path.getsize(src)} -> {len(out)}")


if __name__ == "__main__":
    main()

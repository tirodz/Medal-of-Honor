#!/usr/bin/env python3
"""Assemble the final Arabic-localized ISO.

Starts from a byte copy of the pristine original (so the PS2 boot system area
and every untouched file stay identical), then writes each modified file from
build/tree/ back into the volume using tools/iso9660.py.  Files that outgrew
their allocation are relocated to fresh sectors at the end of the volume.
"""
import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))
from tools.iso9660 import IsoFile  # noqa: E402

SRC = os.path.join(HERE, "original", "Medal of Honor - European Assault (USA).iso")
TREE = os.path.join(HERE, "build", "tree")
OUT = os.path.join(HERE, "build", "moh_ea_ar.iso")


def sha256(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def main():
    print("copying original ...", flush=True)
    shutil.copyfile(SRC, OUT)
    iso = IsoFile(OUT)
    changed = 0
    grown = 0
    for root, _, files in os.walk(TREE):
        for fn in files:
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, TREE).replace(os.sep, "/")
            data = open(full, "rb").read()
            before = iso.find(rel)
            if before is None:
                print("  ! not found on ISO:", rel)
                continue
            old_alloc = (before[2] + 2047) // 2048
            new_alloc = (len(data) + 2047) // 2048
            iso.put(rel, data)
            changed += 1
            if new_alloc > old_alloc:
                grown += 1
            print(f"  {rel:48s} {before[2]:9d} -> {len(data):9d}")
    iso.close()
    print(f"\nfiles written: {changed} (relocated: {grown})")
    print("output:", OUT)
    print("sha256:", sha256(OUT))


if __name__ == "__main__":
    main()

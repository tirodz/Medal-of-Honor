#!/usr/bin/env python3
"""Verify the rebuilt ISO against the original.

Checks:
  * the PS2 boot system area (first 16 sectors) is byte-identical
  * every file not in build/tree/ is byte-identical to the original
  * every file in build/tree/ is present with the expected size
  * the ISO9660 directory records are consistent (pycdlib can open it)
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))
from tools.iso9660 import IsoFile  # noqa: E402

ORIG = os.path.join(HERE, "original", "Medal of Honor - European Assault (USA).iso")
NEW = os.path.join(HERE, "build", "moh_ea_ar.iso")
TREE = os.path.join(HERE, "build", "tree")
SYS = 16 * 2048


def changed_set():
    out = set()
    for root, _, files in os.walk(TREE):
        for fn in files:
            out.add(os.path.relpath(os.path.join(root, fn), TREE).replace(os.sep, "/"))
    return out


def main():
    changed = changed_set()
    a = IsoFile(ORIG)
    b = IsoFile(NEW)
    fails = []

    with open(ORIG, "rb") as f1, open(NEW, "rb") as f2:
        if f1.read(SYS) != f2.read(SYS):
            fails.append("system area (PS2 boot logo) differs")

    n_ok = n_changed = 0
    for path, roff, lba, ln, isdir in a.walk():
        bf = b.find(path)
        if bf is None:
            fails.append(f"missing on new ISO: {path}")
            continue
        _, blba, bln = bf
        if path in changed:
            expect = open(os.path.join(TREE, path), "rb").read()
            got = b._read_sectors(blba, (bln + 2047) // 2048)[:bln]
            if got != expect:
                fails.append(f"{path}: bytes differ from build tree "
                             f"({bln} vs {len(expect)})")
            else:
                n_changed += 1
            continue
        # unchanged: compare bytes
        da = a._read_sectors(lba, (ln + 2047) // 2048)[:ln]
        db = b._read_sectors(blba, (bln + 2047) // 2048)[:bln]
        if da != db:
            fails.append(f"unexpected change: {path} ({ln} -> {bln})")
        else:
            n_ok += 1

    a.close(); b.close()

    # structural check via pycdlib
    import pycdlib
    iso = pycdlib.PyCdlib(); iso.open(NEW)
    iso.close()

    print(f"unchanged files verified identical : {n_ok}")
    print(f"changed files with expected size   : {n_changed}")
    print(f"failures                           : {len(fails)}")
    for f in fails[:30]:
        print("  !", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

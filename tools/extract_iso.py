#!/usr/bin/env python3
"""Extract files from the MoH: European Assault PS2 ISO (ISO9660, no Joliet/RR).

Walks the ISO with pycdlib and writes each file to a mirrored directory tree.
File names are stored as NAME.EXT (version suffix ';1' stripped).
"""
import argparse
import os
import sys

import pycdlib


def walk(iso, path, outdir):
    count = 0
    for child in iso.list_children(iso_path=path):
        if child is None or child.is_dot() or child.is_dotdot():
            continue
        name = child.file_identifier().decode("ascii", "replace")
        if child.is_dir():
            clean = name.rstrip(".").rstrip("/")
            sub = os.path.join(outdir, clean)
            os.makedirs(sub, exist_ok=True)
            count += walk(iso, (path.rstrip("/") + "/" + clean), sub)
        else:
            clean = name.split(";")[0]
            dest = os.path.join(outdir, clean)
            with open(dest, "wb") as f:
                iso.get_file_from_iso_fp(f, iso_path=(path.rstrip("/") + "/" + name))
            count += 1
    return count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("iso")
    ap.add_argument("outdir")
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    iso = pycdlib.PyCdlib()
    iso.open(args.iso)
    n = walk(iso, "/", args.outdir)
    iso.close()
    print(f"extracted {n} files to {args.outdir}")


if __name__ == "__main__":
    sys.exit(main())

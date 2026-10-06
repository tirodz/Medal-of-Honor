#!/usr/bin/env python3
"""Create / apply a compact sector-delta patch between two ISO images.

The Arabic build changes 41 files but writes every one of them in place (the
grown files are relocated into free gaps, so the image keeps its original
length).  A sector-level delta is therefore tiny compared to the 3.86 GB ISO
and is the artefact that can actually be distributed.

Patch format (little-endian):
    char     magic[8]  = b"MOH4AR01"
    u32      sector_size = 2048
    u64      target_size
    u32      count
    repeat count times:
        u32  sector index
        u8   data[sector_size]

Usage:
    make_patch.py make  <original.iso> <patched.iso> <out.patch>
    make_patch.py apply <original.iso> <in.patch>    <out.iso>
    make_patch.py info  <in.patch>
"""
import os
import struct
import sys

MAGIC = b"MOH4AR01"
SECTOR = 2048


def _sha(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def make(orig, patched, out):
    so, sp = os.path.getsize(orig), os.path.getsize(patched)
    if so != sp:
        raise SystemExit(f"size mismatch {so} != {sp}; sector delta needs equal length")
    diffs = []
    with open(orig, "rb") as a, open(patched, "rb") as b:
        i = 0
        while True:
            da = a.read(SECTOR)
            if not da:
                break
            db = b.read(SECTOR)
            if da != db:
                diffs.append((i, db))
            i += 1
    with open(out, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<IQI", SECTOR, sp, len(diffs)))
        for idx, data in diffs:
            f.write(struct.pack("<I", idx))
            f.write(data)
    print(f"sectors compared : {i}")
    print(f"sectors changed  : {len(diffs)}")
    print(f"patch size       : {os.path.getsize(out)} bytes")
    print(f"sha256(patch)    : {_sha(out)}")


def apply(orig, patch, out):
    with open(patch, "rb") as f:
        if f.read(8) != MAGIC:
            raise SystemExit("bad patch magic")
        sector, tsize, count = struct.unpack("<IQI", f.read(16))
        if sector != SECTOR:
            raise SystemExit("unexpected sector size")
        with open(orig, "rb") as a, open(out, "wb") as o:
            o.write(a.read())
            for _ in range(count):
                idx, = struct.unpack("<I", f.read(4))
                o.seek(idx * SECTOR)
                o.write(f.read(SECTOR))
    if os.path.getsize(out) != tsize:
        raise SystemExit("output size mismatch after apply")
    print(f"applied {count} sectors -> {out} ({tsize} bytes)")
    print(f"sha256(out)      : {_sha(out)}")


def info(patch):
    with open(patch, "rb") as f:
        if f.read(8) != MAGIC:
            raise SystemExit("bad patch magic")
        sector, tsize, count = struct.unpack("<IQI", f.read(16))
    print(f"magic=MOH4AR01 sector={sector} target_size={tsize} sectors={count}")
    print(f"patch bytes={os.path.getsize(patch)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    cmd = sys.argv[1]
    if cmd == "make":
        make(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "apply":
        apply(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "info":
        info(sys.argv[2])
    else:
        raise SystemExit(__doc__)

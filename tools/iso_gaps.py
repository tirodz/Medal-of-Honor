#!/usr/bin/env python3
"""Map ISO9660 extent usage and inspect the free gaps."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))
from tools.iso9660 import IsoFile  # noqa: E402

ORIG = os.path.join(HERE, "original", "Medal of Honor - European Assault (USA).iso")
SECTOR = 2048

iso = IsoFile(ORIG)
spans = []
for path, roff, lba, ln, isdir in iso.walk():
    nsec = (ln + SECTOR - 1) // SECTOR
    spans.append((lba, lba + nsec, path))
spans.sort()
vol = iso.volume_sectors
print("volume_sectors", vol, "files", len(spans))
print("first file lba", spans[0][0], "max end", max(s[1] for s in spans))

# gaps between occupied spans (also include system area 0..16 and pvd)
occ = [(0, 16, "<system>")] + spans
gaps = []
prev_end = 0
for s, e, p in occ:
    if s > prev_end:
        gaps.append((prev_end, s))
    prev_end = max(prev_end, e)
if vol > prev_end:
    gaps.append((prev_end, vol))
print("\ngaps (lba_start, lba_end, sectors, MB):")
for g0, g1 in gaps:
    n = g1 - g0
    print(f"  {g0:8d} .. {g1:8d}  {n:8d}  {n*2048/1e6:8.1f} MB")
# inspect first 4KB of each gap
print("\ngap contents:")
for g0, g1 in gaps:
    iso.f.seek(g0 * SECTOR)
    sample = iso.f.read(min(4096, (g1 - g0) * SECTOR))
    nz = sum(1 for b in sample if b)
    print(f"  {g0:8d} nonzero_bytes_in_first_4k={nz}  head={sample[:16].hex()}")
iso.close()

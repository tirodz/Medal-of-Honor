#!/usr/bin/env python3
"""Minimal ISO9660 reader/writer tailored to the MoH:EA PS2 disc.

Only what the localization needs:
  * walk the directory hierarchy and record, for every file, the byte offset
    of its directory record (so the extent/size fields can be patched), plus
    its extent LBA and size.
  * relocate a file to a fresh extent at the end of the volume and rewrite its
    directory record + the PVD volume size.  No Rock Ridge/Joliet on this disc.

The PS2 boot "system area" (first 16 sectors) is never touched, so the boot
logo and licence data stay intact -- unlike a full pycdlib re-master, which
zeroes it.
"""
import struct

SECTOR = 2048
SYS_SECTORS = 16
PVD_LBA = 16


def _both16(v):
    return struct.pack("<H", v) + struct.pack(">H", v)


def _both32(v):
    return struct.pack("<I", v) + struct.pack(">I", v)


class IsoFile:
    def __init__(self, path):
        self.f = open(path, "r+b")
        self.f.seek(PVD_LBA * SECTOR)
        self.pvd = bytearray(self.f.read(SECTOR))
        self._cache = None
        self._alloc = None  # (cursor, limit) inside the free gap

    def _free_gaps(self):
        """Unused sector ranges inside the volume (excluding the boot area,
        ISO metadata below the first file, the anchor sector at the very end,
        and every file extent)."""
        vol = self.volume_sectors
        spans = [(lba, lba + (ln + SECTOR - 1) // SECTOR)
                 for _p, _r, lba, ln, _d in self.walk()]
        floor = min((s for s, _ in spans), default=SYS_SECTORS)
        occ = [(0, SYS_SECTORS), (vol - 1, vol)] + spans
        occ.sort()
        gaps, prev = [], 0
        for s, e in occ:
            if s > prev:
                gaps.append((prev, s))
            prev = max(prev, e)
        if vol > prev:
            gaps.append((prev, vol))
        return [(a, b) for a, b in gaps if b - a >= 64 and a >= floor]

    def _alloc_sectors(self, n):
        if self._alloc is None:
            gaps = self._free_gaps()
            if not gaps:
                raise RuntimeError("no free space in volume")
            g = max(gaps, key=lambda t: t[1] - t[0])
            self._alloc = [g[0], g[1]]
        cur, limit = self._alloc
        if cur + n > limit:
            raise RuntimeError("free gap exhausted")
        self._alloc[0] = cur + n
        return cur

    @property
    def volume_sectors(self):
        return struct.unpack_from("<I", self.pvd, 80)[0]

    def set_volume_sectors(self, n):
        struct.pack_into("<I", self.pvd, 80, n)
        struct.pack_into(">I", self.pvd, 84, n)

    def _read_sectors(self, lba, count):
        self.f.seek(lba * SECTOR)
        return self.f.read(count * SECTOR)

    def _records(self, lba, size):
        """Yield (record_offset_in_iso, rec) for a directory extent."""
        data = self._read_sectors(lba, (size + SECTOR - 1) // SECTOR)
        base = lba * SECTOR
        off = 0
        while off < size:
            ln = data[off]
            if ln == 0:
                # advance to next sector boundary
                off = (off // SECTOR + 1) * SECTOR
                continue
            rec = data[off:off + ln]
            yield base + off, rec
            off += ln

    def walk(self, lba=None, size=None, prefix=""):
        """Yield (path, record_offset, extent_lba, data_len, is_dir)."""
        if lba is None:
            lba = struct.unpack_from("<I", self.pvd, 158)[0]
            size = struct.unpack_from("<I", self.pvd, 166)[0]
        for roff, rec in self._records(lba, size):
            if rec[25] & 0x02:  # directory flag
                name_len = rec[32]
                ident = rec[33:33 + name_len]
                if ident in (b"\x00", b"\x01"):
                    continue
                child_lba = struct.unpack_from("<I", rec, 2)[0]
                child_len = struct.unpack_from("<I", rec, 10)[0]
                nm = ident.decode("ascii")
                yield from self.walk(child_lba, child_len, prefix + nm + "/")
            else:
                name_len = rec[32]
                ident = rec[33:33 + name_len].decode("ascii")
                if ident.endswith(";1"):
                    ident = ident[:-2]
                yield (prefix + ident, roff, struct.unpack_from("<I", rec, 2)[0],
                       struct.unpack_from("<I", rec, 10)[0], False)

    def find(self, path):
        if self._cache is None:
            self._cache = {p: (roff, lba, ln)
                           for p, roff, lba, ln, _ in self.walk()}
        return self._cache.get(path)

    def read_file(self, path):
        roff, lba, ln = self.find(path)
        return self._read_sectors(lba, (ln + SECTOR - 1) // SECTOR)[:ln]

    def write_in_place(self, path, data):
        """Overwrite a file if it still fits its allocated extent."""
        roff, lba, ln = self.find(path)
        alloc = (ln + SECTOR - 1) // SECTOR
        need = (len(data) + SECTOR - 1) // SECTOR
        if need > alloc:
            return False
        self.f.seek(lba * SECTOR)
        self.f.write(data)
        if len(data) % SECTOR:
            self.f.write(b"\x00" * (SECTOR - len(data) % SECTOR))
        self._set_record_size(roff, len(data))
        self._cache = None
        return True

    def _set_record_size(self, roff, n):
        self.f.seek(roff + 10)
        self.f.write(_both32(n))

    def _set_record_extent(self, roff, lba, n):
        self.f.seek(roff + 2)
        self.f.write(_both32(lba))
        self.f.write(_both32(n))

    def append_file(self, path, data):
        """Write a file into fresh sectors inside the volume's free space.

        The volume size and the UDF anchor sector at the very end are left
        untouched, so the disc structure stays exactly as mastered.
        """
        roff, lba, ln = self.find(path)
        nsec = (len(data) + SECTOR - 1) // SECTOR
        new_lba = self._alloc_sectors(nsec)
        self.f.seek(new_lba * SECTOR)
        self.f.write(data)
        if len(data) % SECTOR:
            self.f.write(b"\x00" * (SECTOR - len(data) % SECTOR))
        self._set_record_extent(roff, new_lba, len(data))
        self._cache = None  # extents changed
        return new_lba

    def put(self, path, data):
        if not self.write_in_place(path, data):
            self.append_file(path, data)

    def close(self):
        self.f.close()


if __name__ == "__main__":
    import sys
    iso = IsoFile(sys.argv[1] if len(sys.argv) > 1 else
                  "original/Medal of Honor - European Assault (USA).iso")
    n = 0
    for p, roff, lba, ln, _ in iso.walk():
        n += 1
        if n <= 40:
            print(f"{lba:8d} {ln:10d} {p}")
    print("total files", n, "volume_sectors", iso.volume_sectors)
    iso.close()

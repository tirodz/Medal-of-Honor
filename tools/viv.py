#!/usr/bin/env python3
"""EA VIV container (Medal of Honor: European Assault PS2).

Layout (all big-endian):
  u16 magic            0xc0fb
  u16 names_region_size
  u16 entry_count
  for each entry (desc immediately precedes its name):
      u24 offset       absolute file offset of data block
      u24 size         data block size
      name             ASCII, NUL-terminated
  <padding to 64-byte boundary>
  data blocks at their offsets

This module parses, extracts, and repacks VIVs. Repacking preserves the exact
original bytes when no entry is modified (verified by round-trip test).
"""
import struct
from dataclasses import dataclass, field


def align64(x):
    return (x + 63) & ~63


@dataclass
class VivEntry:
    name: str
    offset: int
    size: int
    data: bytes = b""


@dataclass
class Viv:
    path: str = ""
    magic: int = 0xC0FB
    names_region_size: int = 0
    entries: list = field(default_factory=list)
    tail: bytes = b""  # any bytes after the last entry's data block

    @classmethod
    def parse(cls, path):
        with open(path, "rb") as f:
            raw = f.read()
        return cls.parse_bytes(raw, path)

    @classmethod
    def parse_bytes(cls, raw, path=""):
        o = cls(path=path)
        o.magic, o.names_region_size, count = struct.unpack_from(">HHH", raw, 0)
        pos = 6
        for _ in range(count):
            off = int.from_bytes(raw[pos:pos + 3], "big")
            size = int.from_bytes(raw[pos + 3:pos + 6], "big")
            pos += 6
            end = raw.index(b"\x00", pos)
            name = raw[pos:end].decode("latin1")
            pos = end + 1
            o.entries.append(VivEntry(name, off, size, raw[off:off + size]))
        # tail: bytes after the max data end (normally none)
        maxend = max((e.offset + e.size for e in o.entries), default=0)
        o.tail = raw[maxend:]
        return o

    def build(self):
        count = len(self.entries)

        def table_for(offsets):
            t = bytearray()
            for e, off in zip(self.entries, offsets):
                t += off.to_bytes(3, "big")
                t += e.size.to_bytes(3, "big")
                t += e.name.encode("latin1") + b"\x00"
            return t

        def layout():
            # entries are stored 64-byte aligned; the table itself is fixed
            # size, so offsets are stable once names_region is known
            t = table_for([0] * count)
            names_region = len(t) + 2
            data_start = align64(8 + names_region)
            offs, cur = [], data_start
            for e in self.entries:
                offs.append(cur)
                cur = align64(cur + e.size)
            return names_region, offs

        names_region, offsets = layout()
        # names_region does not depend on offsets, so this is already stable
        t = table_for(offsets)
        out = bytearray(struct.pack(">HHH", self.magic, len(t) + 2, count) + bytes(t))
        last = len(self.entries) - 1
        for i, (e, off) in enumerate(zip(self.entries, offsets)):
            if len(out) < off:
                out += b"\x00" * (off - len(out))
            out += e.data
            if i != last and len(out) % 64:   # entries are 64-aligned; no tail pad
                out += b"\x00" * (64 - len(out) % 64)
        out += self.tail
        return bytes(out)

    def get(self, name):
        for e in self.entries:
            if e.name == name:
                return e
        return None


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        v = Viv.parse(p)
        rebuilt = v.build()
        orig = open(p, "rb").read()
        rt = "ROUNDTRIP-OK" if rebuilt == orig else f"ROUNDTRIP-FAIL({len(rebuilt)} vs {len(orig)})"
        print(f"{p}: magic=0x{v.magic:04x} n={len(v.entries)} {rt}")
        for e in v.entries:
            print(f"   {e.name:40s} off=0x{e.offset:06x} size={e.size} head={e.data[:8].hex()}")

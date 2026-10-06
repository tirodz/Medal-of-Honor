#!/usr/bin/env python3
"""EA BIGF/BIGH archive (Medal of Honor: European Assault PS2 front-end).

Header (16 bytes, big-endian except archive size):
  char  signature[4]      "BIGF" or "BIGH"
  u32le archive_size
  u32be number_of_files
  u32be directory_size     (bytes of directory that follow)
Directory entries (in order):
  u32be offset
  u32be size
  name\0
Data blocks at their offsets (64-byte aligned).
"""
import struct
from dataclasses import dataclass, field


@dataclass
class BigEntry:
    name: str
    offset: int
    size: int
    data: bytes = b""


@dataclass
class Big:
    path: str = ""
    signature: str = "BIGF"
    archive_size: int = 0
    num_files: int = 0
    directory_size: int = 0
    entries: list = field(default_factory=list)
    raw: bytes = b""

    @classmethod
    def parse(cls, path):
        with open(path, "rb") as f:
            raw = f.read()
        return cls.parse_bytes(raw, path)

    @classmethod
    def parse_bytes(cls, raw, path=""):
        o = cls(path=path, raw=raw)
        o.signature = raw[0:4].decode("latin1")
        o.archive_size = struct.unpack_from("<I", raw, 4)[0]
        o.num_files, o.directory_size = struct.unpack_from(">II", raw, 8)
        pos = 16
        for _ in range(o.num_files):
            off, size = struct.unpack_from(">II", raw, pos)
            pos += 8
            end = raw.index(b"\x00", pos)
            name = raw[pos:end].decode("latin1")
            pos = end + 1
            o.entries.append(BigEntry(name, off, size, raw[off:off + size]))
        o.dir_end = pos
        return o

    def build(self):
        """Rebuild preserving offsets when sizes are unchanged; otherwise repack."""
        out = bytearray(self.raw[:16])
        # keep original offsets if all entries fit within original layout
        dirbuf = bytearray()
        for e in self.entries:
            dirbuf += struct.pack(">II", e.offset, e.size)
            dirbuf += e.name.encode("latin1") + b"\x00"
        # header
        struct.pack_into("<I", out, 4, self.archive_size)
        struct.pack_into(">I", out, 8, len(self.entries))
        struct.pack_into(">I", out, 12, len(dirbuf))
        body = bytearray(bytes(out[:16]) + bytes(dirbuf))
        if len(body) < self.entries[0].offset:
            body += b"\x00" * (self.entries[0].offset - len(body))
        # place each entry at its declared offset
        for e in self.entries:
            if len(body) < e.offset:
                body += b"\x00" * (e.offset - len(body))
            assert len(body) == e.offset, (len(body), e.offset)
            body += e.data
        return bytes(body)

    def get(self, name):
        for e in self.entries:
            if e.name == name:
                return e
        return None


if __name__ == "__main__":
    import sys
    p = sys.argv[1]
    b = Big.parse(p)
    print(f"{p}: sig={b.signature} n={len(b.entries)} dirsize={b.directory_size} archsize={b.archive_size}")
    rebuilt = b.build()
    print("roundtrip:", "OK" if rebuilt == b.raw else f"DIFF({len(rebuilt)} vs {len(b.raw)})")
    for e in b.entries[:20]:
        print(f"   {e.name:45s} off=0x{e.offset:06x} size={e.size} head={e.data[:8]!r}")

#!/usr/bin/env python3
"""MoH:EA .LOC string-table parser (movie subtitles + save-game text).

Two on-disc layouts, distinguished by the container magic:

  'LOCHD' (movies)   header: size,flags,count + count dword offsets
                     section 'LOCL': size, flags, count, count offsets,
                     then NUL-terminated 8-bit (Latin-1) strings.
  'LOCH'  (savegame) header: size,?,count + count dword offsets
                     section 'LOCL': size, flags, count, count offsets,
                     then NUL-terminated UTF-16LE strings, preceded by a
                     'LOCI' index block of 16-bit ids (not rebuilt here).

Every section is preserved verbatim; only string payloads are re-encoded.
"""
import struct

MAGIC_L = b"LOCL"


class Loc:
    def __init__(self, raw):
        self.raw = bytes(raw)
        assert raw[:4] in (b"LOCH", b"LOCHD"), raw[:5]
        self.magic = raw[:5] if raw[:5] == b"LOCHD" else b"LOCH"
        self.utf16 = self.magic == b"LOCH"          # savegame strings are 16-bit
        self.count = struct.unpack_from("<I", raw, 12)[0]
        self.offsets = [struct.unpack_from("<I", raw, 16 + 4 * i)[0]
                        for i in range(self.count)]
        self.sections = []
        for o in self.offsets:
            assert raw[o:o + 4] == MAGIC_L, (o, raw[o:o + 4])
            n = struct.unpack_from("<I", raw, o + 12)[0]
            base = o + 16 + 4 * n
            offs = [struct.unpack_from("<I", raw, o + 16 + 4 * j)[0]
                    for j in range(n)]
            strs = []
            for so in offs:
                start = base + so
                if start >= len(raw):
                    strs.append("")
                    continue
                if self.utf16:
                    end = start
                    while end + 1 < len(raw) and raw[end:end + 2] != b"\x00\x00":
                        end += 2
                    strs.append(raw[start:end].decode("utf-16-le"))
                else:
                    end = raw.find(b"\x00", start)
                    if end < 0:
                        end = len(raw)
                    strs.append(raw[start:end].decode("latin1"))
            self.sections.append(strs)
        # remember the exact original bytes of each section so untouched
        # sections can be copied verbatim (their internal offset tables stay
        # valid; only modified sections are re-encoded)
        self._orig = list(self.sections)
        self._blobs = []
        for i, o in enumerate(self.offsets):
            end = self.offsets[i + 1] if i + 1 < self.count else len(raw)
            self._blobs.append(raw[o:end])

    def set_section(self, idx, strings):
        self.sections[idx] = strings

    def build(self):
        head = bytearray(self.raw[:self.offsets[0]])
        blobs = []
        for i, strs in enumerate(self.sections):
            if strs == self._orig[i]:
                blobs.append(self._blobs[i])          # verbatim
                continue
            body = bytearray()
            offs = []
            for s in strs:
                offs.append(len(body))
                if self.utf16:
                    body += s.encode("utf-16-le") + b"\x00\x00"
                else:
                    body += s.encode("latin1") + b"\x00"
            sec = bytearray(MAGIC_L)
            # size field counts the whole section:
            # LOCL+size+flags+count+offsets+body
            sec += struct.pack("<I", 16 + 4 * len(strs) + len(body))
            sec += struct.pack("<I", 0)               # flags
            sec += struct.pack("<I", len(strs))
            for off in offs:
                sec += struct.pack("<I", off)
            sec += body
            blobs.append(bytes(sec))
        cur = len(head)
        for i, blob in enumerate(blobs):
            struct.pack_into("<I", head, 16 + 4 * i, cur)
            cur += len(blob)
        return bytes(head) + b"".join(blobs)


def parse_stf(raw):
    return [ln.split("\t")
            for ln in raw.decode("latin1").split("\r\n") if ln.strip()]


if __name__ == "__main__":
    import glob
    for p in sorted(glob.glob("extracted/**/*.LOC", recursive=True)):
        raw = open(p, "rb").read()
        loc = Loc(raw)
        ok = loc.build() == raw
        firsts = [next((x for x in s if x.strip()), "")[:22]
                  for s in loc.sections]
        print(f"{p.split('/')[-1]:16s} {'u16' if loc.utf16 else 'u8 '} "
              f"secs={len(loc.sections):2d} n={len(loc.sections[0]):3d} "
              f"roundtrip={'OK' if ok else 'FAIL'}")
        print("      ", " | ".join(firsts))

#!/usr/bin/env python3
"""Parser for MoH:EA movie .LOC subtitle/overlay files.

Format (little endian):
    char[5]  magic  "LOCHD"
    char[3]  padding
    uint32   version
    uint32   num_languages
    uint32   lang_block_offsets[num_languages]
  each language block at its offset:
    char[4]  magic  "LOCL"
    uint32   block_size
    uint32   unknown (0)
    uint32   string_count
    uint32   string_offsets[string_count]   (relative to block start)
    ...      null-terminated strings

The file is used by the movie player to draw subtitles and the opening
title cards over the FMVs.  Each language block is independent, so a
localization only needs to rewrite one block's strings.
"""
import struct


class Loc:
    def __init__(self, raw, path=""):
        self.raw = raw
        self.path = path
        self.version = struct.unpack_from("<I", raw, 8)[0]
        self.num_languages = struct.unpack_from("<I", raw, 12)[0]
        self.lang_offsets = [struct.unpack_from("<I", raw, 16 + i * 4)[0]
                             for i in range(self.num_languages)]
        self.blocks = []
        for off in self.lang_offsets:
            self.blocks.append(self._parse_block(off))

    def _parse_block(self, off):
        magic = self.raw[off:off + 4]
        block_size = struct.unpack_from("<I", self.raw, off + 4)[0]
        cnt = struct.unpack_from("<I", self.raw, off + 12)[0]
        str_offs = [struct.unpack_from("<I", self.raw, off + 16 + i * 4)[0]
                    for i in range(cnt)]
        strings = []
        for so in str_offs:
            p = off + so
            end = self.raw.index(b"\x00", p)
            strings.append(self.raw[p:end].decode("latin1"))
        return {"magic": magic, "offset": off, "size": block_size,
                "strings": strings, "str_offsets": str_offs, "count": cnt}

    @staticmethod
    def build(blocks):
        """Serialise language blocks back to a .LOC byte stream.

        ``blocks`` is a list of lists of ``str`` (one list per language, in
        the same order as the original header).  Returns the full file bytes
        with recomputed block offsets and sizes.
        """
        n = len(blocks)
        header_size = 16 + 4 * n
        body = bytearray()
        offsets = []
        for strs in blocks:
            offsets.append(header_size + len(body))
            block = bytearray()
            block += b"LOCL"
            block += b"\x00" * 8                      # size (filled in later)
            block += struct.pack("<I", len(strs))
            str_off = 16 + 4 * len(strs)
            offs = []
            data = bytearray()
            for s in strs:
                offs.append(str_off + len(data))
                data += s.encode("latin1") + b"\x00"
            for o in offs:
                block += struct.pack("<I", o)
            block += data
            while len(block) % 4:                     # blocks are 4-byte aligned
                block += b"\x00"
            struct.pack_into("<I", block, 4, len(block))
            body += block
        out = bytearray(b"LOCHD\x00\x00\x00")
        out += struct.pack("<I", 0)
        out += struct.pack("<I", n)
        for o in offsets:
            out += struct.pack("<I", o)
        out += body
        return bytes(out)

    def rebuild(self):
        return self.build([b["strings"] for b in self.blocks])


if __name__ == "__main__":
    import sys
    loc = Loc(open(sys.argv[1], "rb").read(), sys.argv[1])
    print(f"{sys.argv[1]}: ver={loc.version} langs={loc.num_languages}")
    for i, b in enumerate(loc.blocks):
        print(f"  block {i}: size={b['size']} count={b['count']}")
        for s in b["strings"][:4]:
            print("     ", repr(s[:70]))

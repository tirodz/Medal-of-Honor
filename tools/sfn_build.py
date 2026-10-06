#!/usr/bin/env python3
"""EA SFN/FFN font builder for the PS2 'FntS' little-endian variant.

Layout (all offsets from the header):

  [0x00] header            32 bytes
  [0x20] font states       96 bytes (version >= 100)
  [cio ] character table   nch * 12 bytes (Character12)
  [    ] kerning table     optional, kio..sho
  [    ] image entry       name + padding + 16-byte EA image header
  [sho ] shape header      16 bytes
  [sho+16] glyph atlas     w*h/2 bytes, 4bpp, high nibble = left pixel
  [     ] atlas footer     48 bytes (constant metadata)
  [     ] trailer          336 bytes (palette / opaque, preserved)

Shape header: u8 record_id, u24le block_size (= pixels + 48), u16le w, u16le h,
then 8 zero bytes.

The engine only reads the character table, the shape header and the atlas, so a
rebuild that keeps those consistent is valid.  `rebuild()` reproduces the
original bytes exactly, which is the round-trip regression test.
"""
import struct

from sfn import SfnFont, CharEntry

FOOTER = 48


class SfnBuilder:
    def __init__(self, raw: bytes):
        self.raw = raw
        self.font = SfnFont.parse_bytes(raw)
        d = raw
        self.cio = self.font.char_info_offset
        self.nch = self.font.num_chars
        self.kio = self.font.kerning_offset
        self.sho = self.font.shape_offset
        self.entry_size = 12 if self.font.fmt == 0 else 16
        self.header = d[:0x20]
        self.fontstates = d[0x20:self.cio]
        self.char_table = d[self.cio:self.cio + self.nch * self.entry_size]
        self.mid = d[self.cio + self.nch * self.entry_size:self.sho]
        self.shape_hdr = d[self.sho:self.sho + 16]
        self.block_size = int.from_bytes(self.shape_hdr[1:4], "little")
        self.atlas_w = struct.unpack_from("<H", self.shape_hdr, 4)[0]
        self.atlas_h = struct.unpack_from("<H", self.shape_hdr, 6)[0]
        self.atlas_size = self.atlas_w * self.atlas_h // 2
        self.atlas = d[self.sho + 16:self.sho + 16 + self.atlas_size]
        self.footer = d[self.sho + 16 + self.atlas_size:self.sho + 16 + self.block_size]
        self.tail = d[self.sho + 16 + self.block_size:]

    # --- round-trip -------------------------------------------------------
    def rebuild(self):
        return (self.header + self.fontstates + self.char_table + self.mid
                + self.shape_hdr + self.atlas + self.footer + self.tail)

    # --- extension --------------------------------------------------------
    def add_glyphs(self, new_chars, new_rows, new_width=None):
        """Append glyph rows to the atlas and glyph entries to the table.

        new_chars : list[CharEntry] with (u, v) into the extended atlas
        new_rows  : list[bytes], each a full atlas row of width new_width
        new_width : new atlas width (default: keep current width)
        """
        w = new_width or self.atlas_w
        if w != self.atlas_w:
            raise ValueError("atlas width changes are not supported")
        new_h = self.atlas_h + len(new_rows)
        new_atlas = self.atlas + b"".join(new_rows)
        assert len(new_atlas) == w * new_h // 2

        ctab = bytearray(self.char_table)
        for c in new_chars:
            if self.entry_size == 12:
                ctab += struct.pack("<HBBHHBBBB", c.code, c.width, c.height,
                                    c.u, c.v, c.advance, c.x_offset, c.y_offset, 0)
            else:
                ctab += struct.pack("<HBBHHBBBBHH", c.code, c.width, c.height,
                                    c.u, c.v, c.advance_y, c.x_offset, c.y_offset,
                                    0, 0, c.advance)

        sh = bytearray(self.shape_hdr)
        sh[1:4] = (len(new_atlas) + FOOTER).to_bytes(3, "little")
        struct.pack_into("<H", sh, 4, w)
        struct.pack_into("<H", sh, 6, new_h)

        header = bytearray(self.header)
        struct.pack_into("<H", header, 10, self.nch + len(new_chars))
        struct.pack_into("<I", header, 20, self.cio)
        struct.pack_into("<I", header, 24, self.kio)
        new_sho = self.cio + len(ctab) + len(self.mid)
        struct.pack_into("<I", header, 28, new_sho)
        out = bytearray(bytes(header) + self.fontstates + bytes(ctab) + self.mid
                        + bytes(sh) + new_atlas + self.footer + self.tail)
        struct.pack_into("<I", out, 4, len(out))
        return bytes(out)


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        raw = open(p, "rb").read()
        b = SfnBuilder(raw)
        print(f"{p}: nch={b.nch} atlas={b.atlas_w}x{b.atlas_h} "
              f"block={b.block_size} footer={len(b.footer)} tail={len(b.tail)} "
              f"roundtrip={'OK' if b.rebuild() == raw else 'DIFF'}")

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
        # After the character table come (in this order) the optional kerning
        # table and the EA image entry, up to the shape header.  The kerning
        # table must be relocated when the character table grows, otherwise the
        # header offset points into the appended glyph entries.
        ctab_end = self.cio + self.nch * self.entry_size
        if self.kio:
            nk = struct.unpack_from("<I", d, self.kio)[0]
            kern_size = 4 + nk * 4          # version >= 310 entry is 4 bytes
            self.kern_block = d[self.kio:self.kio + kern_size]
            self.image_entry = d[self.kio + kern_size:self.sho]
        else:
            self.kern_block = b""
            self.image_entry = d[ctab_end:self.sho]
        self.shape_hdr = d[self.sho:self.sho + 16]
        self.block_size = int.from_bytes(self.shape_hdr[1:4], "little")
        self.atlas_w = struct.unpack_from("<H", self.shape_hdr, 4)[0]
        self.atlas_h = struct.unpack_from("<H", self.shape_hdr, 6)[0]
        self.atlas_size = self.atlas_w * self.atlas_h // 2
        # The EA image entry that precedes the shape header carries a duplicate
        # copy of the atlas geometry in its last 28 bytes:
        #   [-28] block size (pixels + 48), [-24] 48, [-20] pixel bytes,
        #   [-8]  atlas width,               [-4]  atlas height
        # The engine reads the *image entry* copy (not the shape header) to size
        # the texture, so it must be kept in sync whenever the atlas grows.
        self._entry_tail = len(self.image_entry) >= 28
        self.atlas = d[self.sho + 16:self.sho + 16 + self.atlas_size]
        self.footer = d[self.sho + 16 + self.atlas_size:self.sho + 16 + self.block_size]
        self.tail = d[self.sho + 16 + self.block_size:]

    # --- round-trip -------------------------------------------------------
    def rebuild(self):
        return (self.header + self.fontstates + self.char_table
                + self.kern_block + self.image_entry
                + self.shape_hdr + self.atlas + self.footer + self.tail)

    # --- extension --------------------------------------------------------
    def _pack_entry(self, c):
        if self.entry_size == 12:
            return struct.pack("<HBBHHbbbB", c.code, c.width, c.height,
                               c.u, c.v, c.advance, c.x_offset, c.y_offset, 0)
        return struct.pack("<HBBHHBbbBHH", c.code, c.width, c.height,
                           c.u, c.v, c.advance_y, c.x_offset, c.y_offset,
                           0, 0, c.advance)

    def _pack_sorted(self, chars):
        """Pack the character table with entries ordered by ascending code.

        The engine locates glyphs by their code in this table, so a code that
        is appended out of order (e.g. the Arabic-block punctuation 0x060C..
        landing after an existing 0x2122) makes the lookup miss.  Sorting is
        safe because each entry carries its own metrics and the kerning table
        is keyed by code, not by table position.
        """
        return b"".join(self._pack_entry(c) for c in sorted(chars, key=lambda c: c.code))

    def _emit(self, ctab, new_rows, new_width):
        w = new_width or self.atlas_w
        if w != self.atlas_w:
            raise ValueError("atlas width changes are not supported")
        new_h = self.atlas_h + len(new_rows)
        new_atlas = self.atlas + b"".join(new_rows)
        assert len(new_atlas) == w * new_h // 2

        sh = bytearray(self.shape_hdr)
        sh[1:4] = (len(new_atlas) + FOOTER).to_bytes(3, "little")
        struct.pack_into("<H", sh, 4, w)
        struct.pack_into("<H", sh, 6, new_h)

        # Keep the duplicate geometry in the image entry in sync, otherwise the
        # engine sizes/clips the texture using the stale (smaller) height and
        # every glyph appended beyond the original atlas is dropped.
        entry = bytearray(self.image_entry)
        if self._entry_tail:
            nblk = len(new_atlas) + FOOTER
            struct.pack_into("<I", entry, len(entry) - 28, nblk)
            struct.pack_into("<I", entry, len(entry) - 20, len(new_atlas))
            struct.pack_into("<I", entry, len(entry) - 8, w)
            struct.pack_into("<I", entry, len(entry) - 4, new_h)

        header = bytearray(self.header)
        struct.pack_into("<H", header, 10, len(ctab) // self.entry_size)
        struct.pack_into("<I", header, 20, self.cio)
        new_kio = self.cio + len(ctab) if self.kern_block else 0
        struct.pack_into("<I", header, 24, new_kio)
        new_sho = self.cio + len(ctab) + len(self.kern_block) + len(entry)
        struct.pack_into("<I", header, 28, new_sho)
        out = bytearray(bytes(header) + self.fontstates + bytes(ctab)
                        + self.kern_block + bytes(entry)
                        + bytes(sh) + new_atlas + self.footer + self.tail)
        struct.pack_into("<I", out, 4, len(out))
        return bytes(out)

    def add_glyphs(self, new_chars, new_rows, new_width=None):
        """Append glyph rows to the atlas and glyph entries to the table.

        new_chars : list[CharEntry] with (u, v) into the extended atlas
        new_rows  : list[bytes], each a full atlas row of width new_width
        new_width : new atlas width (default: keep current width)
        """
        ctab = self._pack_sorted(self.font.chars + list(new_chars))
        return self._emit(ctab, new_rows, new_width)

    def replace_chars(self, kept_chars, new_chars, new_rows, new_width=None):
        """Rebuild the character table from an explicit glyph set.

        Used to drop a range of existing glyphs (freeing their code slots)
        while preserving the remaining ones and appending new glyphs.  The
        combined set is emitted in ascending code order.
        """
        ctab = self._pack_sorted(list(kept_chars) + list(new_chars))
        return self._emit(ctab, new_rows, new_width)

    def replace_glyphs(self, replacements, new_rows):
        """Point existing glyph entries at new bitmaps, keeping the table shape.

        ``replacements`` maps an existing code to a CharEntry whose (u, v)
        address the extended atlas.  The entry count, code order and therefore
        the kerning indices are all preserved, so a font can have a block of
        glyphs (e.g. Latin-1) overwritten with new shapes without disturbing
        anything that references glyph positions.
        """
        ctab = bytearray()
        for c in self.font.chars:
            r = replacements.get(c.code)
            ctab += self._pack_entry(r if r is not None else c)
        return self._emit(ctab, new_rows, None)


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        raw = open(p, "rb").read()
        b = SfnBuilder(raw)
        print(f"{p}: nch={b.nch} atlas={b.atlas_w}x{b.atlas_h} "
              f"block={b.block_size} footer={len(b.footer)} tail={len(b.tail)} "
              f"roundtrip={'OK' if b.rebuild() == raw else 'DIFF'}")

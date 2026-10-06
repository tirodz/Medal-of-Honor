#!/usr/bin/env python3
"""EA SFN/FFN/XFN font parser (PS2 'FntS' little-endian variant).

Format reference: rewiki EA_FFN_SFN_Font + EA-Font-Manager (Bartlomiej Duda).
Header (little endian):
  char signature[4]
  u32 total_file_size
  u16 version
  u16 number_of_characters
  u32 font_flags
  u8 center_x, center_y, ascent, descent
  u32 char_info_table_offset
  u32 kerning_table_offset
  u32 shape_header_offset
Character entry (Character12, format_flag==0), 12 bytes:
  u16 char_index (unicode), u8 width, u8 height, u16 u, u16 v,
  u8 advance, u8 x_offset, u8 y_offset
"""
import struct
from dataclasses import dataclass, field


def get_bits(value, num_bits, start_bit):
    return (value >> start_bit) & ((1 << num_bits) - 1)


BASELINE = {0: "Roman", 1: "Ideographic", 2: "Hanging/Arabic"}
ENCODING = {0: "ASCII/8-bit", 1: "UTF-16", 2: "Shift-JIS", 3: "?"}
DIRECTION = {0: "LTR", 1: "RTL"}


@dataclass
class CharEntry:
    code: int
    width: int
    height: int
    u: int
    v: int
    advance: int          # advance_x (horizontal pen movement)
    x_offset: int
    y_offset: int
    num_kern: int = 0
    advance_y: int = 0
    kern_index: int = 0


@dataclass
class SfnFont:
    path: str
    signature: str = ""
    total_size: int = 0
    version: int = 0
    num_chars: int = 0
    flags: int = 0
    center_x: int = 0
    center_y: int = 0
    ascent: int = 0
    descent: int = 0
    char_info_offset: int = 0
    kerning_offset: int = 0
    shape_offset: int = 0
    # decoded flags
    antialiased: int = 0
    dropshadow: int = 0
    outline: int = 0
    vram: int = 0
    baseline: int = 0
    orientation: int = 0
    direction: int = 0
    encoding: int = 0
    fmt: int = 0
    chars: list = field(default_factory=list)
    raw: bytes = b""

    @classmethod
    def parse(cls, path):
        with open(path, "rb") as f:
            data = f.read()
        o = cls.parse_bytes(data, path)
        return o

    @classmethod
    def parse_bytes(cls, data, path=""):
        o = cls(path=path, raw=data)
        o.signature = data[0:4].decode("latin1")
        (o.total_size, o.version, o.num_chars, o.flags) = struct.unpack_from("<IHHI", data, 4)
        (o.center_x, o.center_y, o.ascent, o.descent) = struct.unpack_from("<BBBB", data, 16)
        (o.char_info_offset, o.kerning_offset, o.shape_offset) = struct.unpack_from("<III", data, 20)
        o.antialiased = get_bits(o.flags, 1, 0)
        o.dropshadow = get_bits(o.flags, 1, 1)
        o.outline = get_bits(o.flags, 1, 2)
        o.vram = get_bits(o.flags, 1, 3)
        o.baseline = get_bits(o.flags, 2, 8)
        o.orientation = get_bits(o.flags, 1, 10)
        o.direction = get_bits(o.flags, 1, 11)
        o.encoding = get_bits(o.flags, 2, 16)
        o.fmt = get_bits(o.flags, 1, 18)
        # Character12 (fmt 0, 12 bytes) or Character16 (fmt 1, 16 bytes)
        pos = o.char_info_offset
        if o.fmt == 0:
            for i in range(o.num_chars):
                (code, w, h, u, v, adv, xo, yo) = struct.unpack_from("<HBBHHBBB", data, pos)
                o.chars.append(CharEntry(code, w, h, u, v, adv, xo, yo))
                pos += 12
        else:
            for i in range(o.num_chars):
                (code, w, h, u, v, adv_y, xo, yo, nk, ki, adv_x) = \
                    struct.unpack_from("<HBBHHBBBBHH", data, pos)
                o.chars.append(CharEntry(code, w, h, u, v, adv_x, xo, yo,
                                         num_kern=nk, advance_y=adv_y, kern_index=ki))
                pos += 16
        return o

    def summary(self):
        return (f"{self.path.split('/')[-1]}: sig={self.signature} ver={self.version} "
                f"nchars={self.num_chars} flags=0x{self.flags:08x} "
                f"baseline={BASELINE.get(self.baseline, self.baseline)} "
                f"dir={DIRECTION.get(self.direction, self.direction)} "
                f"enc={ENCODING.get(self.encoding, self.encoding)} fmt={self.fmt} "
                f"ascent={self.ascent} descent={self.descent} center=({self.center_x},{self.center_y})")


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        f = SfnFont.parse(p)
        print(f.summary())
        print("  codes:", " ".join(f"{c.code:04x}" for c in f.chars[:48]))

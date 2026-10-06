#!/usr/bin/env python3
"""PS2 PAL4 (4bpp indexed) glyph atlas encode/decode.

The font atlas is a raw 4bpp bitmap: two pixels per byte, the high nibble is
the left pixel.  Values are palette indices; the font palette is a linear
grayscale ramp (index i -> alpha i*17), so an index is also an 0..15 intensity.
"""
from PIL import Image


def decode(data, width, height):
    """Return a PIL 'L' image (0..15) from a 4bpp atlas."""
    img = Image.new("L", (width, height))
    px = img.load()
    half = width // 2
    for y in range(height):
        row = y * half
        for x in range(width):
            b = data[row + x // 2]
            px[x, y] = (b >> 4) if x % 2 == 0 else (b & 0xF)
    return img


def encode(img):
    """Encode a PIL 'L' image (values 0..15) into a 4bpp atlas."""
    width, height = img.size
    px = img.load()
    out = bytearray(height * (width // 2))
    half = width // 2
    for y in range(height):
        row = y * half
        for x in range(0, width, 2):
            hi = px[x, y] & 0xF
            lo = px[x + 1, y] & 0xF if x + 1 < width else 0
            out[row + x // 2] = (hi << 4) | lo
    return bytes(out)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, __import__("os").path.dirname(__file__))
    from tools.viv import Viv
    from sfn_build import SfnBuilder
    v = Viv.parse("extracted/MOH4/DATA/SHARED/UI/FE/REALFONT.VIV")
    b = SfnBuilder(v.get("Courier New_18.sfn").data)
    img = decode(b.atlas, b.atlas_w, b.atlas_h)
    print("atlas roundtrip:", "OK" if encode(img) == b.atlas else "DIFF")

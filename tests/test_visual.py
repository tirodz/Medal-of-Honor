#!/usr/bin/env python3
"""Visual regression suite for the Arabic localization.

Renders a fixed corpus through every *built* SFN font using the
renderer-faithful harness (real glyph atlas + real metrics) and compares the
result against stored goldens.  Also asserts glyph coverage and baseline
alignment, which a byte round-trip alone cannot catch.

Run:            python3 tests/test_visual.py
Regenerate:     python3 tests/test_visual.py --regen
"""
import glob
import json
import os
import sys
import unittest

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))

from tools.render_ui import SfnRenderer  # noqa: E402
from tools.sfn import SfnFont  # noqa: E402

BUILD = os.path.join(HERE, "build", "fonts")
GOLDEN = os.path.join(HERE, "tests", "golden")
REALF = os.path.join(HERE, "translations", "ar_final.json")

CORPUS = [
    "مرحبا",
    "ثلاث دبابات",
    "دمّر مدفعية العدو.",
    "دُمّرت 2 من 3 دبابات",
    "قنبلة، مدفع؛ نعم!",
    "المهمة 2 - عملية: صمت V2",
    "(من 2 إلى 4 لاعبين)",
    "هل أنت متأكد؟",
    "50%",
    "R1",
    "START",
    "أوقف الخصم قبل وصول التعزيزات إلى المدينة القديمة",
]


def built_fonts():
    out = []
    for p in sorted(glob.glob(os.path.join(BUILD, "*.SFN"))):
        out.append((os.path.basename(p), open(p, "rb").read()))
    for p in sorted(glob.glob(os.path.join(BUILD, "REALF*"))):
        out.append((os.path.basename(p), open(p, "rb").read()))
    return out


def sheet_for(name, raw):
    r = SfnRenderer(raw, name)
    imgs = [r.render(t) for t in CORPUS]
    w = max(i.width for i in imgs) + 4
    h = sum(i.height + 4 for i in imgs)
    sheet = Image.new("L", (w, h), 0)
    y = 0
    for i in imgs:
        sheet.paste(i, (2, y))
        y += i.height + 4
    return sheet, r


def _regen():
    os.makedirs(GOLDEN, exist_ok=True)
    for name, raw in built_fonts():
        sheet, _ = sheet_for(name, raw)
        sheet.save(os.path.join(GOLDEN, name + ".png"))
    print("regenerated", len(built_fonts()), "goldens in", GOLDEN)


@unittest.skipUnless(os.path.isdir(BUILD), "built fonts not present")
class TestVisual(unittest.TestCase):
    def test_glyph_coverage_all_fonts(self):
        used = set()
        for v in json.load(open(REALF)).values():
            used.update(v)
        codes = {ord(c) for c in used if c not in "\x00\t\n"}
        for name, raw in built_fonts():
            have = {c.code for c in SfnFont.parse_bytes(raw).chars}
            missing = sorted(codes - have)
            with self.subTest(font=name):
                self.assertEqual(missing, [], [hex(c) for c in missing[:8]])

    def test_baseline_alignment(self):
        # Arabic alef (isolated) must sit on the same baseline row as Latin 'H'.
        for name, raw in built_fonts():
            f = SfnFont.parse_bytes(raw)
            h = [c for c in f.chars if c.code == ord("H")]
            a = [c for c in f.chars if c.code == 0xFE8D]
            if not h or not a:
                continue
            hb = h[0].y_offset + h[0].height
            ab = a[0].y_offset + a[0].height
            with self.subTest(font=name):
                self.assertLessEqual(abs(hb - ab), 2, f"Latin={hb} Arabic={ab}")

    def test_golden_renders(self):
        if not os.path.isdir(GOLDEN):
            self.skipTest("no goldens; run with --regen")
        for name, raw in built_fonts():
            gp = os.path.join(GOLDEN, name + ".png")
            if not os.path.exists(gp):
                self.skipTest("missing golden " + gp)
            sheet, _ = sheet_for(name, raw)
            gold = Image.open(gp).convert("L")
            with self.subTest(font=name):
                self.assertEqual(sheet.size, gold.size)
                a = np.asarray(sheet, dtype=int)
                b = np.asarray(gold, dtype=int)
                diff = float(np.mean(np.abs(a - b)))
                self.assertLess(diff, 1.0, f"mean pixel diff {diff:.3f}")


if __name__ == "__main__":
    if "--regen" in sys.argv:
        _regen()
    else:
        unittest.main(argv=[sys.argv[0]])

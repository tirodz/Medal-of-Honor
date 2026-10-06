#!/usr/bin/env python3
"""Regression tests for the movie .LOC subtitle pipeline.

Covers the three things that must not silently break:
  * the .LOC reader/writer round-trips every shipped file byte-for-byte,
  * the Arabic movie translations only use bytes the movie font provides,
  * the byte-addressed movie fonts keep the Latin and 16-bit Arabic glyphs.
"""
import glob
import importlib.util
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))

import tools.arabic as ar  # noqa: E402
from tools.loc import Loc  # noqa: E402
from tools.sfn import SfnFont  # noqa: E402

LOC_DIR = os.path.join(HERE, "extracted/MOH4/DATA/SHARED/MOVIES/LOC")
MAP = os.path.join(HERE, "build/fonts/movie_byte_map.json")
FONTS = os.path.join(HERE, "build/fonts")


def _load_ar():
    spec = importlib.util.spec_from_file_location(
        "loc_ar", os.path.join(HERE, "translations", "loc_ar.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.AR


class TestLocRoundtrip(unittest.TestCase):
    def test_every_loc_roundtrips(self):
        files = sorted(glob.glob(os.path.join(LOC_DIR, "*.LOC")))
        self.assertGreater(len(files), 0)
        for f in files:
            raw = open(f, "rb").read()
            self.assertEqual(Loc(raw).rebuild(), raw, os.path.basename(f))

    def test_language_block_count_preserved(self):
        f = os.path.join(LOC_DIR, "STNMINTR.LOC")
        loc = Loc(open(f, "rb").read())
        self.assertEqual(len(loc.blocks), loc.num_languages)
        self.assertEqual(loc.blocks[0]["count"], loc.blocks[1]["count"])


class TestMovieTranslations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.AR = _load_ar()
        cls.bmap = {int(k): v for k, v in json.load(open(MAP)).items()}
        cls.rows = json.load(open(os.path.join(HERE, "translations", "loc_strings.json")))

    def test_full_coverage(self):
        ids = {r["id"] for r in self.rows}
        missing = sorted(i for i in ids if i not in self.AR)
        self.assertEqual(missing, [], f"untranslated movie strings: {missing}")

    def test_every_shaped_form_has_a_byte(self):
        for r in self.rows:
            shaped = ar.process(self.AR[r["id"]])
            for ch in shaped:
                o = ord(ch)
                if o < 0x80:
                    continue
                self.assertIn(o, self.bmap,
                              f"{r['id']}: U+{o:04X} not in movie byte map")

    def test_byte_map_is_within_one_byte(self):
        for cp, b in self.bmap.items():
            self.assertTrue(0x80 <= b <= 0xFF, f"U+{cp:04X}->0x{b:02X}")

    def test_encoding_is_reversible(self):
        rev = {v: k for k, v in self.bmap.items()}
        for r in self.rows:
            shaped = ar.process(self.AR[r["id"]])
            encoded = [self.bmap.get(ord(c), ord(c)) for c in shaped]
            decoded = "".join(chr(rev[b]) if b >= 0x80 else chr(b) for b in encoded)
            self.assertEqual(decoded, shaped, r["id"])


@unittest.skipUnless(os.path.isdir(FONTS), "built fonts not present")
class TestMovieFonts(unittest.TestCase):
    def test_fonts_keep_latin_and_both_arabic_ranges(self):
        for name in ("SUBFNT.SFN", "OBJFONT.SFN"):
            fo = SfnFont.parse(os.path.join(FONTS, name))
            codes = {c.code for c in fo.chars}
            self.assertTrue({ord(c) for c in "AZaz09"} <= codes, name)
            self.assertTrue(any(c > 0xFF for c in codes), f"{name}: 16-bit Arabic")
            self.assertTrue(any(0x80 <= c <= 0xFF for c in codes), f"{name}: byte Arabic")

    def test_every_mapped_byte_has_a_glyph(self):
        bmap = {int(k): v for k, v in json.load(open(MAP)).items()}
        for name in ("SUBFNT.SFN", "OBJFONT.SFN"):
            codes = {c.code for c in SfnFont.parse(os.path.join(FONTS, name)).chars}
            missing = sorted({v for v in bmap.values()} - codes)
            self.assertEqual(missing, [], f"{name}: missing byte glyphs {missing}")


if __name__ == "__main__":
    unittest.main()

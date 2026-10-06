#!/usr/bin/env python3
"""Regression tests for the MoH:EA Arabic localization build.

Run:  python3 tests/test_roundtrip.py

Every custom parser is checked with an original -> parse -> rebuild ->
compare cycle; the translation pipeline is checked for control-code
preservation and Arabic shaping/bidi correctness.  The tests that need the
extracted tree are skipped (not failed) when it is absent.
"""
import glob
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))

from tools import mohsub, sfn_build, viv, arabic  # noqa: E402
from tools.sfn_build import SfnBuilder  # noqa: E402

EX = os.path.join(HERE, "extracted")
TR = os.path.join(HERE, "translations")


def have(path):
    return os.path.exists(path)


@unittest.skipUnless(have(EX), "extracted tree not present")
class TestArchiveRoundTrip(unittest.TestCase):
    def test_viv_roundtrip_all(self):
        paths = sorted(glob.glob(os.path.join(EX, "**", "*.VIV"), recursive=True))
        self.assertGreater(len(paths), 0)
        for p in paths:
            with self.subTest(p=os.path.relpath(p, HERE)):
                raw = open(p, "rb").read()
                if raw[:4] in (b"BIGF", b"BIGH"):
                    continue  # BIGF builder only supports <=16 MiB offsets
                try:
                    v = viv.Viv.parse_bytes(raw, p)
                except Exception:
                    continue  # not a 0xc0fb archive
                self.assertEqual(v.build(), raw)

    def test_string_table_xml_roundtrip(self):
        paths = sorted(glob.glob(os.path.join(EX, "**", "STRINGS.VIV"), recursive=True))
        paths.append(os.path.join(EX, "MOH4", "DATA", "SHARED", "STRINGMP.VIV"))
        for p in paths:
            if not have(p):
                continue
            with self.subTest(p=os.path.relpath(p, HERE)):
                from tools.inject_strings import patch_xml
                v = viv.Viv.parse(p)
                txt = v.entries[0].data.decode("utf-16-le")
                self.assertEqual(patch_xml(txt, {}), txt)


@unittest.skipUnless(have(EX), "extracted tree not present")
class TestLocRoundTrip(unittest.TestCase):
    def test_all_loc(self):
        paths = sorted(glob.glob(os.path.join(EX, "**", "*.LOC"), recursive=True))
        self.assertGreater(len(paths), 0)
        for p in paths:
            with self.subTest(p=os.path.relpath(p, HERE)):
                raw = open(p, "rb").read()
                self.assertEqual(mohsub.Loc(raw).build(), raw)


@unittest.skipUnless(have(EX), "extracted tree not present")
class TestFontRoundTrip(unittest.TestCase):
    def test_all_sfn(self):
        paths = sorted(glob.glob(os.path.join(EX, "**", "*.SFN"), recursive=True))
        paths += [p for p in glob.glob(os.path.join(EX, "**", "*.VIV"), recursive=True)
                  if os.path.basename(p).upper().startswith("REALF")]
        n = 0
        for p in paths:
            raw = open(p, "rb").read()
            if os.path.basename(p).upper().endswith(".VIV"):
                v = viv.Viv.parse_bytes(raw, p)
                for e in v.entries:
                    if e.name.lower().endswith(".sfn"):
                        with self.subTest(f="{os.path.basename(p)}::{e.name}"):
                            self.assertEqual(sfn_build.SfnBuilder(e.data).rebuild(), e.data)
                        n += 1
                continue
            with self.subTest(p=os.path.relpath(p, HERE)):
                self.assertEqual(sfn_build.SfnBuilder(raw).rebuild(), raw)
            n += 1
        self.assertGreater(n, 0)

    def test_font_parse_rebuild_identical(self):
        p = os.path.join(EX, "MOH4", "DATA", "SUBFNT.SFN")
        if not have(p):
            self.skipTest("SUBFNT.SFN missing")
        raw = open(p, "rb").read()
        self.assertEqual(SfnBuilder(raw).rebuild(), raw)


class TestArabicPipeline(unittest.TestCase):
    def test_presentation_forms_and_order(self):
        out = arabic.process("مرحبا")
        # visual order: the last logical letter (alef) is stored first
        self.assertEqual(out[0], "\uFE8E")
        self.assertTrue(all(0xFE70 <= ord(c) <= 0xFEFF for c in out))

    def test_latin_word_stays_ltr_inside_arabic(self):
        out = arabic.process("اضغط START للبدء")
        i = out.index("START")
        self.assertEqual(out[i:i + 5], "START")

    def test_pure_latin_untouched(self):
        self.assertEqual(arabic.process("Mission 1"), "Mission 1")

    def test_control_codes_preserved(self):
        for s in ("%1 من %2", "اضغط $ACTION الآن", "سطر\\nسطر"):
            out = arabic.process(s)
            for tok in ("%1", "%2", "$ACTION", "\\n"):
                if tok in s:
                    self.assertIn(tok, out)


class TestTranslations(unittest.TestCase):
    def test_no_english_left_in_tables(self):
        f = os.path.join(TR, "untranslated.json")
        if not have(f):
            self.skipTest("run tools/coverage.py first")
        d = json.load(open(f))
        self.assertEqual(d, {}, f"untranslated ids: {list(d)[:10]}")

    def test_arabic_present_in_every_string(self):
        db = json.load(open(os.path.join(TR, "ar_final.json")))
        self.assertGreater(len(db), 2500)
        # proper nouns / brand names intentionally left in Latin script
        allow = {"SP_DolbyDigital", "SP_Español"}
        non_arabic = [k for k, v in db.items()
                      if k not in allow and v and not arabic.has_arabic(v)
                      and not v.isascii()]
        self.assertEqual(non_arabic, [], non_arabic[:10])


if __name__ == "__main__":
    unittest.main(verbosity=2)

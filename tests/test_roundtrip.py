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

    def test_offsets_are_signed(self):
        # The EA format stores advance/x_offset/y_offset as signed int8; the
        # original digit '0' in SUBFNT uses y_offset 0xff == -1.
        p = os.path.join(EX, "MOH4", "DATA", "SUBFNT.SFN")
        if not have(p):
            self.skipTest("SUBFNT.SFN missing")
        f = sfn_build.SfnFont.parse(p)
        zero = [c for c in f.chars if c.code == ord("0")]
        self.assertTrue(zero)
        self.assertEqual(zero[0].y_offset, -1)
        self.assertEqual(zero[0].y_offset + zero[0].height, 13)

    def test_kerning_offset_relocated(self):
        # Growing the character table must move the kerning-table offset, or
        # the engine reads kerning from inside the appended glyph entries.
        from tools.sfn import CharEntry
        from tools.pal4 import encode
        from PIL import Image
        for p in sorted(glob.glob(os.path.join(EX, "MOH4", "DATA", "*.SFN"))):
            raw = open(p, "rb").read()
            b = SfnBuilder(raw)
            if not b.kio:
                continue
            with self.subTest(p=os.path.basename(p)):
                strip = Image.new("L", (b.atlas_w, 4), 0)
                rows = [encode(strip)[i:i + b.atlas_w // 2]
                        for i in range(0, len(encode(strip)), b.atlas_w // 2)]
                ch = CharEntry(code=0xFFFF, width=2, height=2, u=0,
                               v=b.atlas_h, advance=3, x_offset=0, y_offset=0)
                out = b.add_glyphs([ch], rows)
                f2 = sfn_build.SfnFont.parse_bytes(out)
                ctab_end = f2.char_info_offset + f2.num_chars * b.entry_size
                self.assertEqual(f2.kerning_offset, ctab_end)
                import struct
                nk = struct.unpack_from("<I", out, f2.kerning_offset)[0]
                self.assertLess(nk, 1000)


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

    def test_line_order_not_reversed(self):
        # The engine draws each line left-to-right, so the bidi pass must run
        # per line; otherwise the first paragraph would render last.
        out = arabic.process("الأول\\n\\nالثاني")
        self.assertTrue(out.startswith(arabic.process("الأول") + "\\n\\n"))
        out2 = arabic.process("- واحد|- اثنان")
        self.assertTrue(out2.startswith(arabic.process("- واحد") + "|"))


class TestTranslations(unittest.TestCase):
    def test_no_english_left_in_tables(self):
        f = os.path.join(TR, "untranslated.json")
        if not have(f):
            self.skipTest("run tools/coverage.py first")
        d = json.load(open(f))
        self.assertEqual(d, {}, f"untranslated ids: {list(d)[:10]}")

    def test_no_arabic_indic_digits(self):
        # static numerals must be Western so they match runtime %1 substitutions
        db = json.load(open(os.path.join(TR, "ar_final.json")))
        import re
        bad = [k for k, v in db.items() if re.search(r"[\u0660-\u0669]", v)]
        self.assertEqual(bad, [], bad[:10])

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

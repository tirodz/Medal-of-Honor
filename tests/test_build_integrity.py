#!/usr/bin/env python3
"""Integrity tests for the built tree.

These guard the failure modes that a per-tool round-trip cannot catch:
  * every built STRINGS.VIV is still well-formed XML (the injector must escape
    `"` as `&quot;`, exactly like the shipped English does),
  * every STF-referenced subtitle resolves to an Arabic string in its .LOC,
  * the save-game .LOC tables decode back to Arabic.
Skipped (not failed) when build/ is absent.
"""
import glob
import importlib.util
import os
import struct
import sys
import unittest
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))

import tools.arabic as ar  # noqa: E402
from tools.viv import Viv  # noqa: E402

BUILD = os.path.join(HERE, "build", "tree")
EX = os.path.join(HERE, "extracted")


@unittest.skipUnless(os.path.isdir(BUILD), "build tree not present")
class TestBuiltStrings(unittest.TestCase):
    def test_all_built_strings_are_wellformed_xml(self):
        files = sorted(glob.glob(os.path.join(BUILD, "**", "STRINGS*.VIV"), recursive=True))
        self.assertGreater(len(files), 0)
        for p in files:
            with self.subTest(p=os.path.relpath(p, BUILD)):
                v = Viv.parse(p)
                for e in v.entries:
                    ET.fromstring(e.data.decode("utf-16-le"))  # raises on bad XML

    def test_built_strings_are_arabic(self):
        p = os.path.join(BUILD, "MOH4/DATA/SHARED/STRINGS.VIV")
        v = Viv.parse(p)
        vals = []
        for e in v.entries:
            root = ET.fromstring(e.data.decode("utf-16-le"))
            for s in list(root.iter("localstring")) + list(root.iter("globalstring")):
                for c in s:
                    if c.tag == "english":
                        vals.append(c.get("value", ""))
        self.assertGreater(len(vals), 0)
        arabic = [v for v in vals if ar.has_arabic(v)]
        # every string with letters must be Arabic; the remainder are codes,
        # language names and proper nouns
        self.assertGreater(len(arabic) / len(vals), 0.95)


@unittest.skipUnless(os.path.isdir(os.path.join(BUILD, "MOH4/DATA/SAVEGAME")), "no savegame")
class TestSaveGame(unittest.TestCase):
    def test_savegame_decodes_to_arabic(self):
        import struct
        from tools.inject_savegame import split_parts
        for fn in ("SAVEGAME.LOC", "SG_MISC.LOC"):
            p = os.path.join(BUILD, "MOH4/DATA/SAVEGAME", fn)
            raw = open(p, "rb").read()
            o = struct.unpack_from("<I", raw, 16)[0]
            n = struct.unpack_from("<I", raw, o + 12)[0]
            parts, _ = split_parts(raw[o + 16 + 4 * n:])
            blob = "".join(parts)
            with self.subTest(fn=fn):
                self.assertTrue(ar.has_arabic(blob), fn + " has no Arabic")


class TestPlaceholders(unittest.TestCase):
    def test_format_codes_are_not_reordered(self):
        """%s / %d must stay intact - bidi would otherwise flip them to s% / d%."""
        import re
        from tools.arabic import process
        for src in ("أدخل البطاقة في المنفذ %s.",
                    "يرجى الضغط على %d للمتابعة"):
            out = process(src)
            with self.subTest(src=src):
                self.assertIn("%", out)
                self.assertIsNone(re.search(r"[A-Za-z]%", out), out)

    @unittest.skipUnless(os.path.exists(os.path.join(HERE, "translations/ar_final.json")),
                         "no shaped DB")
    def test_shaped_db_has_no_reversed_placeholders(self):
        import json
        import re
        db = json.load(open(os.path.join(HERE, "translations/ar_final.json")))
        bad = [k for k, v in db.items() if re.search(r"[A-Za-z]%", v)]
        self.assertEqual(bad, [], f"{len(bad)} strings have reversed placeholders")


class TestMovieCoverage(unittest.TestCase):
    def test_every_referenced_subtitle_is_translated(self):
        from tools.loc import Loc
        spec = importlib.util.spec_from_file_location(
            "loc_ar", os.path.join(HERE, "translations", "loc_ar.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        AR = mod.AR
        total = miss = 0
        for stf in sorted(glob.glob(os.path.join(EX, "MOH4/DATA/SHARED/MOVIES/STF/US/*.STF"))):
            movie = os.path.splitext(os.path.basename(stf))[0]
            loc = Loc(open(os.path.join(EX, "MOH4/DATA/SHARED/MOVIES/LOC", movie + ".LOC"), "rb").read())
            en = loc.blocks[0]["strings"]
            for ln in open(stf, encoding="latin1").read().splitlines():
                if not ln or ln.startswith("FRAME"):
                    continue
                f = ln.split("\t")
                if len(f) > 1 and f[1].strip():
                    i = int(f[1])
                    if i < len(en) and en[i].strip():
                        total += 1
                        if "LOC_%s_%03d" % (movie, i) not in AR:
                            miss += 1
        self.assertGreater(total, 0)
        self.assertEqual(miss, 0, f"{miss} referenced subtitles have no translation")


class TestFontGeometry(unittest.TestCase):
    """The SFN image entry duplicates the atlas geometry; growing the atlas
    without updating it makes the engine clip every appended glyph (all of the
    Arabic ones), which is the runtime corruption this test guards against."""

    def _entry_tail(self, raw):
        from tools.sfn_build import SfnBuilder
        b = SfnBuilder(raw)
        e = b.image_entry
        if len(e) < 28:
            return None, b
        tail = (struct.unpack_from("<I", e, len(e) - 28)[0],
                struct.unpack_from("<I", e, len(e) - 24)[0],
                struct.unpack_from("<I", e, len(e) - 20)[0],
                struct.unpack_from("<I", e, len(e) - 8)[0],
                struct.unpack_from("<I", e, len(e) - 4)[0])
        return tail, b

    def test_rebuild_preserves_entry_tail(self):
        from tools.sfn_build import SfnBuilder
        for p in sorted(glob.glob(os.path.join(EX, "MOH4/DATA/*.SFN"))):
            raw = open(p, "rb").read()
            b = SfnBuilder(raw)
            with self.subTest(font=os.path.basename(p)):
                self.assertEqual(b.rebuild(), raw)

    def test_built_fonts_have_consistent_geometry(self):
        import glob as _glob
        checked = 0
        for p in sorted(_glob.glob(os.path.join(HERE, "build/fonts/*.sfn"))):
            tail, b = self._entry_tail(open(p, "rb").read())
            if tail is None:
                continue
            w, h = b.atlas_w, b.atlas_h
            px = w * h // 2
            with self.subTest(font=os.path.basename(p)):
                self.assertEqual(tail, (px + 48, 48, px, w, h))
            checked += 1
        self.assertGreater(checked, 0)

    def test_add_glyphs_updates_entry_geometry(self):
        from tools.sfn_build import SfnBuilder
        from tools.sfn import CharEntry
        raw = open(os.path.join(EX, "MOH4/DATA/SUBFNT.SFN"), "rb").read()
        b = SfnBuilder(raw)
        row = bytes(b.atlas_w // 2)
        c = CharEntry(code=0xFF00, width=1, height=1, u=0, v=b.atlas_h,
                      advance=1, x_offset=0, y_offset=0)
        out = b.add_glyphs([c], [row])
        tail, nb = self._entry_tail(out)
        w, h = nb.atlas_w, nb.atlas_h
        px = w * h // 2
        self.assertEqual(h, SfnBuilder(raw).atlas_h + 1)
        self.assertEqual(tail, (px + 48, 48, px, w, h))


if __name__ == "__main__":
    unittest.main()

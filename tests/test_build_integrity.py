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


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Build an inventory of all localizable string tables in the game.

String tables are VIV containers holding a single UTF-16LE XML file with
<localstring>/<globalstring> entries, each carrying a `value` per language.
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.viv import Viv  # noqa: E402


def find_tables(root):
    out = []
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if f.upper() == "STRINGS.VIV":
                out.append(os.path.join(dp, f))
    return sorted(out)


def load_table(path):
    v = Viv.parse(path)
    e = v.entries[0]
    return e.name, e.data.decode("utf-16-le")


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "extracted"
    outdir = sys.argv[2] if len(sys.argv) > 2 else "text"
    os.makedirs(outdir, exist_ok=True)
    tables = find_tables(root)
    total = 0
    langs = set()
    report = []
    for p in tables:
        name, txt = load_table(p)
        root_el = ET.fromstring(txt)
        strings = list(root_el.iter("localstring")) + list(root_el.iter("globalstring"))
        n = len(strings)
        total += n
        # write a normalized copy
        rel = os.path.relpath(p, root).replace("/", "__")
        with open(os.path.join(outdir, rel + ".xml"), "w", encoding="utf-8") as f:
            f.write(txt)
        for s in strings:
            for c in s:
                langs.add(c.tag)
        report.append((p, name, n))
    print(f"tables={len(tables)} total_strings={total}")
    print("languages:", sorted(langs))
    for p, name, n in report:
        print(f"  {n:6d}  {name:35s} {p}")
    with open(os.path.join("reports", "text_inventory.json"), "w") as f:
        json.dump({"tables": [{"path": p, "xmlname": name, "strings": n} for p, name, n in report],
                   "total_strings": total, "languages": sorted(langs)}, f, indent=2)


if __name__ == "__main__":
    main()

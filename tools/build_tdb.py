#!/usr/bin/env python3
"""Extract every localizable string from the game into a translation database.

Output: translations/strings.json  (list of entries)
Each entry: id, table, source_viv, kind, english, control_codes, other_langs
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.viv import Viv  # noqa: E402

LANGS = ["danish", "dutch", "english", "french", "german", "italian",
         "japanese", "korean", "spanish", "swedish", "chinese"]
# control codes: %1 %2 $NAME $[NAME] [n.n] \n etc.
CTRL_RE = re.compile(r"(%\d|\$\[?[A-Za-z_]+\]?|\[\d+(?:\.\d+)?\]|\\n|~[A-Za-z])")


def find_tables(root):
    out = []
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if f.upper() in ("STRINGS.VIV", "STRINGMP.VIV"):
                out.append(os.path.join(dp, f))
    return sorted(out)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "extracted"
    entries = []
    for p in find_tables(root):
        v = Viv.parse(p)
        e = v.entries[0]
        txt = e.data.decode("utf-16-le")
        root_el = ET.fromstring(txt)
        table = e.name
        rel = os.path.relpath(p, root)
        for s in list(root_el.iter("localstring")) + list(root_el.iter("globalstring")):
            kind = "local" if s.tag == "localstring" else "global"
            sid = s.get("name", "")
            vals = {c.tag: c.get("value", "") for c in s}
            en = vals.get("english", "")
            ctrl = sorted(set(CTRL_RE.findall(en)))
            entries.append({
                "id": sid,
                "table": table,
                "source": rel,
                "kind": kind,
                "english": en,
                "control_codes": ctrl,
                "langs": sorted(vals.keys()),
                "all": vals,
            })
    os.makedirs("translations", exist_ok=True)
    with open("translations/strings.json", "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)
    print(f"wrote {len(entries)} entries to translations/strings.json")
    # summary
    from collections import Counter
    print("by table:", Counter(e["table"] for e in entries).most_common())
    # empty english?
    print("empty english:", sum(1 for e in entries if not e["english"].strip()))


if __name__ == "__main__":
    main()

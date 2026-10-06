#!/usr/bin/env python3
"""Merge the hand-authored Arabic sources, validate them and shape them.

Reads translations/{ui_ar,global_ar,mp_ar}.py, matches the IDs against the
string inventory (translations/strings.json), verifies that every control code
of the English source survives, applies Arabic shaping + bidi and writes
translations/ar_final.json  (id -> shaped string) plus a QA summary.
"""
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))
from tools.arabic import process, shape_only  # noqa: E402
from tools.inject_strings import STR_OPEN, _unescape  # noqa: E402

CTRL = re.compile(r"(%\d|\$\[?[A-Za-z_][A-Za-z0-9_]*\]?|\[\d+(?:\.\d+)?\]|\\n|\|[^\|]*\|?|~[A-Za-z])")


def load_source(name):
    path = os.path.join(HERE, "translations", name)
    spec = importlib.util.spec_from_file_location(name[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.AR


def tokens(s):
    return re.findall(r"%[A-Za-z0-9]|\$\[?[A-Za-z_][A-Za-z0-9_]*\]?|\\n|\[\d+(?:\.\d+)?\]", s)


def _escape_id(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    db = json.load(open(os.path.join(HERE, "translations", "strings.json")))
    english = {x["id"]: x["english"] for x in db}

    raw = {}
    ui_raw = {}
    for name in ("ui_ar.py", "global_ar.py", "mp_ar.py", "mission_ar.py",
                 "mission_ar2.py", "mission_ar3.py", "mission_ar4.py",
                 "mission_ar5.py", "mission_ar6.py", "mission_ar7.py", "mission_ar8.py",
                 "mission_ar9.py", "mission_ar10.py", "credits_ar.py"):
        p = os.path.join(HERE, "translations", name)
        if os.path.exists(p):
            vals = load_source(name)
            raw.update(vals)
            if name == "ui_ar.py":
                ui_raw.update(vals)

    shaped = {}
    scaleform = {}
    problems = []
    unmatched = []
    for sid, ar in raw.items():
        if sid not in english:
            unmatched.append(sid)
            continue
        src = english[sid]
        miss = [t for t in tokens(src) if t not in tokens(ar)]
        if miss:
            problems.append((sid, miss))
        shaped[sid] = process(ar)
        if sid in ui_raw:
            scaleform[sid] = shape_only(ar)

    json.dump(scaleform, open(os.path.join(HERE, "translations", "ar_scaleform_final.json"), "w"),
              ensure_ascii=False, indent=1)
    json.dump(shaped, open(os.path.join(HERE, "translations", "ar_final.json"), "w"),
              ensure_ascii=False, indent=1)

    total = len(english)
    print(f"authored={len(raw)} matched={len(shaped)} of {total} unique strings "
          f"({100*len(shaped)//total}%)")
    print(f"ids not in DB: {len(unmatched)} {unmatched[:10]}")
    print(f"scaleform/UI strings: {len(scaleform)} (shape-only, logical order)")
    print(f"control-code mismatches: {len(problems)}")
    for sid, miss in problems[:20]:
        print("   ", sid, "missing", miss)
    # control code inventory of the untranslated remainder
    from collections import Counter
    rem = [i for i in english if i not in shaped]
    cc = Counter()
    for i in rem:
        for t in tokens(english[i]):
            cc[t] += 1
    print("untranslated control codes:", dict(cc))


if __name__ == "__main__":
    main()

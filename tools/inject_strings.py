#!/usr/bin/env python3
"""Inject Arabic strings into the EA string tables (STRINGS.VIV).

A table is a single UTF-16LE XML document of the form

  <localstring name="ID">
    <danish value=".." /> <english value=".." /> ... </localstring>

The engine selects the language child by index, so we overwrite the `english`
child with the shaped, visually-ordered Arabic text.  Editing is surgical:
only the `value` attribute of the chosen language child is replaced, every
other byte (indentation, ordering, other languages) is preserved verbatim.

`apply` with an empty translation map reproduces the original XML exactly,
which is the round-trip regression test.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.viv import Viv  # noqa: E402

STR_OPEN = re.compile(r'<(local|global)string name="([^"]+)">')
LANG_VAL = r'(<(%s) value=")(.*?)("\s*/>)'
LANG_RE = {}


def _lang_re(lang):
    r = LANG_RE.get(lang)
    if r is None:
        r = LANG_RE[lang] = re.compile(LANG_VAL % re.escape(lang), re.DOTALL)
    return r


def _escape(s):
    # values live in double-quoted XML attributes, so a literal quote must be
    # escaped exactly as the shipped English does (`&quot;`)
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _unescape(s):
    return (s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            .replace("&quot;", '"'))


def patch_xml(txt, translations, lang="english"):
    """Return the XML with `lang` values replaced from {id: value}."""
    out = []
    pos = 0
    for m in STR_OPEN.finditer(txt):
        sid = m.group(2)
        key = sid if sid in translations else _unescape(sid)
        if key not in translations:
            continue
        block_start = m.end()
        close = txt.find("</%sstring>" % m.group(1), block_start)
        if close < 0:
            continue
        block = txt[block_start:close]
        new_val = _escape(translations[key])
        new_block, n = _lang_re(lang).subn(
            lambda mm: mm.group(1) + new_val + mm.group(4),
            block, count=1)
        if n:
            out.append(txt[pos:block_start])
            out.append(new_block)
            pos = close
    out.append(txt[pos:])
    return "".join(out)


def inject_table(viv_path, translations, lang="english", out_path=None):
    v = Viv.parse(viv_path)
    entry = v.entries[0]
    txt = entry.data.decode("utf-16-le")
    patched = patch_xml(txt, translations, lang)
    data = patched.encode("utf-16-le")
    if data == entry.data:
        return False, v.build()
    entry.data = data
    entry.size = len(data)
    return True, v.build()


if __name__ == "__main__":
    # round-trip check: empty map must yield identical bytes
    import glob
    bad = 0
    for p in sorted(glob.glob("extracted/**/STRINGS.VIV", recursive=True)):
        v = Viv.parse(p)
        e = v.entries[0]
        txt = e.data.decode("utf-16-le")
        if patch_xml(txt, {}) != txt:
            print("XML round-trip DIFF", p)
            bad += 1
        if v.build() != open(p, "rb").read():
            print("VIV round-trip DIFF", p)
            bad += 1
    print("round-trip failures:", bad)

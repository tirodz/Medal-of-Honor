#!/usr/bin/env python3
"""Arabic text processing for a non-RTL PS2 engine.

The engine renders UTF-16 code units left-to-right through a glyph table.
To display Arabic we:
  1. Reshape Arabic into contextual presentation forms (arabic_reshaper).
  2. Apply the Unicode bidi algorithm to obtain visual order (python-bidi).
The resulting sequence of Unicode code points is stored in the string table;
the font is extended with a glyph for each code point actually used.

Control codes ( %1 %2 $ACTION $[...] [n.n] \\n ) are preserved verbatim and
must be re-inserted after shaping because they are direction-neutral tokens.
"""
import re
import unicodedata

import arabic_reshaper
from bidi.algorithm import get_display

CTRL_RE = re.compile(r"(%[A-Za-z0-9]|\$\[?[A-Za-z_][A-Za-z0-9_]*\]?|\[>[A-Za-z_]+\]|\[\d+(?:\.\d+)?\]|\\n|~[A-Za-z])")

_RESHAper = arabic_reshaper.ArabicReshaper(
    # Diacritics (harakat) are dropped: the engine places glyphs linearly on the
    # baseline with no mark positioning, so inline marks render incorrectly.
    configuration={"delete_harakat": True, "support_ligatures": True}
)

ARABIC_RANGES = [
    (0x0600, 0x06FF),  # Arabic
    (0x0750, 0x077F),  # Arabic Supplement
    (0x08A0, 0x08FF),  # Arabic Extended-A
    (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
]


def has_arabic(s: str) -> bool:
    return any(any(a <= ord(c) <= b for a, b in ARABIC_RANGES) for c in s)


def _protect(s: str):
    """Replace control codes with private-use placeholders."""
    store = []

    def repl(m):
        store.append(m.group(0))
        return "\uE000" + chr(0xE001 + len(store) - 1)

    return CTRL_RE.sub(repl, s), store


def _restore(s: str, store) -> str:
    def repl(m):
        return store[ord(m.group(1)) - 0xE001]

    return re.sub("\uE000([\uE001-\uE0FF])", repl, s)


def process(text: str) -> str:
    """Return the shaped, visually-ordered string to store in the game.

    The string tables use two line separators - the literal two-character
    sequence ``\\n`` and ``|`` - and the engine breaks lines on them, drawing
    each line left to right.  They must therefore be handled as hard breaks:
    the bidi algorithm would otherwise reverse the order of the lines
    themselves (first paragraph would render last).  Each line is reshaped and
    reordered on its own and the separators are kept verbatim.
    """
    if not has_arabic(text):
        return text
    out = []
    for part in re.split(r"(\\n|\|)", text):
        if part in ("\\n", "|"):
            out.append(part)
            continue
        protected, store = _protect(part)
        shaped = _RESHAper.reshape(protected)
        visual = get_display(shaped, base_dir="R")
        out.append(_restore(visual, store))
    return "".join(out)


if __name__ == "__main__":
    import sys
    for t in sys.argv[1:] or ["مرحبا بالعالم", "دمّر مدفعية العدو.", "اضغط $ACTION لإضافة هدف", "%1 من %2"]:
        print(repr(t), "->", repr(process(t)))
        print("   codes:", [hex(ord(c)) for c in process(t)])

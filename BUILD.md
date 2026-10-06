# BUILD.md — reproducing the Arabic localization of Medal of Honor: European Assault (PS2, USA)

This document describes, end to end, how the Arabic-localized image is produced
from the user-supplied original ISO. Everything is scripted; no manual binary
editing is required.

## 0. Prerequisites

```
python3            (3.13 used here)
pip install pycdlib pillow arabic-reshaper python-bidi
```

`pycdlib` is only used for an independent structural sanity check of the output.
The build itself uses the project's own ISO9660 reader/writer
(`tools/iso9660.py`) so that file sizes may change without any dependency on an
external mastering tool.

The Arabic glyphs are rasterized from an open-source TrueType face. The build
defaults to Noto Sans Arabic; a copy is kept in `build/fonts_src/` and the path
can be overridden with the `AR_TTF` environment variable:

```
export AR_TTF=build/fonts_src/NotoSansArabic-Regular.ttf
```

## 1. Project layout

```
original/      pristine supplied ISO + its SHA-256 (never modified)
extracted/     byte-exact extraction of the original ISO tree
build/
  tree/        the modified tree (only the 50 changed files live here)
  fonts/       Arabic-extended SFN fonts
  fonts_src/   the TrueType source used for rasterization
  moh_ea_ar.iso        final image
  moh_ea_ar.xdelta     sector delta patch vs. the original
research/      upstream EA font/graphics documentation gathered for reference
reports/       reconnaissance report, ISO listing, text inventory
tools/         all build + reverse-engineering tools
translations/  Arabic sources, glossary DB, shaped output, QA data
tests/         regression suite
```

`original/`, `extracted/` and `build/` are git-ignored (copyrighted game data).

## 2. Pipeline

The pipeline is a straight line; each stage is idempotent and can be re-run.

```
original ISO
   │  tools/extract_iso.py        -> extracted/            (byte-exact)
   │  tools/inventory_text.py     -> reports/text_inventory.json
   │  tools/build_tdb.py          -> translations/strings.json
   │  (hand-authored Arabic)      -> translations/*_ar.py
   │  tools/build_translations.py -> translations/ar_final.json (shaped+bidi)
   │  tools/build_fonts.py        -> build/fonts/*.SFN  (16-bit Arabic)
   │  tools/build_movie_font.py   -> build/fonts/*.SFN  (+ byte Arabic for movies)
   │  tools/inject_loc.py         -> build/movies/LOC/*.LOC
   │  tools/build_tree.py         -> build/tree/   (50 modified files)
   │  tools/build_iso.py          -> build/moh_ea_ar.iso
   │  tools/verify_iso.py         -> structural verification
   │  tools/verify_build.py       -> resource-level verification + QA sheets
   │  tools/make_patch.py         -> build/moh_ea_ar.xdelta
```

### 2.1 Extraction
`extract_iso.py` walks the ISO9660 directory tree and writes every file out
unmodified. The supplied ISO is never opened for writing.

### 2.2 String inventory
`inventory_text.py` opens every `STRINGS.VIV` / `STRINGMP.VIV` (0xC0FB
archives holding a single UTF-16LE XML string table), parses the
`<localstring>` / `<globalstring>` elements and records, for each ID, the
English text, every sibling language, the control codes and the source file.
`build_tdb.py` turns that into `translations/strings.json` (3,174 entries,
2,623 unique IDs).

### 2.3 Translation
Arabic is authored by hand in `translations/{ui,global,mp,mission_ar*,credits}_ar.py`
keyed by string ID. `build_translations.py`:

* matches each ID against the inventory (IDs not present in the game are
  reported and dropped);
* verifies that every control code of the English source (`%1`, `%2`, `%s`,
  `$ACTION`, `[$…]`, `\n`, …) survives into the Arabic;
* runs the Arabic processor and writes `translations/ar_final.json`.

The Arabic processor (`tools/arabic.py`):

1. protects control codes behind private-use placeholders,
2. reshapes Arabic into contextual presentation forms (U+FE70–U+FEFF) with
   `arabic_reshaper` (harakat dropped — the engine has no mark positioning),
3. applies the Unicode bidirectional algorithm (`python-bidi`) with a
   right-to-left base direction to obtain visual order,
4. restores the control codes verbatim.

Because the engine renders UTF-16 code units strictly left to right, storing
the *visually ordered* presentation forms makes RTL text appear correctly
without any renderer change.

### 2.4 Fonts
`build_fonts.py` iterates every SFN font in the game — the 8 standalone
`DATA/*.SFN` files and the 10 SFN entries inside `REALFONT.VIV` /
`REALFTFE.VIV`. For each font it:

* round-trip-validates the parser,
* computes the set of code points actually used by the shaped translations
  (142 code points),
* rasterizes the missing glyphs from the TrueType face, quantizes them to the
  font's 4bpp grayscale palette, and appends a `Character12` entry with
  baseline-matched metrics,
* writes the result to `build/fonts/`.

All 18 fonts build with full coverage (0 missing, 0 out-of-atlas).

`build_movie_font.py` then adds a second, byte-addressed Arabic set to the
standalone `DATA/*.SFN` fonts for the cutscene subtitles. The 8-bit `.LOC`
tables can only address bytes, so the 114 Arabic contextual forms used by the
subtitles are rasterized into the byte slots `0x80–0xF1` of the two fonts that
have enough high slots (`SUBFNT.SFN`, `OBJFONT.SFN`), in place so the character
table size, order and kerning are preserved. Fonts with fewer free slots are
left with 16-bit Arabic only. `build/fonts/movie_byte_map.json` records the
form→byte mapping used by the injector.

### 2.5 Injection
`build_tree.py` writes the modified files into `build/tree/`:

* `inject_strings.py` replaces only the `value` attribute of the `english`
  child of each `<localstring>`; indentation, ordering and the ten other
  language children are preserved byte for byte, and `"` is escaped as
  `&quot;` exactly as the shipped English does;
* `inject_savegame.py` re-encodes the save-game `.LOC` payloads (UTF-16LE),
  reconstructing the suffix-shared offsets;
* `inject_loc.py` writes the byte-mapped shaped Arabic into the `english` block
  of the 9 cutscene `MOVIES/LOC/*.LOC` tables (frame timing in `.STF` is
  untouched);
* the SFN files are copied from `build/fonts/`.

### 2.6 ISO rebuild
`build_iso.py` copies the original image, then writes each changed file into
its original extent when it fits, or into a free gap inside the ISO data area
when it grew. Free gaps are located by `iso_gaps.py` from the original
directory extents. Directory records are rewritten with the new sizes; the
total image length is unchanged, so no PVD/lead-out patching is needed.
`verify_iso.py` then confirms:

* the 16-sector PS2 boot system area is byte-identical,
* the 341 unchanged files are byte-identical,
* the 50 changed files match `build/tree/` byte for byte,
* `pycdlib` opens the image without error.

### 2.7 Delta patch
The image is 3.86 GB, so `make_patch.py` emits a sector-level delta
(`build/moh_ea_ar.xdelta`, 5.5 MB) that applies to the original ISO and
reproduces the final image exactly.

```
python3 tools/make_patch.py apply \
    "original/Medal of Honor - European Assault (USA).iso" \
    build/moh_ea_ar.xdelta /tmp/moh_ea_ar.iso
```

## 3. Full rebuild (one shot)

```
cd /workspace/project
bash scripts/build_all.sh          # every stage, in order, idempotent
```

`scripts/build_all.sh` runs:

```
python3 tools/build_fonts.py            # -> build/fonts/  (16-bit Arabic)
python3 tools/build_movie_font.py       # -> build/fonts/  (+ byte Arabic)
python3 tools/inject_loc.py             # -> build/movies/LOC/
python3 tools/build_tree.py             # -> build/tree/
python3 tools/verify_build.py           # static resource verification
python3 tools/build_iso.py              # -> build/moh_ea_ar.iso
python3 tools/verify_iso.py             # structural verification
python3 -m unittest discover -s tests   # regression suite

# optional, 3.86 GB -> 5.5 MB delta patch
python3 tools/make_patch.py make \
    "original/Medal of Honor - European Assault (USA).iso" \
    build/moh_ea_ar.iso build/moh_ea_ar.xdelta
```

(Edit `translations/*_ar.py`, then run `tools/build_translations.py` first if
the translation sources changed.)

## 4. Adding or fixing a translation

1. edit the relevant `translations/*_ar.py` (plain `{"ID": "نص"}` dicts),
2. `python3 tools/build_translations.py && python3 tools/build_fonts.py`,
3. `python3 tools/build_tree.py && python3 tools/build_iso.py`,
4. `python3 tools/verify_iso.py`.

New Arabic code points are picked up automatically: `build_fonts.py` derives
its glyph set from the shaped translation DB, so no font list needs editing.

## 5. Determinism

Every tool reads only from `original/`, `extracted/`, `translations/` and
`build/fonts_src/`, and all inputs are byte-stable, so repeated runs produce a
byte-identical `build/moh_ea_ar.iso` (same SHA-256).

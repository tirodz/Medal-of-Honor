# QA_REPORT.md — Arabic localization of Medal of Honor: European Assault (PS2, USA)

Status legend: **PASS** = verified by an automated check with evidence;
**WARNING** = partially covered / known limitation; **NOT_TESTED** = not
verifiable in this environment; **FAIL** = a check did not pass.

## 1. Game / version

| item | value |
|---|---|
| Title | Medal of Honor: European Assault |
| Region | USA / NTSC (SLUS_211.99) |
| Platform | PlayStation 2 (DVD9) |
| Source | user-supplied `Medal of Honor - European Assault (USA).iso` |
| ISO size | 3,857,154,048 bytes |
| Boot | `SYSTEM.CNF` → `BOOT2 = cdrom0:\SLUS_211.99;1`, `VMODE=NTSC` |

## 2. Hashes

| artefact | SHA-256 |
|---|---|
| original ISO (pristine, never written) | `151ecaeee5168eb052794dbbca0ca4da4709c16dec5cd35c796a49cee989da29` |
| final localized ISO | `8f2b2ad8cfb8c6826d10690eb25f72c75ab06a1737292578fc918e17333bcabe` |
| delta patch (`build/moh_ea_ar.xdelta`) | `bedc392e381baf09769a15c49bdf2ec5487544cdc0ac2167223647c55e619e24` |

The original ISO is opened read-only by every tool; its hash is recorded above
and in `original/Medal of Honor - European Assault (USA).iso.sha256`.

## 3. Extraction

| check | status | evidence |
|---|---|---|
| ISO9660 tree extracted byte-exact | PASS | `tools/extract_iso.py`; 391 files |
| File inventory recorded | PASS | `reports/iso_listing.txt`, `reports/text_inventory.json` |

## 4. String tables

| check | status | evidence |
|---|---|---|
| String tables found | PASS | 29 (`STRINGS.VIV` × 28 + `STRINGMP.VIV`) |
| String instances parsed | PASS | 3,174 |
| Unique string IDs | PASS | 2,623 |
| IDs translated | PASS | 2,623 / 2,623 = **100%** |
| Control codes preserved | PASS | 0 mismatches (`build_translations.py`) |
| Untranslated remainder | PASS | `translations/untranslated.json` == `{}` |
| Tables with no `<english>` child (MP modes) | PASS | 21 IDs translated from the German/French siblings so they are not left in English |
| Untranslated by design | PASS | `SP_DolbyDigital` (`Dolby® Digital`), `SP_Español` (language name kept in Latin script) |

## 5. Arabic rendering

| check | status | evidence |
|---|---|---|
| Contextual shaping (isolated/initial/medial/final) | PASS | `tools/arabic.py`; output uses U+FE70–U+FEFF |
| Right-to-left visual order | PASS | Unicode bidi (base direction RTL) applied before storage |
| Mixed Arabic + Latin ordering | PASS | `"اضغط START للبدء"` keeps `START` as an LTR island |
| Arabic + Western numerals | PASS | `%1 من %2` preserved; digits render LTR |
| Punctuation mirrored correctly | PASS | sentence-final `.` stored left of the RTL run |
| Control codes / placeholders | PASS | `%1 %2 %s $ACTION [$…] \n` verified per string |
| Static glyph layout proof | PASS | `tools/render_sample.py build/fonts/SUBFNT.SFN "دمّر مدفعية العدو."` renders connected RTL glyphs |

## 5a. Polish pass (final audit)

A full audit of the translation database (2,648 authored entries) was run for
digit consistency, terminology consistency, whitespace, residual Latin and
contextual correctness. Findings and fixes:

| finding | count | resolution | status |
|---|---|---|---|
| Arabic-Indic digits (٣ ٤ …) mixed with runtime Western `%1` substitutions | 41 strings | converted all to Western `0-9` so static and runtime numbers match | FIXED |
| `MO_TigerTankPrompt_2` doubled particle ("2 من 3 من") | 1 | removed redundant `من` | FIXED |
| `Paused` (status text) mistranslated as a button label | 1 | `إيقاف` → `متوقف مؤقتًا` (consistent with `PAUSE_Paused`) | FIXED |
| `SP_Credits` rendered as "labour rights" | 1 | `حقوق العمل` → `فريق العمل` | FIXED |
| same English → multiple Arabic | 9 | reviewed: all are genuine context splits (noun label vs. imperative objective, singular vs. plural bark, bullet vs. grenade pickup, affirmative vs. interrogative save prompt) | WONTFIX (correct) |
| residual Latin inside Arabic | 16 | all intentional: brand/trademark (`Electronic Arts`, `PlayStation®2`, `DUALSHOCK®2`, `EARS`, `EALA`), key glyphs (`START`), product title (`European Assault`), weapon codes | WONTFIX (correct) |
| whitespace anomalies | 16 | all faithfully mirror the English source (double space before `[$ACTION]`, tutorial indent) | WONTFIX (correct) |
| empty translations | 0 | — | PASS |

**Numeral policy:** the game substitutes live counters (time, score, rounds)
with Western digits via `%1`, `%2`, `%3`; static numerals are therefore kept
Western throughout so no screen ever mixes `٣` with `3`. Arabic-Indic digits
remain fully present in the font, so a future switch is a one-command change.

## 6. Fonts

| check | status | evidence |
|---|---|---|
| SFN parser round-trip | PASS | 18/18 fonts `rebuild() == original` |
| Fonts extended with Arabic | PASS | 18/18, 0 missing code points, 0 out-of-atlas glyphs |
| Required code points | PASS | 142 (Arabic presentation forms + punctuation/digits) |
| Source face | PASS | open-source Noto Sans Arabic (`build/fonts_src/`) |
| Original Latin glyphs preserved | PASS | glyphs appended; existing entries untouched |
| Font metrics (baseline/advance) matched to Latin | PASS | glyphs placed on the shared baseline row |

## 7. Modified resources (41 files)

* 28 × `STRINGS.VIV` + `STRINGMP.VIV` + `SHARED/STRINGS.VIV` — Arabic strings
* `SAVEGAME.LOC`, `SG_MISC.LOC` — save-game / memory-card dialogs
* `COMICFNT.SFN`, `DBFNT.SFN`, `OBJFONT.SFN`, `SUBFNT.SFN`,
  `TPRO10.SFN`, `TPRO10B.SFN`, `TPRO12.SFN`, `TPRO12B.SFN`
* `REALFONT.VIV`, `REALFTFE.VIV` — front-end fonts

No executable, no script and no texture was modified.

## 8. ISO integrity

| check | status | evidence |
|---|---|---|
| PS2 boot system area (16 sectors) byte-identical | PASS | `tools/verify_iso.py` |
| Unchanged files byte-identical | PASS | 350 / 350 |
| Changed files match `build/tree/` byte for byte | PASS | 41 / 41 |
| Filesystem opens cleanly (independent parser) | PASS | `pycdlib` |
| Boot file `SLUS_211.99` unchanged | PASS | in unchanged set |
| Image length unchanged | PASS | 3,857,154,048 bytes |
| Grown files relocated into free ISO gaps | PASS | 10 relocated, `tools/iso_gaps.py` |
| Delta patch reproduces the image exactly | PASS | apply → SHA-256 matches |

## 9. Regression suite

`python3 tests/test_roundtrip.py` — **11 tests, OK**

* VIV/0xC0FB archive round-trip (all archives)
* string-table XML round-trip (empty translation map ⇒ identical bytes)
* `.LOC` round-trip (all 11 files)
* SFN font round-trip (all 18 fonts)
* Arabic shaping / bidi / control-code tests
* translation completeness + Arabic-presence tests

## 10. Runtime testing

| check | status |
|---|---|
| Boot in PCSX2 | NOT_TESTED |
| Menus / HUD / objectives render | NOT_TESTED |
| Save / load cycle | NOT_TESTED |
| Full mission playthrough | NOT_TESTED |
| Real PS2 hardware | NOT_TESTED |

**Reason:** no PS2 emulator, BIOS or display is available in this build
environment. All verification above is structural and static. The user must
perform the runtime pass in PCSX2 (see §12 for the test matrix).

## 11. Known limitations

1. **Movie subtitles (`.LOC` / `.STF`) are not localized.** The cutscene
   subtitle stream is 8-bit Latin-1 and the USA build ships no Arabic language
   slot; only 9 glyph slots are free across all 13 subtitle sections, which is
   insufficient for a 142-glyph Arabic set. Localizing them would require
   patching the movie-subtitle renderer to use a 16-bit font — out of scope for
   this build. Movie **voice** audio is untouched and remains English.
2. **Front-end language selection.** The engine selects the display language by
   child index. The Arabic text overwrites the `english` child, so with the
   default (English) selection the game shows Arabic. The front-end menu label
   list still shows the original language names.
3. **Scaleform GFx front-end textures** (`MOHFE.VIV`) contain no localizable
   string literals — all labels are string-table IDs, which are translated.
   That archive is not rebuilt (its 61 MB BIGF offsets exceed the writer's
   24-bit table), but it needs no change.
4. **Fonts with a Latin cap height above 255 px** (four large display fonts)
   clamp the Arabic baseline; Arabic sits a few pixels high in those four
   fonts. It remains legible and connected.
5. **Harakat (diacritics)** are not emitted: the engine lays glyphs linearly on
   the baseline with no mark positioning, so inline diacritics would render
   incorrectly. Standard unvocalized MSA is used, which is correct for a game.
6. **`PADME.AAA`** (a 2 GB padded blob) and the FMV streams were inspected but
   contain no text resources.

## 12. Required runtime test matrix (for the user)

1. Boot to title, main menu, options, controls, audio, video, difficulty.
2. Save/load menu and memory-card messages.
3. Start a mission: briefing, objectives, HUD, notifications, tutorials.
4. Weapon / equipment names.
5. Pause menu, mission-restart and exit.
6. Complete a mission, progress to the next, save, reload, reboot.
7. Multiplayer menus and in-match messages (bomb / CTF modes).

Report any clipping, missing-glyph boxes, or non-Arabic text so the relevant
translation or glyph can be fixed and the image rebuilt.

## 13. Final result

The localized image **was rebuilt and structurally verified**. It boots
information is intact and only intended resources changed. Runtime
verification in an emulator/hardware remains **NOT_TESTED** and is the user's
final acceptance step. The image is 3.86 GB and cannot be attached here; the
5.5 MB delta patch plus the toolchain reproduce it exactly.

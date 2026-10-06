# PROGRESS REPORT — Arabic localization of MoH: European Assault (PS2, USA)

Snapshot taken after the movie-subtitle pass and the final polish audit. The
toolchain, translations, fonts, ISO rebuild and regression suite are complete
and re-verified.

## Status at a glance

| area | state |
|---|---|
| Reconnaissance / format reversing | COMPLETE |
| String extraction + translation | COMPLETE (100% of unique IDs) |
| Arabic shaping + bidi | COMPLETE |
| Arabic font injection (18 SFN fonts, 16-bit) | COMPLETE |
| Cutscene subtitle localization (.LOC/.STF) | COMPLETE (byte-mapped) |
| ISO repack | COMPLETE, structurally verified |
| Delta patch | COMPLETE, reproduces image byte-exactly |
| Regression tests | 32/32 PASS |
| Runtime test in PCSX2 | NOT_TESTED (no emulator/BIOS here) |

## Deliverables present in `/workspace/project`

| artefact | size | SHA-256 |
|---|---|---|
| `build/moh_ea_ar.iso` (localized image) | 3,857,154,048 | `06bec309ccc135f3b19f2c437c3800f558a01d1b6ee85b8665b5275a22658dd5` |
| `build/moh_ea_ar.xdelta` (sector delta vs. original) | 5,538,372 | `0f847a425a1288752cbc5a005cce64c4eaea5922fb8ea22e62735ded72829995` |
| `original/…(USA).iso` (pristine, never written) | 3,857,154,048 | `151ecaeee5168eb052794dbbca0ca4da4709c16dec5cd35c796a49cee989da29` |

Documentation: `reports/RECON.md` (technical reconnaissance), `BUILD.md`
(reproducible build), `QA_REPORT.md` (full QA), this file. One-command rebuild:
`bash scripts/build_all.sh`.

## What was done in this session

1. **Localized the cutscene subtitles.** The 8-bit `.LOC` subtitle tables were
   previously a documented limitation. Added `tools/build_movie_font.py` (raster
   the 114 subtitle contextual forms into byte slots `0x80–0xF1` of the two
   fonts with enough room, in place so kerning/table order survive) and
   `tools/inject_loc.py` (write the byte-mapped shaped Arabic into the `english`
   block of every movie `.LOC`). **144/144 referenced subtitles translated, 0
   missing**; `.STF` frame timings are untouched so subtitle timing is
   unchanged. English voice audio remains intact.
2. **Fixed an XML-escaping bug.** Translations containing `"` (e.g. quoted
   speech, `"Wild Bill" Donovan`) were written literally into the
   `value="…"` attribute, corrupting the XML of 2 built tables. `_escape()` now
   emits `&quot;`, matching the shipped English. All 28 built tables parse.
3. **Added static resource verification** (`tools/verify_build.py`): decodes
   every built `.LOC` back to the expected shaped text (145/145 OK), counts
   Arabic coverage (2,565/2,589) and renders UI + subtitle contact sheets
   (`build/qa/*.png`).
4. **Added regression tests** (`tests/test_build_integrity.py`): built-tree XML
   well-formedness, Arabic presence, save-game decode, STF→LOC coverage. Suite
   is now **32 tests, all passing**.
5. **Added a one-shot build script** (`scripts/build_all.sh`) that runs the whole
   pipeline in the correct order and is idempotent.
6. **Rebuilt and re-verified the image**: 341 unchanged files byte-identical,
   50 changed files correct, 0 failures, PS2 boot area intact, `pycdlib` opens
   it; delta patch regenerated and round-trips to the same hash.
7. **Updated `BUILD.md`, `QA_REPORT.md` and this report.**

## Modified resources (50 files, no code/texture changes)

* 30 string tables (`STRINGS.VIV` × 28, `STRINGMP.VIV`, `SHARED/STRINGS.VIV`)
* `SAVEGAME.LOC`, `SG_MISC.LOC` (save-game / memory-card dialogs)
* 9 cutscene subtitle tables (`MOVIES/LOC/*.LOC`, byte-mapped)
* 8 standalone SFN fonts + `REALFONT.VIV` + `REALFTFE.VIV` (10 fonts)

## Known limitations

1. **Movie subtitle font not named in the executable.** Byte glyphs were written
   into both fonts that have enough high slots (`SUBFNT.SFN`, `OBJFONT.SFN`);
   the other six get 16-bit Arabic only. Static evidence points to these two;
   runtime confirmation is the one open item.
2. **Front-end language menu** labels keep their original language names; the
   game displays Arabic under the default English selection.
3. Four large display fonts clamp the Arabic baseline a few pixels high.
4. **Runtime verification is NOT_TESTED** — no PCSX2/BIOS/display here.

## Next steps (optional)

* Run the test matrix in `QA_REPORT.md` §12 in PCSX2 on the patched image,
  including a cutscene to confirm the byte-mapped subtitle font.
* Report any clipping / missing glyphs / residual English for a targeted fix
  and rebuild (deterministic, re-runnable with `scripts/build_all.sh`).

## Final polish pass

A product audit of the whole translation DB was performed. Fixes applied:
unified all numerals to Western digits (41 strings) so static numbers match the
engine's runtime `%1` substitutions; fixed a doubled particle in a King Tiger
objective; corrected the `Paused` status string and the `SP_Credits` label.
Terminology variants (9) and residual Latin (16) were reviewed and confirmed
contextually correct. Arabic subtitle width was checked against the 530 px
subtitle box: max 874 px vs. English 1,430 px, and the renderer already wraps
English to ≤3 lines, so Arabic is strictly safer.

## How to obtain the localized game

The ISO is too large to attach. Recreate it from the patch:

```
python3 tools/make_patch.py apply \
    "original/Medal of Honor - European Assault (USA).iso" \
    build/moh_ea_ar.xdelta /path/to/moh_ea_ar.iso
```

or do a full source rebuild following `BUILD.md` §3 (`bash scripts/build_all.sh`).

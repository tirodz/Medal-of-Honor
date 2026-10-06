# PROGRESS REPORT — Arabic localization of MoH: European Assault (PS2, USA)

Snapshot taken after the toolchain, translations, fonts, ISO rebuild and
regression suite were all completed and re-verified following an environment
restart.

## Status at a glance

| area | state |
|---|---|
| Reconnaissance / format reversing | COMPLETE |
| String extraction + translation | COMPLETE (100% of unique IDs) |
| Arabic shaping + bidi | COMPLETE |
| Arabic font injection (18 SFN fonts) | COMPLETE |
| ISO repack | COMPLETE, structurally verified |
| Delta patch | COMPLETE, reproduces image byte-exactly |
| Regression tests | 11/11 PASS |
| Runtime test in PCSX2 | NOT_TESTED (no emulator in this environment) |
| Movie subtitles (.LOC/.STF) | WARNING — documented limitation |

## Deliverables present in `/workspace/project`

| artefact | size | SHA-256 |
|---|---|---|
| `build/moh_ea_ar.iso` (localized image) | 3,857,154,048 | `30ff50a295e42e6ac81c2c81fc2ba0ffa54d3130379477e8d22b5fc43f7a0b75` |
| `build/moh_ea_ar.xdelta` (sector delta vs. original) | 5,513,748 | `e2e1926a7132e91317fa1d747d7ca2d52ffadf770cdccb02e1b9f8ad2e1b3ac0` |
| `original/…(USA).iso` (pristine, never written) | 3,857,154,048 | `151ecaeee5168eb052794dbbca0ca4da4709c16dec5cd35c796a49cee989da29` |

Documentation: `reports/RECON.md` (technical reconnaissance), `BUILD.md`
(reproducible build), `QA_REPORT.md` (full QA), this file.

## What was done in this session

1. **Re-verified the previously built ISO** byte for byte: 350 unchanged files
   identical, 41 changed files match the build tree, PS2 boot area intact,
   `pycdlib` opens the image, zero failures.
2. **Closed the translation gap.** 21 multiplayer strings (bomb / CTF / general
   modes) had no `<english>` child on disc; translated them from their
   German/French siblings. Also fixed an XML-escaped ID (`&amp;`). Result:
   **2,623 / 2,623 unique IDs translated, 0 untranslated, 0 control-code
   mismatches.**
3. **Improved the Arabic typeface.** Replaced the fallback rasterization source
   with open-source **Noto Sans Arabic** (vendored in `build/fonts_src/`); all
   **18 SFN fonts** rebuild with full coverage (0 missing, 0 out-of-atlas).
4. **Rebuilt the image** with the improved font and complete translations.
5. **Added `tools/make_patch.py`** — a compact sector-delta generator, since the
   3.86 GB ISO cannot be attached. The 5.5 MB patch applies to the original ISO
   and reproduces the final image byte-exactly (hash verified).
6. **Added `tests/test_roundtrip.py`** — 11 regression tests covering every
   custom parser round-trip, the Arabic shaping/bidi pipeline and translation
   completeness. All pass.
7. **Hardened the injector** to resolve XML-escaped string IDs.
8. **Wrote `BUILD.md` and `QA_REPORT.md`.**

## Modified resources (41 files, no code/texture changes)

* 29 string tables (`STRINGS.VIV` × 28, `STRINGMP.VIV`, `SHARED/STRINGS.VIV`)
* `SAVEGAME.LOC`, `SG_MISC.LOC` (save-game / memory-card dialogs)
* 8 standalone SFN fonts + `REALFONT.VIV` + `REALFTFE.VIV` (10 fonts)

## Known limitations

1. **Movie subtitles** are 8-bit Latin-1 with no Arabic slot and only 9 free
   glyph slots across all 13 language sections — not localizable without a
   renderer patch. Cutscene **voice audio stays English** (as intended).
2. **Front-end language menu** labels keep their original language names; the
   game displays Arabic under the default English selection.
3. Four large display fonts clamp the Arabic baseline a few pixels high.
4. **Runtime verification is NOT_TESTED** — no PCSX2/BIOS/display here.

## Next steps (optional)

* Run the test matrix in `QA_REPORT.md` §12 in PCSX2 on the patched image.
* Report any clipping / missing glyphs / residual English for a targeted fix
  and rebuild (the pipeline is deterministic and re-runnable in ~4 commands).

## How to obtain the localized game

The ISO is too large to attach. Recreate it from the patch:

```
python3 tools/make_patch.py apply \
    "original/Medal of Honor - European Assault (USA).iso" \
    build/moh_ea_ar.xdelta /path/to/moh_ea_ar.iso
```

or do a full source rebuild following `BUILD.md` §3.

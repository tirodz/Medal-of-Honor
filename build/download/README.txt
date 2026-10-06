Medal of Honor: European Assault (PS2, USA) — Arabic localization
==================================================================

The final ISO is 3.86 GB and cannot be attached. Two ways to get it:

A) Apply the delta patch to your own original ISO (fast, 5.5 MB):

   python3 tools/make_patch.py apply \
       "original/Medal of Honor - European Assault (USA).iso" \
       build/download/moh_ea_ar.xdelta /path/to/moh_ea_ar.iso

   (make_patch.py is in the project's tools/ directory; it is a plain
    sector-delta applier, no external tools needed.)

B) Full source rebuild: see BUILD.md section 3 (bash scripts/build_all.sh).

Original ISO SHA-256 (must match before patching):
  151ecaeee5168eb052794dbbca0ca4da4709c16dec5cd35c796a49cee989da29

Localized ISO SHA-256 (verify after patching):
  c3be6386f04f9f60ffa3447283c131ba28abf52ad5d13f366f623bbc51ea41cc

Patch SHA-256:
  fba063200514d9223d43dcf858280262583f372d1b5b7ef259132fe3780784b3

Files here:
  moh_ea_ar.xdelta   sector delta patch (applies to the original ISO)
  BUILD.md           reproducible build documentation
  QA_REPORT.md       full QA report (statuses, limitations, test matrix)
  PROGRESS_REPORT.md progress snapshot

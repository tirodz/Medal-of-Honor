#!/usr/bin/env bash
# Reproducible end-to-end build of the Arabic-localized ISO.
#
#   scripts/build_all.sh
#
# Every stage is idempotent.  The original ISO in original/ is never modified.
set -u
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}

echo "== 1/7  fonts: 16-bit Arabic for all SFN (UI text) =="
$PY tools/build_fonts.py | tail -3

echo "== 2/7  fonts: byte-addressed Arabic for the standalone movie fonts =="
$PY tools/build_movie_font.py

echo "== 3/7  movie subtitles: inject Arabic into the .LOC tables =="
$PY tools/inject_loc.py | tail -2

echo "== 4/7  strings + fonts + savegame + movies -> build/tree =="
$PY tools/build_tree.py | tail -4

echo "== 5/7  static verification of the built resources =="
$PY tools/verify_build.py

echo "== 6/7  assemble ISO =="
$PY tools/build_iso.py | tail -3

echo "== 7/7  verify ISO integrity =="
$PY tools/verify_iso.py | tail -4

echo "== regression tests =="
$PY -m unittest discover -s tests 2>&1 | tail -3

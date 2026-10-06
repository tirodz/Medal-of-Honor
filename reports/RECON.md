# Technical Reconnaissance Report — Medal of Honor: European Assault (PS2, USA)

## 1. Supplied material
- Source: user-provided `.7z` (cdromance mirror), 1,129,620,881 bytes.
- SHA-256 (7z): `27cca126a35ccf06415759edbce133c53496dc40aae9d8877cfddcad364d8320`
- Contents: one ISO9660 image `Medal of Honor - European Assault (USA).iso`, 3,857,154,048 bytes (DVD9).
- SHA-256 (ISO): `151ecaeee5168eb052794dbbca0ca4da4709c16dec5cd35c796a49cee989da29`
- ISO9660: System id `PLAYSTATION`, Application `PLAYSTATION`, logical block 2048, no Joliet, no Rock Ridge.

## 2. Boot chain
- `SYSTEM.CNF`: `BOOT2 = cdrom0:\SLUS_211.99;1`, `VER=1.00`, `VMODE=NTSC`.
- `SLUS_211.99` (122,692 B) == `MOH4/STUBRDVD.ELF` (byte-identical loader stub).
- Main executable: `MOH4/MOH4RDVD.ELF` (4,557,348 B, ELF32 MIPS little-endian).
- Engine support module `MOH4/EAGLRM.O`.
- `PADME.AAA` (2,000,000,000 declared) — large padded data blob.
- IOP modules: `IOPRP280.IMG`, `LIBSD.IRX`, `MCMAN.IRX`, `MCSERV.IRX`, `MTAPMAN.IRX`, `PADMAN.IRX`, `SIO2MAN.IRX`, `SNDDRV.IRX`.

## 3. Directory layout (relevant)
```
/MOH4/DATA/
  TPRO10/10B/12/12B.SFN      raster text fonts (HUD/objective)
  COMICFNT/DBFNT/OBJFONT/SUBFNT.SFN   raster fonts
  VERSION.XML, GAME.XML, GAME.CFG
  LOADING/*.SSH, LOADING.VIV (loading screens)
  SHARED/STRINGS.VIV         global UI string table
  SHARED/STRINGMP.VIV        multiplayer UI string table
  SHARED/UI/FE/MOHFE.VIV     front-end (Scaleform GFx) 61 MB
  SHARED/UI/FE/REALFONT.VIV  front-end fonts (SFN)
  SHARED/UI/FE/REALFTFE.VIV  front-end fonts (SFN)
  SHARED/MOVIES/*.MPC        cutscenes (EA MPC video)
  SHARED/MOVIES/LOC/*.LOC    subtitle text (ASCII, per-movie)
  SHARED/MOVIES/STF/US/*.STF subtitle timing/layout (ASCII TSV)
  HUD/{SHARED,SP,MP}/*.XML   HUD layout
  1/1_*/, 2/2_*/            mission data: LEVEL_A.STR, ASYNCSTR.REZ,
                            LOADING.VIV, STRINGS.VIV, SOUND/
  SAVEGAME/SAVEGAME.LOC, SG_MISC.LOC
```

## 4. Archive formats (all reversed and round-trip verified)

### 4a. `0xc0fb` container ("FBC0")
Used by all text tables, the font VIVs and some HUD VIVs.
```
u16be magic = 0xC0FB
u16be names_region_size
u16be entry_count
per entry (desc precedes name):
  u24be offset, u24be size, name (ASCII) + NUL
<pad to 64-byte boundary>
data blocks at their offsets
```
Verified byte-exact round-trip on 32 archives (STRINGS.VIV, REALFONT.VIV, …).

### 4b. `BIGF` archive (classic EA)
Used by `MOHFE.VIV` (front-end).
```
char signature[4] = "BIGF"|"BIGH"
u32le archive_size
u32be number_of_files
u32be directory_size
per entry: u32be offset, u32be size, name + NUL
data blocks 64-byte aligned
```

### 4c. `BIG3P` archive
Used by per-level `LOADING.VIV` (loading-screen textures). Header `BIG3P`, directory
of 12-byte descriptors `{u24 offset, u8?, u16 size}` (endianness under study).

## 5. Localization / string system (the key discovery)

The engine ships a **complete multilingual string-table system**, not just English.

- 28 string tables (`STRINGS.VIV`), each a `0xc0fb` archive holding ONE file
  `stringtable.xml` / `globalstringtable.xml` / `globalMPstringtable.xml`.
- Files are **UTF-16LE XML** (`<?xml version="1.0" encoding="utf-16"?>`, BOM `FF FE`).
- Structure: `<document type="stringtable"><xmlstringtable name="LevelTable">`
  with `<localstring name="ID">` (per-level) or `<globalstring name="ID">` (global),
  each containing one child per language: `<english value="…"/>` etc.
- **Languages present**: chinese, danish, dutch, english, french, german, italian,
  japanese, korean, spanish, swedish.
- Total string IDs: **2,589** (1,085 global + 1,504 level).
- Level tables with content: 1_1, 1_11, 1_15, 1_2, 1_21, 1_22, 1_24, 1_4, 1_5, 1_8,
  1_9, 1_99 (Shell), 2_55, 2_60, plus globals. MP level tables are empty (global MP table used).
- Format placeholders seen: `%1`, `%2`, `$ACTION`, `$HB_Select`, `[7.1]` (timing in barks).

### Language selection
- Front-end is Scaleform GFx (`MOHFE.VIV` → `scrns/languageSelect.big` →
  `languageSelect.apt` + `languageSelect.const`).
- `languageSelect.const` contains the **menu list**: `$SP_English`, `$SP_Nederlands`,
  `$SP_Svenska`, `$SP_Dansk`, `$SP_Español` and a `setLanguage` call.
- Label string IDs `SP_English … SP_LanguageSelect` exist in `1_99/STRINGS.VIV`.
- The engine picks the language **by child index** into each `<localstring>`; no language
  name literals appear in `MOH4RDVD.ELF`. The USA build exposes 5 UI languages
  (English, Dutch, Swedish, Danish, Spanish) although the data carries 11.
- Adding an **Arabic child element** to each `<localstring>` extends the language set;
  the front-end must additionally be pointed at it (see BUILD.md).

## 6. Fonts

### Raster fonts (`.SFN`, signature `FntS`, little-endian, version 414)
```
char signature[4]
u32 total_file_size
u16 version
u16 number_of_characters
u32 font_flags
u8 center_x, center_y, ascent, descent
u32 char_info_table_offset
u32 kerning_table_offset
u32 shape_header_offset
if version>=100: u8 font_states[96]
```
`font_flags` bitfields: `[0] antialias, [1] dropshadow, [2] outline, [3] vram,
[8:9] baseline (0=Roman,1=Ideographic,2=Hanging/Arabic), [10] orientation,
[11] direction (0=LTR,1=RTL), [16:17] encoding, [18] format`.

Character entry (format 0 = "Character12", 12 bytes):
`u16 code(unicode), u8 width, u8 height, u16 u, u16 v, u8 advance, u8 x_offset, u8 y_offset`.

Shape header at `shape_header_offset`:
`u8 record_id (bit7 = compressed), u24be block_size, u16be w, u16be h, s16be center_x/y, u16be shape_x/y` — glyph atlas (e.g. 256×104, 4bpp).

Fonts found:
| file | chars | code range | notes |
|---|---|---|---|
| COMICFNT.SFN | 95 | 0x20–0x7E | comic |
| DBFNT.SFN | 191 | 0x20–0xFF | debug |
| OBJFONT.SFN | 224 | 0x20–0xFF | objective |
| SUBFNT.SFN | 224 | 0x20–0xFF | subtitle |
| TPRO10/10B/12/12B.SFN | 194 | 0x20–0x2122 | HUD/objective raster |
| REALFONT.VIV | 4 fonts | 0x20–0x2122 | FE: Courier New_18, Futura Std Book_18, Futura Std Condensed ExtBd_18, Trajan Pro_18 |
| REALFTFE.VIV | 6 fonts | 0x20–0x2122 | FE: +Futura Std Condensed_24, Impact_24, Trajan Pro_24, Tw Cen MT Condensed_36 |

Font char tables are **16-bit Unicode keyed** (codes up to U+2122), so the font layer is
capable of addressing Arabic code points. The `encoding` flag is 0 (8-bit) for the
`DATA/*.SFN` raster fonts and 1 (UTF-16) for the FE VIV fonts.

## 7. Subtitles
- `.STF` = ASCII TSV: `FRAME STRINGID X Y WIDTH HEIGHT SHAPE A R G B JUSTIFY_X JUSTIFY_Y`.
- `.LOC` = `LOCH` + `u32 version + u32 count + u32 offsets[count]`, blocks `LOCL` +
  size + string-ID index table + ASCII NUL-terminated strings.
- 11 LOC files, 9 STF (US). Subtitle text is ASCII in the USA build.

## 8. Textures / UI
- `SSH`/`XSH`/`MSH` EA image files (EA Graphics Library). `.big` front-end files are
  Scaleform GFx (Flash) containers — menu layout/logic, labels are string-table IDs.
- `REALFONT/REALFTFE` carry the front-end fonts.

## 9. Runtime
- No PCSX2/BIOS/display available in this environment → runtime verification is
  documented as NOT_TESTED (see QA_REPORT.md). All build-time structural verification
  is performed instead.

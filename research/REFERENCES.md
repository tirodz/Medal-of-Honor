# Research references

Third-party tools and notes consulted while reverse-engineering the EA PS2
formats used by *Medal of Honor: European Assault*. These are **not vendored**
in this repository; clone them separately if needed.

| tool | source | used for |
|---|---|---|
| EA-Font-Manager | https://github.com/bartlomiejduda/EA-Font-Manager | cross-checking the SFN glyph/atlas layout and the EA font container |
| EA-Graphics-Manager | https://github.com/bartlomiejduda/EA-Graphics-Manager | cross-checking EA texture (VIV/GS) handling |

`EA_FONT.bt` (010 Editor template) is kept in-tree as a reference for the SFN
structure.

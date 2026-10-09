# MVS-GS manual validation in c3270 (user, 2026-10-08/09) - MVS-GS COMPLETE
## 80 x 24 scaled renderer (build JOB 200, CLIST JOB 201)
- 4x2 maze proportions on the macOS terminal font: PASS (user, 2026-10-09). The script-port captures of probe E11 prove
  the buffer contents; the physical aspect was judged by the user on the live screen.

## Geometry integration (build JOB 207, CLIST JOB 208) - `c3270 -model 2 -oversize auto` in a 120 x 30 window
| Check | Result |
|---|---|
| CANVAS(AUTO): 120 x 27, maze centred (rows 4-23, columns 21-100), side HUD, title, bottom rows | PASS |
| Moves, pellets, partial redraw | PASS |
| INVALID command + PA2 redraw | PASS |
| QUIT: 3-second end banner, then line mode / READY | PASS |
| CLEAR + PA2 restores the 120 x 27 screen (explicit Erase/Write Alternate on full redraws) | PASS |
| `COLOR(YES) HILITE(YES) GLYPHS(GRAPHIC)` (no query): 80 x 24 GS fallback | PASS |
| `CANVAS(DEFAULT)`: 80 x 24 GS | PASS |
Visual acceptance (user): the 120 x 27 layout uses the logical canvas effectively - the 80 x 20 maze correctly
proportioned and centred, side margins used for HUD and ghost information, top for the title, bottom for message /
banner / command; the remaining black space is acceptable breathing room. The maze must not be stretched further: 4x2
gives the correct proportions on this terminal/font; larger canvases improve centring and HUD space, not maze scale.

Terminal side (c3270 -trace ~/gs-live-geo.txt, outside the repo): `SENT SB TERMINAL TYPE IS IBM-DYNAMIC`; TSO's own logon
Erase/Write Alternate `SetBufferAddress(27,120)`; PACMAN's data-free size switch `EraseWriteAlternate(reset,restore,
resetMDT)` before the query (trace line 2047); the typed command returned from the field at `SetBufferAddress(26,34)` =
row B0+22 = 26, column C0+13 = 34, as designed. Totals: 9 Erase/Write Alternate, 4 Erase/Write, 506 Write records.

## Model 3 / 4 / 5 geometry evidence (probe E12, kept)
80 x 32, 80 x 43 and 132 x 27 alternate canvases: LIVE PASS (docs/evidence/gs-e12-geometry.md); their layouts (tall /
wide) are covered by the JOB 207 dry runs (tests/test_gx.py) and are supported; 120 x 27 IBM-DYNAMIC is the canvas
validated live with the game.

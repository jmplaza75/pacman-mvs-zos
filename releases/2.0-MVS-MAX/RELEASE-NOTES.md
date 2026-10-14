# Pac-Man 2.0-MVS-MAX (2026-10-14) - the final MVS release
Target: MVS 3.8J TK4- on Hercules (S/370, IKFCBL00 COBOL, IFOX00, IEWL, JES2, TSO / VTAM), c3270 4.5 as the terminal.
Everything in the game runs in MVS; see "What runs where" below. Release design: docs/G8-RELEASE.md (D43).

## What 2.0 is
The maximum presentation and gameplay that the validated TK4- / c3270 environment supports, selected automatically,
without breaking compatibility (requirements sec. 26, G8 / G9):
- **ARCADE rules by default** (`RULES(ARCADE)`): 4 power pellets, frightened ghosts, 200/400/800/1600, eyes going
  home, levels 1-99 with a per-level table, fruit, one extra life at 10000, 7-digit score, persistent high score in
  `HERC01.PACMAN.DATA(HISCORE)`, READY!, death animation, score popups. `RULES(CLASSIC)` = the 1.0-MVS game.
- **Real time** (`PLAY(REALTIME)`): one move every 150 ms (125 ms with `SPEED(FAST)`), arrows = PF7/8/10/11, PF9 pause.
- **Scaled 3270 graphics**: 4x2 maze with arcade contour walls (GE / APL code page 310), half-block sprites, colour and
  highlighting, partial redraw, centred on the 120 x 27 (or 132 x 27, 80 x 32, 80 x 43) alternate screen.
- **Sound** = the 3270 alarm: 1-4 bells per event (`ALARM(PATTERN)`), `SOUND(NO)` silent.
- Automatic fallbacks: no APL set -> G3 colour look; no highlighting -> `#` walls; small or unknown terminal -> 80 x 24;
  no colour / no valid Query Reply -> monochrome line mode, turn by turn. Final defaults: DEFAULTS.md.

## What runs where (requirements sec. 27, authenticity rule)
| Runs in MVS 3.8J (the emulated mainframe) | Runs on the Mac (client side) |
|---|---|
| the whole game: rules, ghost AI, levels, timing (STCK clock, STIMER waits to absolute deadlines), input decoding | c3270: draws the 3270 screen the host sends, maps the keys (the `tools/c3270_rt.sh` keymap), rings the bell when the host's alarm bit arrives (macOS Terminal bell setting) |
| every screen: the 3270 data stream (colours, highlighting, GE glyphs, partial redraw) built in COBOL and sent with TPUT | fonts and the window size (the alternate screen size is negotiated at connect) |
| the alarm bit in the Write Control Character (the only sound source) | optional Python helpers that type the `EXEC` command (`tools/rt_play.py`, `tools/gp2_live.py`) or analyse traces; they take no part in the game |
| the high-score file (`<prefix>.DATA(HISCORE)`, BPAM / QSAM via PACHSIO) | nothing persistent |
There is no companion audio, no client-side rendering and no client logic in 2.0. A Mac-side PCM companion (S3 / S4)
would be an optional client extension after 2.0 and would be labelled as such.

## Verification (MANIFEST.md)
- Built from empty libraries `HERC01.PACMAN.R20` (REL20 JOB 307, 60 steps RC 0000), regressions run-only on that exact
  module (JOBs 308-312: S2, RP, GP2 + S1 / RT / GX, GP23, HS; the 1.0-MVS oracle), every deck and listing audited
  against the old libraries.
- Installed by copy, not relinked (JOB 314), byte-identical (AMASPZAP); installed checks JOBs 315 / 316; CLIST JOB 317.
- Live smoke of the installed release (G8.4): the CLIST with no operand -> ARCADE on 120 x 27, 180/180 writes
  identical to the model, clean QUIT -> READY. Earlier live evidence stays valid (RT, S1, GP1, GP2, HS, RP, S2).
- Benchmarks: docs/BENCHMARKS.md (copy here). Capability matrix: docs/CAPABILITIES.md (copy here).

## Known limits (environment ceilings, documented)
- No Programmed Symbols in c3270 (G5 / G6 closed negative), no GDDM / host graphics on TK4- (G7): the 3270 scaled
  renderer over GE glyphs is the final MVS graphics solution.
- The maze stays 20 x 10 cells (80 x 20 at 4x2); larger canvases add centring and HUD space.
- The canvas is fixed when c3270 connects: size the window first and never shrink it while connected.
- `COLOR(AUTO)` in TURN mode holds the idle animation until the first input (D28); REALTIME is unaffected.
- Level 99 cleared = WON (intentional MVS limit).

## Contents
MANIFEST.md (identity, JOBs, reproduction), DEFAULTS.md, CAPABILITIES.md, BENCHMARKS.md, SHA256SUMS, decks/ (the
decks of record, prefix in each name: R20-* = build and verification under HERC01.PACMAN.R20, INST* = promotion and
installed checks, DATA.jcl = one-time high-score dataset on an existing install), screenshots/ (screens of the
installed release, live G8.4).

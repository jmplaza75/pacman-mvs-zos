# MVS-GS - scaled renderer: feasibility study and design (APPROVED 2026-10-08, D31) - COMPLETE (tag mvs-gs)
Baseline: tag `mvs-g5` (commit 6c44a64). Status: study + isolated probe E11 done; **PACMAN not modified**.
Goal: 1 logical maze cell = several terminal cells, so the maze is much larger, walls are true arcade contours (not
centre-lines, not filled blocks) and sprites are bigger; G4 stays the fallback; GAME/MAP/AI, PACFSIO untouched.
Model (independent, generates every byte of the probe): tools/scaled_model.py. Probe: tools/gen_probe_e11.py ->
src/probe/PACFSB.asm + PACGSP.cob + CLIST GSPROBE (deck `GSP`). Evidence: docs/evidence/gs-probe-build.txt (JOB 198),
docs/evidence/gs-e11-screens.txt (live captures).

## 1. Available geometry (live)
| Source | Value |
|---|---|
| Query Reply X'81' Usable Area (E9/E10, identical) | 80 x 24 (`0050 0018`), 12/14-bit addressing, buffer 1920 (`0780`), cell 9 x 12 |
| Query Reply X'A6' Implicit Partition | default 80 x 24, alternate 80 x 24: **no larger alternate size** |
| c3270 session (x3270if, during E11) | negotiated terminal IBM-3279-2-E; ScreenCurSize = ScreenMaxSize = 24 x 80 (the c3270 `model` reports 3279-4-E, but the session is a model 2) |
**80 x 24 = 1920 cells is the whole canvas.** It is sufficient (sections 2-3); no terminal-model change is needed or
proposed (item 10 does not arise; a 43 x 80 model-4 session would also need TK4-/VTAM definitions - out of scope).

## 2. What fits
LEVEL1 is 20 x 10 logical cells. Today (G4) it uses 200 cells = 10% of the screen.
| Scale | Board | Share of 1920 | Rows left for text | Full screen (exact, 3 ghosts + message) | <= 2048 |
|---|---|---|---|---|---|
| 2x2 | 40 x 20 | 42% | 4 rows + 38 columns beside | 1447-1457 B | yes |
| 3x2 | 60 x 20 | 62% | 4 rows + 19 columns beside | 1643-1651 B | yes |
| **4x2** | **80 x 20** | **83%** | **4 full rows (21-24)** | **1640-1683 B** | **yes** |
Text needed by the game (G1 layout): status line (G0 text, <= 61 chars), ghost positions G2/G3 (<= 17 chars), message
(INVALID COMMAND / end state), command field, help. 4 full rows hold all of them (section 3). The 2048 limit is PACFSIO's
(BUF X(2048), SENDBUF CL2060), kept unchanged: it holds only with the compressed encoding of section 7 (naive encoding of
the 4x2 screen: about 2970 bytes, model estimate).

Physical proportions: a terminal cell is about twice as tall as it is wide (c3270 in a macOS terminal font; 9 x 12 on a
real 3279). 4x2 tiles are therefore about square and the 80 x 20 board keeps LEVEL1's 2:1 shape; 2x2 tiles are tall
(board looks vertically stretched, ~1:1); 3x2 sits in between.

## 3. Layouts (all three shown live by E11; captures in docs/evidence/gs-e11-screens.txt)
**Layout B - 4x2, full width (RECOMMENDED; user's preferred sprite scale)**
```
01|┌──────────────────────────────────────────────────────────────────────────────┐
02|│  ┌────────────────────────────────┐      ┌────────────────────────────────┐  │
03|│  │ ▀█▄ •   •   •   •   •   •   •  │      │ •   •   •   •   •   •   •   •  │  │
04|│  │ ▄█▀                            │      │                                │  │
05|│  │ •  ┌──────┐ •  ┌──────────┐ •  │      │ •  ┌──────────┐ •  ┌──────┐ •  │  │
06|│  │    └──────┘    └──────────┘    └──────┘    └──────────┘    └──────┘    │  │
07|│  │ •   •   •   •   •   •   •   •  ▄°°▄ •   •   •   •   •   •   •   •   •  │  │
08|│  │                                █▀█▀                                    │  │
09|│  │ •  ┌──────┐ •  ┌──┐ •  ┌──────────────────────┐ •  ┌──┐ •  ┌──────┐ •  │  │
10|│  │    └──────┘    │  │    └───────┐      ┌───────┘    │  │    └──────┘    │  │
11|│  │ •   •   •   •  │  │ •   •   •  │      │ •   •   •  │  │ •   •   •   •  │  │
12|│  │                │  │            │      │            │  │                │  │
13|│  │ •  ┌──────┐ •  │  └───────┐ •  │      │ •  ┌───────┘  │ •  ┌──────┐ •  │  │
14|│  │    └──────┘    └──────────┘    └──────┘    └──────────┘    └──────┘    │  │
15|│  │ •   •   •   •   •   •   •   •   •  ▄°°▄ •   •   •   •   •   •   •   •  │  │
16|│  │                                    █▀█▀                                │  │
17|│  │ •   •   •   •   •   •   •   •   •   •   •   •   •   •   •   •   •  ▄°°▄│  │
18|│  │                                                                    █▀█▀│  │
19|│  └────────────────────────────────────────────────────────────────────────┘  │
20|└──────────────────────────────────────────────────────────────────────────────┘
21| T000 START X=02 Y=02 S=0000 L=100 G=19,09 V=3 ST=READY G2=10,04 G3=11,08
22| INVALID COMMAND X        (or the end-state banner: YOU WIN / GAME OVER / QUIT)
23| COMMAND ===> _    U D L R + ENTER   Q QUIT   PA2 REDRAW
24|                          (spare: kept blank)
```
(█ = blank in reverse video. Live capture of this layout = E11 screen 2, identical to the model on all 24 rows.)
- Row 21: the G0 status text unchanged (turquoise), followed by the G2/G3 positions (61 + 17 < 79 columns).
- Row 22: message line - INVALID COMMAND (red, blinking with HILITE as in G2); when ST becomes WON / LOST / QUIT an
  end-state banner (YOU WIN yellow, GAME OVER red, QUIT green). READY is shown by the status line as today.
- Row 23: command field (label green, 1-byte unprotected field underlined, cursor) and the help text.
- Row 24: spare (blank). Board rows 1-20 contain no field attributes; they belong to the protected field that wraps from
  row 23 (formatted screen as in G1: Read Modified returns only the command).
Usability: same five text items as G1 in 3 rows; nothing is cramped; no layout problem found -> 4x2 preferred.

**Layout C - 3x2 + side panel (fallback/compromise)**: board 60 x 20 rows 2-21, cols 1-60; panel cols 62-80 (turn,
score, pellets, lives, ghosts, state, `CMD ===>` field, message truncated to 18 chars, help on 3 lines). Fits (1651 B),
tighter panel. Kept as the alternative scale `SCALE(3)` (section 8).
**Layout A - 2x2 + side panel**: functional, but cramped sprites and a vertically stretched maze; not proposed.

## 4. Mapping: logical wall cell (x, y) -> 4x2 tile
Logical cell (x, y), 0-based, covers terminal rows `1 + 2y .. 2 + 2y` and columns `1 + 4x .. 4 + 4x` (layout B:
board origin row 1, column 1). In buffer addresses: `a = (2y + j) * 80 + 4x + i`, j = 0..1, i = 0..3.
Sub-cell roles: (j=0,i=0) top-left corner, (0,1)(0,2) top edge, (0,3) top-right corner, (1,0) bottom-left, (1,1)(1,2)
bottom edge, (1,3) bottom-right. The same table works for 3x2 (one top/bottom edge sub-cell) and 2x2 (corners only).

## 5. Wall-contour algorithm
'open' = the neighbour is not a wall (corridor, pellet, sprite) **or lies outside the map** (this gives the arcade
double outer border). For each wall cell and each corner sub-cell, look at its two orthogonal neighbours and the
diagonal between them:
| Corner | uses | both open | vertical open only | horizontal open only | both wall, diagonal open | all wall |
|---|---|---|---|---|---|---|
| top-left | N, W, NW | `┌` | `─` (N open) | `│` (W open) | `┘` (inner corner) | blank |
| top-right | N, E, NE | `┐` | `─` | `│` | `└` | blank |
| bottom-left | S, W, SW | `└` | `─` | `│` | `┐` | blank |
| bottom-right | S, E, SE | `┘` | `─` | `│` | `┌` | blank |
Edge sub-cells: top edge = `─` if N is open, else blank; bottom edge = `─` if S is open, else blank.
Properties (checked on LEVEL1 in the model and live):
- A one-cell-thick wall gets a line on each open side, closed by corners: a genuine double-sided wall
  (`┌──────┐ / └──────┘`); a vertical one-cell stem shows `│  │`.
- Where walls meet (T-junctions, the stems under the long bars of rows 4-6), the inner-corner glyphs turn the contour
  around the junction (`└───────┐      ┌───────┘`), as in the arcade.
- The whole contour depends only on the static map: it is computed once at start, drawn by the full screen, and never
  invalidated afterwards. Walls in all profiles: blue (PACPAL), no highlighting.
- Glyphs: CP310 via GE (`┌ C5`, `┐ D5`, `└ C4`, `┘ D4`, `─ A2`, `│ 85`), all proven live in E9 and E11.

## 6. Sprites and tiles (4x2; pixel art on half blocks)
Each terminal cell = 2 vertical pixels: top `▀` (CP310 93), bottom `▄` (94), both = blank in reverse video, none = blank.
A 4x2 tile = 4 x 4 pixels (about square).
| Item | Pixels (rows top->bottom, # = on) | Cells | Colour |
|---|---|---|---|
| Pac-Man facing right | `.##.` `##..` `##..` `.##.` | `▄█▀ ` / `▀█▄ ` | yellow |
| Pac-Man facing left | `.##.` `..##` `..##` `.##.` | ` ▀█▄` / ` ▄█▀` | yellow |
| Pac-Man shut (animation frame B) | `.##.` `####` `####` `.##.` | `▄██▄` / `▀██▀` | yellow |
| Ghost frame A | `.##.` `####` `####` `#.#.` | `▄°°▄` / `█▀█▀` | red / pink / turquoise by index (D24) |
| Ghost frame B | `.##.` `####` `####` `.#.#` | `▄°°▄` / `▀█▀█` | same |
| Pellet | `•` (CP310 A3) in the top row, 2nd column | ` •  ` / `    ` | white |
| Power pellet | `....` `.##.` `.##.` `....` (reserved: the frozen core has no power pellets) | ` ▄▄ ` / ` ▀▀ ` | white |
| Empty corridor | blanks | `    ` / `    ` | - |
Ghost eyes: the two middle cells of the top row are `°` (CP310 A1) in reverse video = dark eyes on the body colour.
Facing: as G4 (D29) - last horizontal move that was not blocked; vertical moves keep it (up/down mouths are possible at
4x4 pixels; optional, not proposed now). Animation (G3 ANIM): Pac-Man open/shut, ghosts frame A/B, on the visual tick.
User assessment (E11 screen 4): 4x2 Pac-Man and ghosts are the clearest and most arcade-like; 3x2 acceptable; 2x2 cramped.

## 7. Partial redraw, animation and byte budget
The renderer keeps PACSCR's two 1920-cell virtual images (char, colour, highlight, charset) and its diff (G3); the
scaled board is rendered into the same image, so the G3/G4 mechanics apply unchanged.
- Invalidation: when logical cell (x, y) changes, exactly its 8 cells `{(2y+j)*80 + 4x+i}` change; wall cells never do.
  A player move invalidates 2 logical cells (old, new; the eaten pellet is inside the new one); each ghost move 2; an
  animation tick only the sprite cells. Status / message / field rows as today.
- Full screen (SEND, Erase/Write + D25 clear prefix added by PACFSIO): encoded with SBA only on address jumps, SA only
  on colour/highlight change, GE per CP310 glyph, **RA (`3C aa aa [08] c`) for runs where it is shorter** (the long
  `─` runs) and **SBA skips over runs of >= 4 blanks** (the buffer is nulled by the clear prefix). RA with GE and with
  the current colour/highlight is supported by x3270 (ctlr.c) and proven live (E11: row 1 = one RA+GE order).
- Partial updates (SENP, Write X'F1', WCC C2/C3): the changed runs, blanks written explicitly, cursor restored.

| 4x2 (exact, model = probe) | Bytes | G4 GRAPHIC today |
|---|---|---|
| First full screen, start position, 1 ghost | 1538 | 800 |
| Full screen, 3 ghosts + message (worst case seen) | 1640-1683 | 912 |
| Limit (PACFSIO SEND) | 2048 | 2048 |
| Player move (old -> empty, new -> Pac-Man) | 53 | - |
| Ghost move | 64 | - |
| Animation tick, Pac-Man / one ghost | 41 / 49 | 35 per tick (G3, docs/G3-PARTIAL.md) |
| E11 partials measured (move, chomp, ...) | 42-57 | - |
| Whole MOVES case, partial traffic | not yet built | 1915 (G4 doc) |
A typical turn (player + 3 ghosts + status line) is about 300 bytes - well within the turn-based rate measured in G3.
The test suite must assert `len(full stream) <= 2048` for every TSD stream (worst case = all pellets, 3 ghosts,
message, ghosts row).

## 8. Compatibility and fallback
New option `SCALE(AUTO|4|3|NO)` (PARM column 17, REQ-SCALE appended to PACREQ): default **NO** for direct calls (the
G4/G3 screens stay byte-identical), **AUTO** in the CLIST.
- The scaled renderer needs: COLOR active, HILITE active (sprite bodies are reverse video) and the GRAPHIC glyph
  resolution (GE + CP310, as G4 AUTO decides from Query Reply X'85', or GLYPHS(GRAPHIC) explicitly).
- AUTO -> 4x2 when all three hold; otherwise the existing chain: G4 GRAPHIC -> BASE -> CLASSIC -> monochrome line mode.
- SCALE(4) / SCALE(3) with a missing prerequisite falls back the same way (reverse video is never forced against
  HILITE, as D29); SCALE(NO) = today's renderer.
- Any SEND/SENP failure: existing fallback (full redraw, then line mode). PA2: full redraw of the scaled screen.
- Batch/card mode stays the reference (D18); GAME/MAP/AI see nothing of this.
- Known environment note (D28) unchanged: with COLOR(AUTO) the idle animation starts after the first input; the explicit
  TK4-/c3270 combination becomes `COLOR(YES) HILITE(YES) GLYPHS(GRAPHIC) SCALE(4)`.

## 9. Implementation plan (only after approval)
Changed: PACREQ (+REQ-SCALE, append-only), PACPAL (layout-B rows, sprite pixel tables, contour glyph codes),
PACSCR (scaled board into the virtual image; contour table computed once; RA/blank-skip in the full encoder),
PACPLAT (resolve SCALE like GLYPHS), PACMAIN (PARM column 17), CLIST (SCALE keyword). Untouched: PACGAME, PACMAP,
PACAI, PACSTATE, PACMREQ, LEVEL1 (core freeze D22), PACFSIO, PACQRY.
Dialect: no nested subscripts (D13: contour table indexed by computed address), counters PIC 9(4), column 72.
Tests (deterministic, independent model = tools/scaled_model.py promoted to tests/ref_gs_screen.py): oracle byte-identical;
SCALE(NO) streams identical to G4; every SCALE(4)/SCALE(3) TSD stream identical to the model; every full stream
<= 2048 bytes. Edge cases (D12): outer double border and its corners, inner corners, T-junctions, one-cell walls and
stems, sprite on pellet, ghost over Pac-Man (hit), 3 ghosts on one cell, last pellet + hit, facing after blocked/vertical
moves, animation frames, message + PA2 full redraw, fallback with HILITE(NO)/COLOR(NO)/no GE.
Live checklist on c3270 as in G1-G4; evidence in docs/evidence/gs-*.

## 10. Points for approval
1. Layout B, 4x2, full width (section 3); 3x2 layout C as `SCALE(3)`; 2x2 dropped.
2. Contour algorithm of section 5 with "outside = open" (double outer border).
3. Sprite set of section 6 (pixel art as shown live in the E11 gallery); pellet `•` at the 2nd column of the top row.
4. Row 22 end-state banner (YOU WIN / GAME OVER / QUIT) - a renderer-only addition.
5. Option `SCALE(AUTO|4|3|NO)`, PARM column 17, NO for direct calls, AUTO in the CLIST.
6. Phase name `MVS-GS` (the requirements ladder has no slot for it; G5/G6 closed/blocked, G7 needs graphics the Query
   Reply does not announce).

## 11. Approval (user, 2026-10-08)
All six points approved: layout B 4x2 primary (80x20 full width), SCALE(3) the smaller alternative, SCALE(NO) = G4; contour
algorithm with the double outer border, computed once; E11 4x2 sprites (Pac-Man R/L/shut, two ghost frames, existing
ghost colours), pellet top row / 2nd column, power pellet reserved; row-22 end/status banner; SCALE(AUTO|4|3|NO) in PARM
column 17; phase name MVS-GS.
Additional constraints: core (GAME/MAP/AI) frozen; PACFSIO untouched; compression in PACSCR; a changed logical cell
redraws exactly its 8 cells; partial redraw and idle animation preserved; fallback chain SCALED -> G4 GRAPHIC -> BASE ->
CLASSIC -> line mode; **direct calls without column 17 behave as SCALE(NO), byte-identical to G4 (explicit regression)**;
**AUTO uses only the capability information of the existing validated query path - no new or reordered 3270 query**;
**renderer-side size guard: no encoded screen larger than 2048 bytes is ever passed to PACFSIO (tested)**.
Visual proportions: approved from the geometry and the E11 results. The script-port captures prove the buffer contents,
NOT the physical aspect ratio; the live proportions of layout B have not yet been visually confirmed by the user
(to be recorded at the live check).

## 12. Implementation (2026-10-08) - built and tested on Hercules; live PASS (proportions 2026-10-09)
Changed (presentation/platform only; core freeze D22 intact, PACFSIO untouched):
- PACSCR: scaled board drawn into the existing 1920-cell virtual image (tiles of 4x2 / 3x2; contour table CT-CODE
  built once from the map; sprites from PACPAL), full-screen encoder ENCODE-S (RA, RA+GE, blank skips, field orders),
  scaled tick = rebuilt image + G3 diff, op ENDS (end screen), size guard (every byte goes through PUT-CHB: nothing is
  written past DS-LIMIT = 2048; an overflowing screen sets DS-OVF and the renderer falls back to the G4 screens for the
  rest of the game, sending the G4 full screen instead).
- PACPAL: LS- layout B values, LAY-SF-ROW / LAY-GHOSTS-COL / LAY-HELP-COL (G4 values by default), contour and half-block
  codes (SG-), sprite tables SPR-4 / SPR-3, pellet column.
- PACREQ: REQ-SCALE appended. PACMAIN: PARM column 17 (absent = N). PACPLAT: SCALE resolution (A -> 4; needs TSC/TSD,
  HILITE Y, GLYPHS G from the existing query path; else N), FALL-BACK -> N, op WAIT (TSC only).
- PACDISP: at END, scaled only: op ENDS, SEND, WAIT, then line mode and the usual end lines.
- PACTSO: op WAIT = STIMER 3 s (no terminal I/O). CLIST: SCALE(AUTO|4|3|NO), default AUTO.
Deviations from the draft, decided during implementation:
- End banner (user decision 2026-10-08): the game has no end screen in TSC (END restores line mode at once, D19: no
  input after the end), so the scaled renderer sends one final full screen with the banner and pauses 3 s (PACTSO
  WAIT) before line mode. No key is read. SCALE(NO) unchanged (no end screen).
- SCALE(3) uses the layout-B text rows (21-23) with the 60 x 20 board centred at column 11, not the layout-C side panel:
  one text layout for both scales (less code, same information).
- 3x2 ghost: the eye is the middle top cell (with the E11 pixel art the 3x2 ghost had no full top cell for eyes and its
  frame B looked like the shut Pac-Man).
Invalidation: a changed logical cell can only change cells inside its own 8 (6) cells (contours are static and never
change); the G3 diff then sends only those of them that differ (e.g. an eaten pellet = 1 cell).
Traffic (JOB 200, real streams): first 4x2 screen 1556-1645 bytes, largest stream 1653 (limit 2048); per turn about
90-300 bytes (status line + Pac-Man + ghosts); MOVES 5171 bytes in total (G4 GRAPHIC 2027), MULTI 8397 (G4 3112).
Tests: tests/ref_gs_screen.py (independent model), tests/test_gs.py; deck `GS` (job PACBLDGS). JOB 200: 100 steps RC
0000, no compiler warnings, oracle byte-identical, 931 TSC streams identical to the models (26 G4 runs without column 17
= G4 regression, 18 GS runs: 4x2/3x2, QUIT/EOF/LOST/WIN banners, AUTO, no-highlight/BASE/CLASSIC fallbacks, guard T,
explicit N), 395 scaled streams replayed on a 3270 buffer image equal to the model image, 12 PACQRY cases.
Geometry integration (larger canvases, 120 x 27 preferred): docs/GS-GEOMETRY.md (D32). Live validation:
docs/evidence/gs-manual-c3270.md. MVS-GS complete (tag mvs-gs).


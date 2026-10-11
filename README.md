# Pac-Man for MVS 3.8J — release 1.0-MVS

A text Pac-Man written in conservative COBOL (IBM OS COBOL, `IKFCBL00`) for MVS 3.8J (TK4-) running on Hercules.
It plays in batch, with one command per card, or interactively from a TSO 3270 session. Everything runs on the
emulated mainframe: there is no client-side extension and no sound (requirements sec. 27).

## Game
- Maze of 20x10 (`maps/LEVEL1.txt`) with 100 pellets worth 10 points each, and three lives.
- Commands: `U` `D` `L` `R` (any case) move one cell, `Q` quits. Walls block, and a blocked move still costs a turn.
- Ghosts (1 to 3) use one of four levels: `AI0` still, `AI1` random (default), `AI2` keeps its direction until an
  intersection, `AI3` chases (Manhattan distance). All levels are deterministic: the LCG seed is fixed at 12345.
- A hit costs one life and resets the player and the ghosts. The game is WON when all pellets are eaten, and LOST at
  0 lives. Rules: `docs/DECISIONS.md` D7, D9, D11 and D14.
- Output for each turn: `Txxx <cmd> <result> X= Y= S=score L=pellets G=ghost V=lives ST=state`, then the board
  (`#` wall, `.` pellet, `P` player, `G` ghost). With several ghosts there is an extra `G2=..[ G3=..]` line.
  At the end the program prints `WIN|LOST|QUIT|EOF`, `TURNS`, `SCORE` and `LIVES`.

## Requirements
- Hercules with TK4- running (`~/mainframe/tk4`, `./start_herc`), the ASCII card reader on `127.0.0.1:3505` and JES
  output in `~/mainframe/tk4/prt/prt00e.txt`. See `docs/ENVIRONMENT.md`.
- Python 3 on the host, to generate, submit and check decks.
- A TSO user that may create `<prefix>.*` datasets; the default prefix is `HERC01.PACMAN`. Put the password in a local
  `.env` file as `HERC01_PASSWORD=...`. That file is git-ignored and is never printed or committed. It is injected into
  the job card in memory and redacted in saved listings.

## Install and build from scratch
```sh
python3 tools/make_deck.py ALLOC   && python3 tools/run_deck.py build/ALLOC.jcl     # first use only
python3 tools/make_deck.py CLIST   && python3 tools/run_deck.py build/CLIST.jcl     # TSO launcher
./tools/release_check.sh                                                         # build + full regression
```
Use `--prefix HLQ.NAME` with `make_deck.py`, and pass the prefix as the argument of `release_check.sh`, to install
under a different prefix. 1.0-MVS was rebuilt this way from empty libraries under `HERC01.PACMAN.R10`
(`docs/evidence/mvs9-fresh-r10-*`).

The build deck (`RELEASE`, job `PACREL10`) does the following:
1. Uploads 3 copybooks and 7 COBOL sources with IEBGENER.
2. Compiles them with IKFCBL00 and assembles the `PACTSO` stub with IFOX00.
3. Links everything with IEWL into `<prefix>.LOAD(PACMAIN)`.
4. Runs the 19 batch regression cases and 6 interactive-mode replays.

`release_check.sh` first runs every local check, then submits the deck, waits for the job and verifies it with
`tests/test_mvs8.py`. The checks are:
- all steps end with RC 0000;
- each run's output equals the independent Python model;
- batch output is byte-identical to the accepted MVS-7 output;
- the AI and lives properties hold, re-derived from the real output;
- the interactive transcripts are correct.

Ready-made decks for the default prefix are in `releases/1.0-MVS/` (`ALLOC`, `CLIST`, `BUILD`, `RUN`). That folder
also holds `SHA256SUMS` for the sources.

## Play in batch
```sh
python3 tools/make_deck.py RUN --cards my-game.txt && python3 tools/run_deck.py build/RUN.jcl
```
The card file has one command per line. An optional first line `AI<l> <n>` picks the level and the number of ghosts,
for example `AI3 2`. The game is printed in the job listing.

## Play interactively (TSO, 3270)
**Real time (MVS-RT, the default):** size a macOS Terminal window to 120x30, start the terminal with the game keymap and
log on to TSO, then start the game from a second shell:
```
TYPEAHEAD=false tools/c3270_rt.sh          (c3270 120x27, arrows = PF7/8/10/11, typeahead off)
python3 tools/rt_play.py                   (at TSO READY: EXEC ... 'PLAY(REALTIME)', P = PF9 pause while it runs)
```
Pac-Man waits until the first arrow, then keeps moving by himself every 150 ms; the ghosts move on their own (4/5 of
his speed). An arrow pressed before an opening is remembered for 3 steps and taken at the first chance; the opposite
arrow reverses at once. P (PF9) pauses and resumes (`PAUSED` banner), PA2 redraws, Q + ENTER quits; U/D/L/R/P + ENTER
also work. Do not use CLEAR (TSO swallows it). Without colour full-screen mode the game plays TURN. Design and
measurements: `docs/RT-REALTIME.md` (D33, D34), `docs/evidence/rt-e14-timing.md`, `docs/evidence/rt3-live.md`.
**Turn by turn (compatibility):** `EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'PLAY(TURN)'` plays one move per command, as
below. Log on to TSO (`c3270 localhost:3270`) and run from `READY` (add `PLAY(TURN)` for the turn-by-turn game):
```
EXEC 'HERC01.PACMAN.CLIST(PACMAN)'
EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'AI(3) GHOSTS(2)'
EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'COLOR(NO)'
EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'HILITE(NO)'
EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'ANIM(NO) REDRAW(FULL)'
EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'COLOR(YES) HILITE(YES)'     (recommended on TK4-/c3270: idle animation at once)
EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'COLOR(YES) HILITE(YES) GLYPHS(GRAPHIC)'   (TK4-/c3270: solid walls + APL sprites)
EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'GLYPHS(BASE)'      (or CLASSIC: the # . C/O G/W look)
EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'COLOR(YES) HILITE(YES) GLYPHS(GRAPHIC) SCALE(4)'   (TK4-/c3270: large 4x2 maze)
EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'SCALE(NO)'         (or 3: smaller 3x2 maze)
```
`SCALE(AUTO|4|3|NO)` (MVS-GS) draws each maze cell as 4x2 (or 3x2) screen cells: the maze fills rows 1-20, walls are
arcade-style double contour lines, Pac-Man and the ghosts are larger half-block sprites, and the game ends on a screen
with a YOU WIN / GAME OVER / QUIT banner shown for 3 seconds. It needs colour, highlighting and the GRAPHIC glyphs (AUTO
scales only when all three are active); otherwise the GLYPHS look above is used. See `docs/GS-SCALED.md`.
`CANVAS(AUTO|DEFAULT)` (MVS-GS geometry, CLIST default AUTO) uses the terminal's larger alternate screen when it has one:
on 120x27 or 132x27 the 4x2 maze is centred with a score/lives/ghosts panel on each side, on 80x32 / 80x43 it is centred
vertically; DEFAULT keeps 80x24. The canvas is fixed when c3270 connects, so **size the terminal window before
connecting and never shrink it below that size while connected** (c3270 cannot recover the display). For a usual
120x30 macOS Terminal window: `c3270 -model 2 -oversize auto localhost:3270` (120x27). Other options: `-model 5`
(window >= 132x30), `-model 4` (>= 46 rows), `-model 3` (>= 36 rows). See `docs/GS-GEOMETRY.md`.
`GLYPHS(AUTO|GRAPHIC|BASE|CLASSIC)` (MVS-G4) picks the board look in colour mode: GRAPHIC and BASE draw walls as solid
blue blocks (reverse video; `#` with `HILITE(NO)`); GRAPHIC draws pellets, Pac-Man and ghosts with APL symbols (3270 GE
order, code page 310), BASE with normal characters; AUTO uses GRAPHIC when the capability query announces it (with
`COLOR(YES)` there is no query, so name GRAPHIC explicitly). See `docs/G4-GLYPHS.md`.
With a colour terminal (COLOR(AUTO), the default) the game runs full-screen in colour: type the command in
`COMMAND ===>` and press ENTER, PA2 redraws, Q quits. COLOR(NO) keeps the monochrome line mode described below.
Type `U/D/L/R` and press ENTER for each move, and `Q` to quit. An empty ENTER redraws the board. Each turn starts on a
fresh screen, so TSO's `***` paging does not interrupt play (`docs/INTERACTIVITY.md`). Several invalid commands in a
row can still fill the screen once. Validated live in c3270.

## Architecture and documentation
- `PACMAIN` is the driver; the layers are `PACGAME`, `PACMAP` and `PACAI` (portable core), `PACINPT` and `PACDISP`
  (adapters), and `PACPLAT` with `PACTSO` (platform). See `docs/ARCHITECTURE.md`.
- `docs/DECISIONS.md` records the compiler dialect rules and the game rules (D1–D30).
- `docs/mvs-build.md` holds the per-phase build history and evidence, and `docs/CURRENT_PHASE.md` the status.

## Phases
MVS-G0 (stable visual baseline: core frozen, 1.0-MVS oracle, optional METRICS, replaceable display, capability
matrix `docs/CAPABILITIES.md`) is complete (tag `mvs-g0`).
MVS-G1 (colour full-screen mode TSC: `COLOR(AUTO|YES|NO)` in the CLIST, auto-detected via Query Reply, monochrome
line mode as fallback; design `docs/G1-RENDERER.md`) is complete (tag `mvs-g1`).
MVS-G2 (highlighting: `HILITE(AUTO|YES|NO)` in the CLIST, reverse P/G, blinking INVALID message, underlined input field;
design `docs/G2-HIGHLIGHT.md`) is complete (tag `mvs-g2`; validated on Hercules, JOB 164, and live in c3270).
MVS-G3 (partial redraw `REDRAW(PARTIAL|FULL)` and glyph animation `ANIM(AUTO|YES|NO)` with an idle visual tick; design and
known limitation in `docs/G3-PARTIAL.md`) is complete. Known limitation: with `COLOR(AUTO)` (default) the idle animation starts after the
first input because TSO holds the ticks after the capability query; use `'COLOR(YES) HILITE(YES)'` on TK4-/c3270 for immediate animation.
MVS-G4 (glyph profiles `GLYPHS(AUTO|GRAPHIC|BASE|CLASSIC)`: filled walls, APL pellets/Pac-Man facing left/right/ghosts,
base-set pellets; CLASSIC = the G3 screens; design `docs/G4-GLYPHS.md`, probe E9 `docs/evidence/g4-probe-analysis.md`) is complete
(tag `mvs-g4`; Hercules JOB 195 and live in c3270). Arcade wall contours are deferred to a future 2x2 scaled renderer.
MVS-G5 (Programmed Symbols, isolated probe E10) is closed negative (tag `mvs-g5`): PS are not supported in the validated
TK4-/MVS 3.8J + TSO + c3270 environment (no loadable sets announced, Load PS rejected by c3270, no host-defined glyph shown);
G4 is the production character-set ceiling. MVS-G6 (multicolour PS) is blocked / not applicable here. See
`docs/evidence/g5-probe-analysis.md` (D30). Next visual step: a 2x2 scaled renderer.
MVS-GS (scaled renderer and geometry: 4x2 maze with arcade contour walls and half-block sprites,
`SCALE(...)` and `CANVAS(...)`, larger canvases up to 132x27; preferred 120x27 IBM-DYNAMIC for a 120x30 macOS Terminal,
80x24 fallback; design `docs/GS-SCALED.md`, `docs/GS-GEOMETRY.md`) is complete (tag `mvs-gs`; Hercules JOBs 200/207 and
live in c3270). The maze stays 80x20 at 4x2: larger canvases add centring and HUD space, not maze scale.
MVS-RT (real-time gameplay: `PLAY(REALTIME|TURN)`, REALTIME the CLIST default; 150 ms absolute-deadline clock,
arrows = PF7/8/10/11, PF9 pause, buffered turns, autonomous ghosts at 4/5 speed, one write per quantum with keyboard
restore; probe E14 + design D33 in `docs/RT-REALTIME.md`) is complete (tag `mvs-rt`; Hercules JOB 226 and live in c3270,
`docs/evidence/rt3-live.md`). TURN is unchanged (1.0-MVS oracle and all earlier regressions pass).
MVS-0 to MVS-9 are complete (tags `mvs-2`..`mvs-8`; release tag `1.0-MVS`). Next is the z/OS migration
(ZOS-0..ZOS-7) or the graphic ladder after 1.0-MVS (MVS-G0+), which has not started.

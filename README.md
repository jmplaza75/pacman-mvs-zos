# Pac-Man for MVS 3.8J — release 2.0-MVS-MAX (final MVS release)

A Pac-Man written in conservative COBOL (IBM OS COBOL, `IKFCBL00`) with three small assembler services, for MVS 3.8J
(TK4-) on Hercules. Release 2.0-MVS-MAX plays the arcade game in real time on a scaled, coloured 3270 screen with the
terminal bell as sound, and picks the best presentation the terminal supports automatically. Everything in the game
runs on the emulated mainframe (see "What runs where"). Release notes, manifest, final defaults, benchmarks,
capability matrix and screenshots: `releases/2.0-MVS-MAX/`. Design of the release: `docs/G8-RELEASE.md` (D43).

**z/OS: release 2.0-zos** (branch `zos`) runs the same 2.0 game on IBM z/OS (IBM Z Xplore) - see "PAC-MAN 2.0 for
z/OS" below and `releases/2.0-ZOS/`.

## Quick start (2.0)
1. Hercules / TK4- running; size a macOS Terminal window to 120x30 **before** connecting, then
   `TYPEAHEAD=false tools/c3270_rt.sh` (c3270 on the 120x27 alternate screen, arrows = PF7/8/10/12) and log on to
   TSO.
2. At `READY`: `EXEC 'HERC01.PACMAN.CLIST(PACMAN)'` — no operand needed (or `python3 tools/rt_play.py` from a second
   shell, which also maps P to PF9 = pause while the game runs; PF9 itself always pauses).
3. Pac-Man waits for the first arrow, then moves by himself every 150 ms; Q + ENTER quits.

With no operand the launcher selects the 2.0 profile: ARCADE rules (power pellets, levels, fruit, persistent high
score, READY!, death animation, popups), REALTIME, colour full-screen with highlighting, GRAPHIC glyphs, the 4x2 maze
centred on the larger screen, partial redraw and alarm patterns. Each feature falls back on its own when the terminal
lacks it (no APL set -> the G3 colour look; 80x24 -> compact layout; no colour -> line mode, turn by turn). The final
defaults are frozen in `releases/2.0-MVS-MAX/DEFAULTS.md`; `RULES(CLASSIC)` plays the 1.0-MVS game, and batch runs are
unchanged (a PARM without the RULES column is CLASSIC).

## What runs where (requirements sec. 27)
- **In MVS 3.8J:** the whole game — rules, ghost AI, levels, the real-time clock (STCK, STIMER to absolute deadlines),
  input decoding, every screen as a 3270 data stream built in COBOL and sent with TPUT, the alarm bit that rings the
  bell, and the high-score file `HERC01.PACMAN.DATA(HISCORE)`.
- **On the Mac (client):** only the c3270 terminal (it draws what the host sends, maps the keys, rings the bell when the
  alarm bit arrives — Terminal > Settings > Profiles > Advanced > "Audible bell"), and optional Python helpers that type
  the `EXEC` command or analyse traces. No companion audio, client rendering or client logic exists in 2.0.

## 1.0-MVS game (RULES(CLASSIC), batch reference)
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
2.0 (the build of record was made this way under `HERC01.PACMAN.R20`, `releases/2.0-MVS-MAX/MANIFEST.md`):
```sh
python3 tools/make_deck.py ALLOC --prefix HLQ.NAME && python3 tools/run_deck.py build/ALLOC.jcl   # empty libraries
./tools/release_check.sh 2.0 HLQ.NAME          # REL20 build + run-only S2/RP/GP2/GP23/HS regressions + tests/test_g8.py
python3 tools/make_deck.py CLIST --prefix HLQ.NAME && python3 tools/run_deck.py build/CLIST.jcl   # TSO launcher
python3 tools/make_deck.py INST20 --source HLQ.NAME --prefix TARGET   # optional: copy the validated PACMAIN, no relink
```
The 1.0-MVS procedure below is kept for the historical release:
```sh
python3 tools/make_deck.py ALLOC   && python3 tools/run_deck.py build/ALLOC.jcl     # first use only
python3 tools/make_deck.py CLIST   && python3 tools/run_deck.py build/CLIST.jcl     # TSO launcher
python3 tools/make_deck.py DATA    && python3 tools/run_deck.py build/DATA.jcl      # high-score dataset (existing install)
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
TYPEAHEAD=false tools/c3270_rt.sh          (c3270 120x27, arrows = PF7/8/10/12, typeahead off)
python3 tools/rt_play.py                   (at TSO READY: EXEC ... 'PLAY(REALTIME)', P = PF9 pause while it runs)
```
Pac-Man waits until the first arrow, then keeps moving by himself every 150 ms; the ghosts move on their own (4/5 of
his speed). An arrow pressed before an opening is remembered for 3 steps and taken at the first chance; the opposite
arrow reverses at once. P (PF9) pauses and resumes (`PAUSED` banner), PA2 redraws, Q + ENTER quits; U/D/L/R/P + ENTER
also work. Do not use CLEAR (TSO swallows it). Without colour full-screen mode the game plays TURN.
Sound (MVS-S1): the terminal bell rings when the game starts, when Pac-Man dies and when he wins (`SOUND(AUTO)`, the
default; `SOUND(NO)` = silent). Turn on macOS Terminal > Settings > Profiles > Advanced > "Audible bell".
**Alarm patterns (MVS-S2):** `ALARM(PATTERN)` (the CLIST default) gives each event its own number of bells: start 1,
death 2, extra life 2, level clear 3, game over 3, win 4, two quanta apart (300 ms; three quanta = 375 ms with
`SPEED(FAST)`). The bells ride on frames the game sends anyway: no extra wait or write during play. After a win or a
game over, the remaining bells ring inside the usual 3-second end pause, which never gets longer. TURN games ring the
first bell of each event during play and the full win / game-over pattern at the end. `ALARM(SINGLE)` keeps one bell
per event (the MVS-S1 / GP2 behaviour); `SOUND(NO)` silences every alarm, PATTERN and SINGLE alike. Example:
`EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'RULES(ARCADE) ALARM(SINGLE)'`. Design: `docs/S2-PATTERNS.md` (D41). Design and
measurements: `docs/RT-REALTIME.md` (D33, D34), `docs/evidence/rt-e14-timing.md`, `docs/evidence/rt3-live.md`.
**Arcade rules (MVS-GP1):** `EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'RULES(ARCADE)'` adds 4 blinking power pellets `o`
(50 points), blue frightened ghosts (white just before the end; 40 quanta = 6 s, 20 turns in TURN) that flee more slowly,
eaten ghosts 200/400/800/1600 that go home as eyes and revive, and a 7-digit score. `RULES(ARCADE)` is the default since
2.0-MVS-MAX; `RULES(CLASSIC)` is the 1.0-MVS game. Design: `docs/GP1-POWER.md` (D36).
**Speed and presentation (MVS-RP):** `SPEED(NORMAL|FAST)` sets the REALTIME quantum to 150 ms (default) or 125 ms:
with FAST, Pac-Man and the ghosts move faster, while frightened time, the fruit, the death / level-clear freeze, READY!,
the death animation and the score popups keep their length in seconds. `RULES(ARCADE)` games show READY! before the
start and after a death, a 6-frame death animation (also before GAME OVER), a popup with the points of an eaten ghost
or fruit, and the high score in the HUD and on the end screen. Try it:
`EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'RULES(ARCADE) SPEED(FAST)'`. TURN games ignore SPEED. Design: `docs/RP-POLISH.md`.
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

## PAC-MAN 2.0 for z/OS (release 2.0-zos)
The 2.0-MVS-MAX game ported to IBM z/OS V3R1 (Enterprise COBOL 6.5, HLASM R6.0, the z/OS binder, LE, TSO / VTAM /
TN3270E), with only the registered z/OS differences (`docs/ZOS-DIFFS.md`, Z1-Z6). Release material (notes, manifest,
defaults, capability matrix, decks of record, SHA256SUMS): `releases/2.0-ZOS/`; evidence:
`docs/evidence/zos10-release.md` (release) and `docs/evidence/zos9-equivalence.md` (equivalence with the MVS oracle).
- **Play:** window 120 x 30 before connecting, `c3270 -model 2 -oversize auto 198.51.100.200:623`, log on, then at TSO
  READY or in ISPF option 6: `EXEC 'Z00000.PACMAN.CLIST(PACMAN)'` (no operand = ARCADE, REALTIME, automatic
  profile). Arrows = PF7 / PF8 / PF10 / PF12 (the `tools/c3270_rt.sh` keymap), PF9 pause, PA2 redraw; quit = type Q,
  then ENTER (no PF key quits). Right is PF12 from 2.1-zos on (ZOS-11, D46, `docs/zos11-design.md`); PF11 does
  nothing in REALTIME. The installed 2.0-zos release keeps Right = PF11 until 2.1-zos is installed.
- **z/OS presentation default:** with PLAY(REALTIME) the launcher selects `PRESENT(COALESCED)` (logic every 150 / 125
  ms, a screen write every 2nd / 3rd quantum), because one write per quantum is not viable over z/OS TSO / VTAM /
  TN3270E; `PRESENT(EVERY)` stays selectable, `PLAY(TURN)` keeps its historical PARM (`releases/2.0-ZOS/DEFAULTS.md`).
- **What runs where:** as on MVS - the whole game (rules, AI, clock, input decoding, every 3270 screen, the alarm bit,
  the high score in `Z00000.PACMAN.DATA(HISCORE)`) runs on z/OS; the Mac only runs c3270 and optional helpers.
- **Build / install:** from empty `<HLQ>.PACMAN.RZ.*` libraries with the decks in `releases/2.0-ZOS/decks/`
  (`@@HLQ@@` templates, submitted by `tools/zowe/zos_submit.py --hlq <HLQ>`; procedure `docs/zos-build.md`,
  `docs/zos10-design.md`). Rollback: `LOAD(PACZ6D)` and `PRV.CLIST(PACMAN)`.

## Architecture and documentation
- `PACMAIN` is the driver; the layers are `PACGAME`, `PACMAP` and `PACAI` (portable core), `PACINPT` and `PACDISP`
  (adapters), and `PACPLAT` with `PACTSO` (platform). See `docs/ARCHITECTURE.md`.
- `docs/DECISIONS.md` records the compiler dialect rules and the game rules (D1–D43).
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
arrows = PF7/8/10/11 (Right = PF12 since D46), PF9 pause, buffered turns, autonomous ghosts at 4/5 speed, one write per quantum with keyboard
restore; probe E14 + design D33 in `docs/RT-REALTIME.md`) is complete (tag `mvs-rt`; Hercules JOB 226 and live in c3270,
`docs/evidence/rt3-live.md`). TURN is unchanged (1.0-MVS oracle and all earlier regressions pass).
MVS-S1 (sound: `SOUND(AUTO|YES|NO)`, the 3270 alarm - the terminal bell - on start, death and win in colour full-screen
mode; probe E15 `docs/evidence/s1-e15-alarm.md`, D35): complete (tag `mvs-s1`; Hercules JOB 236 and live in c3270, `docs/evidence/s1-live.md`).
The bell is sent by MVS in the 3270 data stream; only hearing it depends on the client (the terminal's bell setting).
MVS-GP1 (power pellets under `RULES(ARCADE)`, D36; CLASSIC byte-identical): complete (tag `mvs-gp1`; Hercules JOB 240
(`tests/test_gp1.py`), live in c3270 with both games byte-identical to the model, `docs/evidence/gp1-live.md`).
MVS-GP2 (levels, progression, fruit and one extra life under `RULES(ARCADE)`, D37, `docs/GP2-PROGRESSION.md`):
complete (tag `mvs-gp2`; live in c3270 with three scripted scenarios byte-identical to the model,
`docs/evidence/gp2-live.md`). GP2.2 (core, text output, model): Hercules JOB 244 (`tests/test_gp2.py`, 71 ARCADE runs = model,
CLASSIC byte-identical). Levels 1-99 (clearing level 99 = WON, an intentional MVS limit), the maze refills on a full
clear, a per-level table (AI, ghost cadence, fright), a fruit at (10,8) after 30 / 70 items (cherry 100 ... key 5000),
one extra life at 10000, start level `LEVEL(n)` (PARM columns 22-23; default 1). GP2.3 (colour screens: fruit `%`
in every glyph profile and scale, level and fruit in the HUD / status line, alarm on the extra life and a level clear)
complete: Hercules JOB 246 (43 TSD runs = model) and JOB 247 (regression). Try it:
`EXEC 'HERC01.PACMAN.CLIST(PACMAN)' 'RULES(ARCADE) LEVEL(9)'`.
MVS-HS (persistent ARCADE high score, D38, `docs/HS-HISCORE.md`): complete (tag `mvs-hs`; Hercules JOB 260
(`tests/test_hs.py`, 21 runs = model), live in c3270, `docs/evidence/hs-live.md`). One global high score in
`HERC01.PACMAN.DATA(HISCORE)` (one record: score, `PACHS001`, level reached), read at the start of a `RULES(ARCADE)`
game and rewritten only when beaten by a game started at level 1 (`LEVEL(n>1)` shows it, never saves it). The end lines
show `HIGH SCORE nnnnnnn LEVEL nnn` and `NEW HIGH SCORE` / `HIGH SCORE NOT SAVED` / `START LEVEL nn: HIGH SCORE NOT
RECORDED`, or `HIGH SCORE UNAVAILABLE` when the dataset is missing (the game still plays). A missing, empty or
malformed member counts as 0 and is healed by the next save; disk problems never abend the game. Create the dataset
once on an existing install: `python3 tools/make_deck.py DATA && python3 tools/run_deck.py build/DATA.jcl` (the ALLOC
deck creates it on a fresh install; COMPRESS and rebuilds never touch it). Batch play with the high score:
`make_deck.py RUN --cards FILE --parm 'BAT                 A' --hiscore`.
MVS-RP (presentation and gameplay polish, D39 / D40, `docs/RP-POLISH.md`): complete (tag `mvs-rp`; Hercules deck RP
JOB 285 (`tests/test_rp.py`: 60 ARCADE TSD runs = 6265 model streams, the SPEED runs, the startup sequences), installed
JOB 286/287, live in c3270: `docs/evidence/rp3-fast-live.md`, `docs/evidence/rp-live.md`). ARCADE READY!, death
animation, ghost / fruit popups, HUD and end-screen high score; `SPEED(NORMAL|FAST)` (150 / 125 ms, timers converted
so they keep their wall-clock length; an authorised core change, `docs/CORE_CHANGES.md`); the PACFSIO abend exit
validated live with a test driver; startup hardened against a pending TSO `***` (D40: only a valid Query Reply is
accepted); a 10-minute pause soak. CLASSIC screens and every earlier reference unchanged.
MVS-S2 (alarm patterns, D41, `docs/S2-PATTERNS.md`): complete (tag `mvs-s2`). `ALARM(PATTERN|SINGLE)` (PARM column 25;
absent or any other value = SINGLE, byte for byte the S1 / GP2 behaviour; CLIST default PATTERN); display and platform
only (GAME / MAP / AI / PACARC / PACRT unchanged). Hercules deck S2 JOB 290 (`tests/test_s2.py`: 25 TSD runs = 2986
model streams of the independent pattern model `tests/ref_s2.py`, 21 documented edge cases), SINGLE regression RP 291 /
GP2 293 / HS 294; installed JOB 297 / 298 (PACMAIN) and 299 (CLIST); live in c3270 with six scripted runs byte-identical
to the models and the bells heard as separate (`docs/evidence/s2-live.md`).
MVS-G7 (host graphics) is closed negative (tag `mvs-g7`, D42), a capability limit, not a failed implementation: the 3270 Query Reply and c3270 offer no graphics, and a read-only
check of the TK4- catalog, link list and LPA (`jcl/mvs/G7CHK.jcl`, JOB 301) found no GDDM. The existing
GS scaled renderer over G4 glyphs is the final MVS graphics solution; nothing in the game changed. Evidence: `docs/evidence/g7-gddm-check.md`.
Roadmap to the final MVS release 2.0-MVS-MAX: `docs/ROADMAP-POST-RT.md`.
MVS-G8 / 2.0-MVS-MAX (final MVS release, D43, `docs/G8-RELEASE.md`): CLIST default `RULES(ARCADE)` (the rest of the
AUTO chain was already the maximum), rebuild from empty libraries `HERC01.PACMAN.R20` (REL20 JOB 307) with every
regression run-only on that module (JOBs 308-312), installed by copy with byte identity (JOB 314, AMASPZAP) and checked
(JOBs 315-317), live smoke of the installed release (`docs/evidence/g8-live.md`), benchmarks `docs/BENCHMARKS.md`,
final capability matrix `docs/CAPABILITIES.md`, release folder `releases/2.0-MVS-MAX/`.
MVS-0 to MVS-9 are complete (tags `mvs-2`..`mvs-8`; release tag `1.0-MVS`). The MVS line ends with 2.0-MVS-MAX; any
z/OS work is a separate roadmap, and the companion audio (S3/S4) is an optional client extension after 2.0.
ZOS-0 to ZOS-10 (branch `zos`, tags `zos-*`) port 2.0 to z/OS: ZOS-9 proved the final MVS / z/OS equivalence (tag
`zos-9`), ZOS-10 built, verified and installed the release (tags `zos-10` and `2.0-zos`; `docs/evidence/zos10-release.md`).

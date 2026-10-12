# MVS-GP2: levels, progression and bonus fruit under RULES(ARCADE) - design (D37, APPROVED 2026-10-12)
Source: docs/ROADMAP-POST-RT.md row 3 ("level counter, maze refill on clearing it, per-level table (ghost cadence, AI
level, fright time), extra life at 10000, fixed-position bonus fruit per level. Lives counter widened") and the GP1
design (D36, docs/GP1-POWER.md), which GP2 extends without changing its rules. No probe is needed: nothing here uses a
capability that is not already proven (screens reuse the GP1.3 machinery, REALTIME freeze reuses the death freeze).
Status: approved by the user on 2026-10-12 with the decisions of section 9 (incorporated below); D37 frozen in
docs/DECISIONS.md. GP2.2 = core + text + model + deck only; GP2.3 (screens) starts only when GP2.2 is green.

## 0. Steps
| Step | Content | Exit |
|---|---|---|
| GP2.1 | this design | user approval -> D37 frozen in DECISIONS.md, core change authorised |
| GP2.2 | core + text: PACGAME (level table, level clear, fruit, extra life), PACARC (appended fields), PACRT (per-level cadence, level freeze), PACMAIN (start level), PACDISP text lines, CLIST | deck `GP2`, tests/test_gp2.py: CLASSIC = every earlier reference byte for byte; ARCADE batch TURN + REALTIME + TSO line = independent model |
| GP2.3 | screens: fruit in every glyph profile / scale / layout, level shown, bells | ARCADE TSD runs = screen models; CLASSIC TSD streams unchanged |
| GP2.4 | live c3270 checklist | evidence docs/evidence/gp2-live.md, README, tag `mvs-gp2` |

## 1. Scope rule
Everything is ARCADE only (`ARC-ON = 1`). CLASSIC = 1.0-MVS byte for byte (batch SYSOUT, oracle, TURN/RT/S1 streams).
GP1 rules (power pellets, fright, chain, eyes, collision order GP1-POWER 4.4, pause freezing every timer) are not
changed; GP2 only replaces the single GP1 constants row by a per-level row and adds what happens around them.
GP1 ARCADE references are not kept byte-identical (the game no longer ends at the first cleared maze, fruit appears,
two end lines widen); the GP1 edge cases are rerun against the extended model (section 7).

## 2. ARCADE state: fields appended to PACARC (own 01 unchanged, D16)
```
    05  ARC-LEVEL    PIC 999.     current level (1 at start, or the start level, 5)
    05  ARC-AIB      PIC 9.       configured AI level (config card); AI-LEVEL is derived from it per level
    05  ARC-KNUM     PIC 99.      REALTIME normal-ghost accumulator step of the level (denominator 10)
    05  ARC-BV       PIC 9(4).    fruit points of the level (from the table)
    05  ARC-BK       PIC X.       fruit kind of the level: C S O A M G B K (section 4.4)
    05  ARC-BX/BY    PIC 99.      the fruit cell (from PACGAME, for the displays)
    05  ARC-ITEMS    PIC 999.     items ('.' and 'o') eaten in this level (fruit thresholds)
    05  ARC-BN       PIC 9.       fruits spawned in this level (0-2)
    05  ARC-BT       PIC 999.     fruit ticks left (0 = no fruit on the board)
    05  ARC-XL       PIC 9.       the EXTRA-LIFE-AWARDED flag: 1 = the 10000 life was given (never reset in a game)
    05  ARC-TURNS    PIC 9(7).    ARCADE turn counter (TICK-COUNT mirrors its low 3 digits, 4.7)
    05  ARC-EATN4    PIC 9(4).    ghosts eaten in the game (ARC-EATEN 999 cannot hold 99 levels x 12, 4.7)
    05  ARC-FRUITS   PIC 999.     fruits eaten in the game
    05  ARC-NDIE     PIC 99.      lives lost in the game (at most 4; for the GP2.3 bell, never inferred from LIVES)
    05  ARC-EVF      group X(5)   events of this step (ARC-EA/EF/EX/EC/ED), one column each: A fruit appeared,
                                  F fruit eaten, X extra life, C level cleared, D life lost ('-' = no); reset by ATIK
```
Appended after `ARC-GH`, so every GP1 offset is kept. ARC-EATEN stays (mirrors the low 3 digits of ARC-EATN4 for
any GP1 reader). PACSTATE, PACMREQ, LEVEL1 and ARCADE1 unchanged. PACREQ gains `REQ-START PIC 99` (append-only).

## 3. Core changes (authorised-core-change procedure)
- PACGAME: table K-LVL (13 rows, section 4.2) replaces the fright/warning columns of K-ARC; K-ARC keeps the
  per-mode values that do not depend on the level (eyes wait, frightened step, fruit time); the fixed GP2 values
  (fruit cell, thresholds, 10000, final level 99) are named constants next to it. Nothing level-dependent lives in
  PACAI, PACRT or the displays (they read the copies in PAC-ARC). New paragraphs LEVEL-ROW, LEVEL-START,
  LEVEL-CLEAR, ARC-LOSE, XLIFE, FRUIT-SPAWN, FRUIT-EAT, ARC-TICKS; the fruit timer ticks in ATIK; ARCADE branches at
  the end of DO-MOVE / DO-GHOSTS, in DO-INIT, LOSE-LIFE, ARC-EAT and EAT-GHOST; DO-CONFIG also records ARC-AIB.
  CLASSIC behaviour unchanged.
- PACMAP, PACAI: unchanged (the refill is a second `LDA`; PACAI only sees AI-LEVEL, which PACGAME sets per level).
- PACARC: the appended fields of section 2.

## 4. Rules (ARCADE)
### 4.1 Level clear and refill
Authoritative summary (user decisions 2026-10-12):
- score and lives persist across levels; the level increments only after the current maze is completely cleared;
- the new level reloads every item: 96 small pellets + 4 power pellets with 1 ghost (one home cell fewer per extra
  ghost: 99 / 98 items with 2 / 3 ghosts, as in GP1); Pac-Man and every ghost return to their initial cells;
- FRIGHTENED, the warning window, EYES (returning), the ghost-eaten chain and their cadence accumulators / timers are
  reset at the transition; the fruit, its timer and both fruit thresholds are reset for the new level;
- the EXTRA-LIFE-AWARDED flag is not reset (one extra life per game);
- AI, cadence and fright constants are taken from the new level's row after the level is incremented;
- pause (and the pre-start wait and the freeze) stops every GP2 timer, as every GP1 timer;
- the ordering "last item + collision + scoring / extra life" below is authoritative and is the ordering of the
  independent model (tests/ref_gp2.py).
- A level is cleared when PELLETS-LEFT = 0 at the end of a step (after both hit checks and the life loss, the 1.0-MVS
  order). In ARCADE this no longer ends the game: EAT-PELLET still sets F-WON (so the ghosts do not move after the last
  item, as today), and the end of the step turns it into a level clear.
- Level clear (LEVEL-CLEAR): ARC-LEVEL + 1; maze reloaded with `LDA` (all `.`, 4 `o`, ARC-POWER 4); Pac-Man to 2,2;
  every ghost N at its home with its home direction; the GP1 death reset (fright, chain, accumulators, eyes, pending
  reversals all 0); fruit removed, ARC-ITEMS 0, ARC-BN 0; the new row applied (4.2); PELLETS-LEFT recounted; F-WON 0;
  LAST-RESULT `CLEARED`; flag C. Kept: score, lives, ARC-XL, GHOST-SEED (the LCG continues), TICK-COUNT/ARC-TURNS,
  every game total.
- Final level: clearing level 99 ends the game WON (`GAME-STATE WON`, end `WIN`). This is an intentional MVS
  implementation limit, not an attempt to reproduce the endless arcade progression (nor its level-256 screen): the
  game does not clamp at 99 and continue. It bounds every per-game counter (4.7). Levels 13-99 reuse row 13.
- Same step as a death: the life is lost first; with lives left the level is cleared (LAST-RESULT `CLEARED`, flags C
  and D); at 0 lives the game is LOST and the level is not advanced (the GP1/1.0-MVS rule "LOST at 0 lives").
- REALTIME: a level clear freezes 10 quanta exactly like a death (PACRT, flag C), then play resumes on the new maze
  with the normal-ghost accumulator and ARC-FACC at 0 and Pac-Man's current direction cleared (as after a death).
- TURN: the next MOVE is the first turn of the new level. TSO line mode: as TURN.

### 4.2 Per-level table K-LVL (TURN in turns, REALTIME in quanta of 150 ms)
| Level | AI + | RT normal ghosts | Fright T / R | Warning T / R | Fruit | Points |
|---|---|---|---|---|---|---|
| 1 | 0 | 8/10 | 20 / 40 (6.0 s) | 5 / 10 | C cherry | 100 |
| 2 | 0 | 8/10 | 17 / 34 (5.1 s) | 5 / 10 | S strawberry | 300 |
| 3 | 1 | 8/10 | 14 / 27 (4.1 s) | 5 / 10 | O orange | 500 |
| 4 | 1 | 9/10 | 10 / 20 (3.0 s) | 4 / 7 | O orange | 500 |
| 5 | 2 | 9/10 | 7 / 13 (2.0 s) | 3 / 7 | A apple | 700 |
| 6 | 2 | 9/10 | 17 / 34 (5.1 s) | 5 / 10 | A apple | 700 |
| 7 | 2 | 9/10 | 7 / 13 | 3 / 7 | M melon | 1000 |
| 8 | 2 | 9/10 | 7 / 13 | 3 / 7 | M melon | 1000 |
| 9 | 2 | 9/10 | 4 / 7 (1.05 s) | 2 / 3 | G galaxian | 2000 |
| 10 | 2 | 9/10 | 17 / 34 | 5 / 10 | G galaxian | 2000 |
| 11 | 2 | 9/10 | 7 / 13 | 3 / 7 | B bell | 3000 |
| 12 | 2 | 9/10 | 4 / 7 | 2 / 3 | B bell | 3000 |
| 13-99 | 2 | 9/10 | 4 / 7 | 2 / 3 | K key | 5000 |
Shape after the arcade (fright shrinking with bumps at 6 and 10, the arcade fruit list and values), scaled to the GP1
units. Row 1 is exactly GP1 (fright 20/40, warning 5/10, 4/5 cadence), so a level-1 game differs from GP1 only by
the fruit. Unchanged at every level: eyes wait 10 / 20, frightened cadence (TURN 1 per 2 turns, REALTIME + 2 due at
>= 5), lives rules, ghost count (the config card), seed.
- AI: AI-LEVEL = min(3, ARC-AIB + "AI +"). AI0 stays 0 at every level (D10 controlled mode: ghosts never move). A
  configured AI3 only gets the fright and cadence changes. Switching from AI1 to AI2 stops the seed draws; the
  sequence is still fixed (D14).
- REALTIME normal cadence: accumulator + ARC-KNUM, due at >= 10 (ARCADE only; CLASSIC keeps + 4 / 5). 8/10 gives the
  identical step pattern to GP1's 4/5 (the accumulator is exactly twice the GP1 one), 9/10 = 90 % of the quanta.
  The accumulator resets to 0 at a death and a level clear (ARCADE). TURN ghosts already move every turn (the same rate
  as Pac-Man), so TURN progression is AI + fright + fruit only.
- The row is read at the level start (and at a fright start / ghost eaten for the TURN vs REALTIME column, as in GP1);
  ARC-KWARN, ARC-KNUM, ARC-BV, ARC-BK are copied into PAC-ARC so PACRT and the displays never hold their own copy.

### 4.3 Fruit (one fixed cell, two per level)
- Cell (10,8): an existing `.` corridor cell in the middle of the lower long corridor of ARCADE1, not the player start,
  a ghost home or a power cell (verified). The pellet under it is an ordinary pellet.
- Appears when ARC-ITEMS reaches 30 and again at 70 (the arcade 70 / 170 of 244 scaled to 100 items; 70 < 98, the
  item count with 3 ghosts). ARC-BT = 30 turns / 60 quanta (9.0 s). If the second one appears while the first is still
  shown, the timer restarts (no second fruit object).
- Eaten when Pac-Man is on the cell with a fruit shown at the end of his player step: entering it, or the fruit
  appearing under him (the 30th / 70th item was the pellet of the fruit cell itself). +ARC-BV, ARC-FRUITS + 1, flag F.
  A fruit is not an item: it never counts for PELLETS-LEFT or the level clear.
- Ghosts ignore it (no collision, no blocking); FRIGHTENED / EYES states never change fruit behaviour. A death
  removes a shown fruit in the death reset (it is never carried across the respawn); a level clear removes it too.
  A used threshold is not rearmed by a death (ARC-ITEMS is per level, not per life).
- Unreachable by construction (documented, D12): in TURN the second fruit cannot appear while the first is shown
  (40 items in 30 turns, one item per turn at most); it can in REALTIME (tested, G2RB2). A fruit can never be shown
  during a freeze (a freeze follows only a death or a level clear, both remove it).
- Its timer ticks in ATIK, after the fright and eyes ticks; pause, the pre-start wait and the freeze stop it (GP1 4.3).
- Order inside one player step: eat the item (score, ARC-ITEMS + 1, power pellet / fright) -> fruit appears if a
  threshold is reached (flag A) -> fruit eaten if Pac-Man is on its cell (flag F) -> hit check (GP1 4.4).

### 4.4 Fruit kinds (display only; the value comes from the table)
C cherry, S strawberry, O orange, A apple, M melon, G galaxian, B bell, K key. Text board: `%` for every kind (G is
already a ghost); the kind letter and value are in the ARCADE level line.

### 4.5 Extra life
- One extra life when ARC-SCORE first reaches 10000 (once per game; the arcade default). LIVES + 1, flag X. Any single
  scoring event that takes the score from below 10000 to 10000 or more awards it (a pellet, a power pellet, a ghost,
  a fruit). The EXTRA-LIFE-AWARDED flag ARC-XL makes a second award impossible: nothing at 20000, 30000, ...
- Awarded at the moment the points are added, before any hit of the same check is applied (GP1: eaten ghosts are
  scored before a hit). So a last-life step that eats a frightened ghost across 10000 and is then hit by a normal one
  keeps the game going with 1 life.
- Lives are at most 4 (3 + 1), so `LIVES PIC 9` holds them; see decision 9.2 for the roadmap's "lives widened".

### 4.6 Death detection (needed because of 4.5)
A death and an extra life in one step leave LIVES unchanged, so in ARCADE the "LIVES fell" tests are replaced by
flag D (set by LOSE-LIFE, cleared at the start of every step with the other ARC-EVF flags): PACRT death freeze and
accumulator reset, PACDISP S1 bell. CLASSIC keeps the LIVES comparison byte for byte.

### 4.7 Counters (D13/D14 rule: beyond 99, no silent wrap)
| Counter | Bound | Field |
|---|---|---|
| level | 99 (final level, 4.1) | ARC-LEVEL 999 |
| score | 99 x (96x10 + 4x50 + 4x1400 + 2x5000) = 1659240 | ARC-SCORE 9(7) (unchanged) |
| ghosts eaten | 99 x 12 = 1188 | ARC-EATN4 9(4) (ARC-EATEN mirrors the low 3 digits) |
| fruits eaten | 99 x 2 = 198 | ARC-FRUITS 999 |
| lives | 4 | LIVES 9 (unchanged) |
| turns | as REALTIME quanta (9(7), D33): bounded by the deck / session, documented | ARC-TURNS 9(7) |
TICK-COUNT (PIC 999, PACSTATE) mirrors the low 3 digits of ARC-TURNS in ARCADE; every ARCADE end line uses the wide
field. A start-level game (section 5) starts all totals at 0, so the bounds hold for it too.

### 4.8 Configuration
The config card / PARM configuration (AI, ghosts) is read only before the start, as in 1.0-MVS (a later `A...` card
is an invalid command in TURN and ignored in REALTIME). It sets ARC-AIB; AI-LEVEL is derived from it and the row at
every level start. CLASSIC: unchanged.

## 5. Start level: a supported start / debug option
Start level = PARM columns 22-23: the text from column 22 to the end of the PARM, 1 or 2 digits, value 1-99. Absent,
blank, `0`/`00`, non-digits or more than 2 characters = level 1, following the existing option policy ("anything else
= the default"; nothing is wrapped or clamped). ARCADE only; CLASSIC ignores it. CLIST keyword `LEVEL(n)`, default
`LEVEL(1)`: normal play still starts at level 1. Starting at `LEVEL(10)` initialises a fresh level-10 game (the row
of level 10, its fruit, score 0, 3 lives, no extra life, totals 0): it does not simulate levels 1-9 or grant their
score, fruits or anything else. It is useful for deterministic tests and to play a later difficulty directly.
Without it, rows 3-13, the final-level WON and the counter bounds could only be reached with decks of thousands of
cards; with it every row and the level-99 clear are one short deck each (D12).

## 6. Text output (BAT, TSO line mode, REALTIME batch)
- Header: `RULES ARCADE` then `LEVEL 001` (the start level).
- After the GP1 ARCADE line, one level line (ARCADE only):
  `L LV=001 AI=1 IT=030 BN=1 BT=029 BK=C BV=0100 XL=0 EV=A----`
- Board: `%` = fruit, drawn under Pac-Man and the ghosts.
- End: `SCORE nnnnnnn`, `LIVES`, (`QUANTA`), `TURNS nnnnnnn` (7 digits in ARCADE), `GHOSTS EATEN nnnn`,
  `FRUITS EATEN nnn`, `LEVEL nnn` (last line). GP1 ARCADE end lines change width accordingly.
- CLASSIC output: unchanged.

## 7. Tests (D9, D10, D12)
- Independent model: tests/ref_arcade.py extended from this document (not from the COBOL), TURN and REALTIME.
- CLASSIC regression: test_s1/test_rt/test_gx/test_gs/test_g4 references and the 1.0-MVS oracle byte-identical;
  test_core_frozen PASS after the authorised change. GP1 edge cases (tests/gpcases, RTGP*) rerun = extended model.
- Edge cases, one case each: level clear in TURN and REALTIME (refill, positions, freeze 10 quanta); clear + death
  same step (lives left -> next level; last life -> LOST, level kept); clear by a power pellet as last item; clear
  during a fright and with eyes waiting (all reset); every row 1-13 applied (start level) incl. AI bump with AI0 / AI1
  / AI3 and the 9/10 cadence pattern; level 99 clear = WON; fruit at 30 and 70; second fruit while the first is shown
  (timer restart); fruit expiry exact tick (TURN and REALTIME); fruit appearing under Pac-Man; fruit + death (removed,
  threshold not rearmed); fruit through a pause and a freeze; ghost on the fruit cell; extra life by a pellet, by a
  ghost, by a fruit; extra life + death in one step (flag D drives freeze and bell); no second extra life at 20000;
  1/2/3 ghosts (item counts 100/99/98 vs threshold 70); CFG in ARCADE; PARM columns 22-23 absent / blank / `00` /
  `ab` / `99`; TSO line mode.
- Screens (GP2.3): fruit per profile and scale, level shown, size guard <= 2048 bytes on every ARCADE stream.
- Live (GP2.4): GS 120x27 REALTIME, RULES(ARCADE): fruit appears / eaten / expires, level clear freeze and refill,
  extra life, a start-level game (LEVEL(9)) with the short fright; RULES(CLASSIC) unchanged.

## 8. Screens (GP2.3, outline; made precise in a section 10 like GP1)
Fruit at (10,8) in every profile: unscaled `%` red (CLASSIC / BASE glyphs; GRAPHIC: base `%`, never GE), scaled a
new GS sprite in red; drawn under Pac-Man and the ghosts, no blink. Level: in the wide/tall titles and HUD
(`LEVEL nn`) and, if the 61-column ARCADE status line has no room, only there; the full HUD (level + high score) stays
in RP. Bells (S1, ARCADE): start, death (flag D), level clear (flag C), extra life (flag X), final WON; one bell per
screen as today. No new PACFSIO / PACTSO work.

## 9. Decisions (user, 2026-10-12)
1. Per-level table 4.2 approved (13 rows, levels 13-99 = row 13); AI = configured + bump, at most AI3, AI0 stays AI0
   at every level (the deterministic stationary test mode). Every progression value is in the one level table.
2. Exactly one extra life at 10000 (none at 20000, 30000, ...), awarded when a scoring event crosses the threshold,
   with an explicit EXTRA-LIFE-AWARDED flag (ARC-XL). LIVES stays one digit (max 4); the roadmap item "lives counter
   widened" is closed as not needed. The explicit ARCADE death flag (D) is approved: a death is never inferred from a
   drop in LIVES.
3. Clearing level 99 ends the game WON: an intentional MVS implementation limit, documented as such (4.1).
4. Fruit cell (10,8), 30 / 70 items, 30 turns / 60 quanta, the arcade sequence cherry 100 ... key 5000. Verified
   before coding (2026-10-12): (10,8) is an existing `.` corridor cell of ARCADE1, open to the left, right and down,
   reachable from the start (all 102 open cells connected), not the player start (2,2), a ghost home (19,9) (2,9)
   (19,2) or a power cell; the topology is unchanged. Per-level thresholds, pause freezes the timer, a death removes
   the fruit, a level clear clears it, FRIGHTENED / EYES never alter it.
5. `LEVEL(n)` approved as a real option (section 5); normal play starts at `LEVEL(1)`.
6. REALTIME level-clear freeze 10 quanta = 1.5 s on the existing freeze (no deadline catch-up: the absolute-deadline
   loop of D33 is unchanged); extra-life bell YES (GP2.3). No special level-clear alarm pattern (S2 if ever).
GP1 compatibility: ARCADE GP1 reference output evolves under GP2 (not byte-identical); every GP1 invariant is rerun
against the extended model; RULES(CLASSIC) and the 1.0-MVS oracle stay byte / behaviour identical; structural safety
checks are never disabled by `PACMAN_LATER_PHASE` (it skips only source-equality pins of an earlier phase).

## 10. GP2.2 result (2026-10-12): COMPLETE (core + text + model + deck); GP2.3 (screens) not started
- Core (authorised, docs/CORE_CHANGES.md 2026-10-12): PACGAME (K-LVL table, LEVEL-ROW / LEVEL-START / LEVEL-CLEAR,
  ARC-LOSE, XLIFE, FRUIT-SPAWN / FRUIT-EAT, ARC-TICKS, fruit timer in ATIK), PACARC (appended fields). PACMAP, PACAI,
  PACSTATE, PACMREQ, LEVEL1, ARCADE1 unchanged. Driver / text: PACRT (level step ARC-KNUM of 10, freeze on flags D / C,
  CLASSIC 4/5 and LIVES test unchanged), PACMAIN (PARM columns 22-23 -> REQ-START), PACDISP (LEVEL header, L line,
  `%`, wide end lines), PACREQ +REQ-START, CLIST `LEVEL(1)` (source only; installed with GP2.3). Screen side
  (PACSCR, PACPAL, PACDS), input and platform untouched: ARCADE screens do not show the fruit or the level yet.
- Model tests/ref_gp2.py (extends the frozen GP1 model tests/ref_arcade.py); cases tests/gp2cases from
  tests/search_gp2.py (12 searched TURN edges, 2 REALTIME, 4 constructed: G2CLR = the WIN0 route, G2RCLR, G2ROW,
  G2RPAU).
- Deck `GP2` (job PACBLGP2): `python3 tools/make_deck.py GP2 && python3 tools/run_deck.py build/GP2.jcl`, then
  `python3 tests/test_gp2.py build/PACBLGP2-<n>.txt`. COMPRESS JOB 242; JOB 243 first build 236 steps RC 0000 (70/71
  runs = model, G2RPAU card file rebuilt afterwards); JOB 244 run of record: 236 steps RC 0000, no warnings, S1 /
  CLASSIC regression PASS (1.0-MVS oracle), 71 ARCADE runs = model (52640 lines), 2 CLASSIC runs with columns 21-23 =
  oracle / RT model. Evidence: docs/evidence/gp2-build-text.txt.
- tests/test_gp1.py now honours PACMAN_LATER_PHASE (skips only its source pins and the GP1 constants-row parse) and
  runs inside test_gp2.py as a regression of its structural guards and the frozen GP1 model.

## 11. GP2.3 screens (2026-10-12): display rules as built (display only; the game state is never changed)
- Fruit: `%` at (10,8) while ARC-BT > 0, green (X'F4', the one colour no board actor uses), no blink, base set in
  every glyph profile (CLASSIC, BASE, GRAPHIC: never GE); scaled 4x2 / 3x2: sprite 8 (`BFFB`/` TT ` and `BFB`/` T `:
  lower halves, full reversed cells, upper halves). Drawing order: map -> fruit -> eyes -> Pac-Man -> ghosts, so an
  actor or EYES on the cell hides the fruit, never the reverse, and the fruit is drawn again when the actor leaves while
  the timer runs (G2BGHX). Its appearance / disappearance (timer end, eaten, death, level clear) is an ordinary image
  change: partial redraw sends only the changed cells; pause and the freeze send nothing new for it (the timer stops).
- Level: the ARCADE status line (80x24 G1-G4, GS layout B, tall) becomes
  `T001 R CLEARED S=0001234 L=099 V=3 ST=RUNNING FR=017 LV=01 C` (61 columns: PW dropped - the board shows the `o` -
  then the level and the fruit kind letter). Wide HUD (right column): `LEVEL   nn` and the level's fruit name + points
  (`STRAWBERRY 0300`, fruit colour). Tall: `LEVEL nn` in the title row (column +60), the fruit name + points on the
  score line after the lives (column +55).
- Level transition: no new sequence (READY / intermission belong to RP). The screen of the clearing step shows the
  refilled maze, Pac-Man and the ghosts at their start cells, `CLEARED` (status / wide LAST) and the new level; in
  REALTIME it stays on screen through the existing 10-quantum freeze (normal scheduling, no catch-up).
- Score / lives: 7-digit ARC-SCORE as in GP1.3; lives icons follow LIVES (at most 4, the extra life adds an icon).
- Alarm (S1, one ordinary WCC alarm, no S2 pattern): in ARCADE the screen rings at the start, after a death
  (ARC-NDIE rose), the extra life (ARC-XL 0 -> 1), a level clear (ARC-LEVEL rose, the approved D37 section 8 event) and
  the final WIN. Events on one screen are coalesced into the one alarm of that write (e.g. extra life + death in one
  step, G2XD / G2RXD; clear + death, G2CLRD): no extra host write is made for a second bell. CLASSIC keeps the S1
  LIVES rule byte for byte (it is now guarded by ARC-ON = 0; ARCADE never infers a death from LIVES).
- Changed: PACPAL (append-only: PAL-FRUIT, GLY-FRUIT, SPR-4Y, SPR-3Y, fruit names), PACSCR (fruit overlay, sprite 8,
  status variant, wide / tall HUD), PACDISP (ARC-BELL). Core, PACMAIN, PACRT, PACREQ, input and platform unchanged
  since GP2.2 (93a4811). Models: ref_g2/g4/gs/gx_screen GP2 branches (they key on the game's `level` / `bt`), the
  ref_snap hook takes a game's own snapshot (GP2: lives, won, deaths, extra life, level).
- Deck `GP23` (build + 43 TSD runs: the 21 GP1.3 runs on the GP2 model and 22 GP2 runs; the GP2 deck is at 236 of the
  255 JES steps, so the screens are a separate job on the same sources and the GP2 deck is rerun for the text /
  CLASSIC / S1 regression): `python3 tests/test_gp2.py build/PACBLGP2-<n>.txt build/PACBLG23-<n>.txt`.
- User decisions (2026-10-12, GP2.3 approved as implemented): (1) the level-clear alarm stays (D37 section 8): one
  ordinary S1 alarm, coalesced with any other alarm event of the same write; (2) the 80x24 compact HUD is an
  intentional compact-layout tradeoff: the 61-column status line keeps LEVEL and the fruit kind letter, PW= is dropped
  and the fruit points do not fit; the larger layouts (wide, tall) keep the full fruit name and points.

## 12. GP2.4 result (2026-10-12): live PASS - MVS-GP2 COMPLETE (tag mvs-gp2)
Three scripted scenarios (tests/gp2live LIVEA/B/C from G2RCLR, G2XF, G2RXD; tools/gp2_live.py; checklist
docs/evidence/gp2-live-checklist.md) played in c3270 at 120x27 and replayed from the trace by tools/c3270_gp2_trace.py:
A 203/203, B 78/78, C 149/149 host writes = the model; alarms A [0, 184], B [0, 76], C [0, 44, 113, 145]; freezes
1.49-1.51 s; pause and PA2 with the fruit shown change nothing; QUIT -> READY. Run 1 found a test-driver defect only
(c3270 Wait(Output) does not block without an AID; fixed by sending the ignored PF1 on idle quanta); B was accepted
from run 1, A and C from run 2. Evidence: docs/evidence/gp2-live.md.

# MVS-GP1: power pellets under RULES(ARCADE) - design (D36, APPROVED 2026-10-11)
Source: docs/ROADMAP-POST-RT.md (approved order, "Design corrections fixed before GP1"). No probe is needed: every
capability used here is already proven (GE/CP310 E9, highlight/blink G2, scaled sprites E11, REALTIME E14).

## 0. Steps
| Step | Content | Exit |
|---|---|---|
| GP1.1 | this design | user approval -> D36 frozen in DECISIONS.md, core change authorised |
| GP1.2 | core + text: PACGAME/PACMAP/PACAI, new copybook PACARC, PACRT, PACMAIN, PACDISP text lines, CLIST | deck `GP1`, tests/test_gp1.py: CLASSIC = every earlier reference byte for byte; ARCADE batch TURN + REALTIME + TSO line = independent model |
| GP1.3 | screens: PACSCR/PACPAL for CLASSIC/BASE/GRAPHIC glyphs, SCALE 4/3, all GX layouts | ARCADE TSD dry runs = screen models; CLASSIC TSD streams unchanged |
| GP1.4 | live c3270 checklist | evidence docs/evidence/gp1-live.md, README, tag `mvs-gp1` |

## 1. Rule set switch
- `RULES(CLASSIC|ARCADE)`: PARM column 21, `A` = ARCADE, anything else / absent = CLASSIC (so every existing PARM and
  every reference stays CLASSIC). PACREQ gains `REQ-RULES PIC X` (append-only). CLIST keyword `RULES`, default
  `CLASSIC` during GP1 (roadmap decision 2; the default flips to ARCADE only in G8).
- CLASSIC = 1.0-MVS byte for byte: the ARCADE code paths are entered only when `ARC-ON = 1`.

## 2. ARCADE state: new copybook PACARC (own 01, D16), PACSTATE unchanged
```
01  PAC-ARC.
    05  ARC-ON       PIC 9.       1 = ARCADE (set by PACGAME RSET from REQ-RULES)
    05  ARC-SCORE    PIC 9(7).    ARCADE score (SCORE keeps its low 4 digits, see 4.6)
    05  ARC-POWER    PIC 9.       power pellets left (4 at INIT)
    05  ARC-FR       PIC 999.     fright ticks left (0 = no fright)
    05  ARC-FTURN    PIC 999.     ticks since the fright started (TURN cadence)
    05  ARC-FACC     PIC 9.       frightened-ghost accumulator (REALTIME cadence)
    05  ARC-CHAIN    PIC 9.       ghosts eaten in this fright (0-4)
    05  ARC-EATEN    PIC 999.     ghosts eaten in the game (counter beyond 99)
    05  ARC-MOVEN    PIC 9.       this step moves normal ghosts (0/1)
    05  ARC-MOVEF    PIC 9.       this step moves frightened ghosts (0/1)
    05  ARC-EVT      PIC X(4).    last event: POWR / GHST / blank (display only)
    05  ARC-PTS      PIC 9(4).    points of the last ghost eaten (display only)
    05  ARC-KWARN    PIC 999.     warning window of the running fright (from the constants table)
    05  ARC-KFINC    PIC 9.       REALTIME frightened accumulator increment (from the constants table)
    05  ARC-GH       OCCURS 3 TIMES.
        10  ARC-GM   PIC X.       N normal, F frightened, E eyes (at home)
        10  ARC-GW   PIC 999.     eyes wait left
        10  ARC-GR   PIC 9.       1 = reversal pending (fright start)
```
PACMAIN owns it and appends it to the USING list of PACGAME, PACAI, PACRT, PACDISP and PACSCR (every call site, also in
CLASSIC). PACMAP, PACINPT, PACPLAT, PACQRY, PACFSIO and PACTSO do not see it.

## 3. Core changes (authorised-core-change procedure, tools/core_baseline.py --authorize)
- PACMAP: new op `LDA ` = LOAD + four `o` cells at (2,4), (19,4), (2,8), (19,8) (none is the player start or a ghost
  home); `EAT` sets `M-FLAG = 2` on `o` (blanks it); `CNT` counts `.` and `o`. CLASSIC never has an `o` in the map,
  so EAT/CNT behave exactly as in 1.0-MVS. maps/LEVEL1.txt unchanged; maps/ARCADE1.txt documents the ARCADE layout.
- PACGAME: RSET also resets PAC-ARC; INIT uses `LDA ` when ARC-ON; new op `ATIK` (one fright tick, 4.3); DO-MOVE and
  CHECK-HIT get an ARCADE branch (4.1-4.4). The CLASSIC paragraphs are not changed.
- PACAI: ghosts selected by mode and ARC-MOVEN/ARC-MOVEF; frightened movement (4.2). CLASSIC loop unchanged.
- PACSTATE and PACMREQ unchanged.

## 3a. Constants (one place: the PACGAME table K-ARC, row T = TURN, row R = REALTIME)
| Constant | TURN (turns) | REALTIME (quanta) |
|---|---|---|
| fright length | 20 | 40 = 6.0 s |
| warning window (final part of the fright) | 5 | 10 = 1.5 s |
| eyes wait at home | 10 | 20 = 3.0 s |
| frightened cadence | 1 move every 2 Pac-Man turns | accumulator + 2, due at >= 5 (2/5 of the quanta) |
The row is chosen by REQ-PLAY when the value is used (fright start, ghost eaten); PACGAME copies the warning window
and the REALTIME increment into PAC-ARC (ARC-KWARN, ARC-KFINC) so PACRT and the displays never hold their own copy.
GP2 replaces the single row per mode by a per-level table without touching the GP1 logic. If a lost TSC session turns
a REALTIME game into TURN (D33), counts already running are kept and later frights use the TURN row.

## 4. Rules (ARCADE)
### 4.1 Items and score
96 pellets `.` (10 points) + 4 power pellets `o` (50 points) = PELLETS-LEFT 100 with 1 ghost; ghost homes are
cleared as today (one fewer item per extra ghost). Clearing every `.` and `o` = WON. Eaten ghost: 200, 400, 800, 1600
by ARC-CHAIN (the 4th value exists for completeness; 3 ghosts reach 800). GP1 maximum = 96x10 + 4x50 + 4x(200+400+800)
= 6760.

### 4.2 Fright
- Eating `o`: +50, ARC-FR = fright length (TURN 20 turns, REALTIME 40 quanta = 6.0 s), ARC-FTURN 0, ARC-FACC 0,
  ARC-CHAIN 0. Every ghost not in eyes becomes F with a pending reversal (a ghost already F gets it again).
- Eating another `o` during a fright **restarts** the fright (the timer is set to the full length again, nothing is
  added to what was left) and **resets the 200/400/800/1600 chain** to 200.
- Eyes (returning) ghosts are never affected by a new power pellet: they stay eyes and keep their wait.
- Frightened move (all AI levels 1-3 alike, no use of the seed): if the reversal is pending and the reverse cell is
  open, step there; otherwise candidates = open directions except the reverse of the current one (the reverse only
  in a dead end); pick the one that **maximises** the Manhattan distance to Pac-Man, first maximum in U,D,L,R order
  (D14). AI0 ghosts never move, frightened or not (they can still be eaten).
- Cadence (roadmap correction). TURN and REALTIME are two different discrete scheduling rules, documented exactly
  (neither is called "half speed"):
  - TURN: normal ghosts every Pac-Man turn; frightened ghosts 1 move every 2 Pac-Man turns, on the turns where
    ARC-FTURN is even and > 0 (turns 2, 4, 6 after the eat) = 50 % of the Pac-Man turn rate.
  - REALTIME: Pac-Man may step every quantum; normal ghosts on the existing accumulator (ACC + 4, due at >= 5, untouched
    by the fright) = 4/5 of the quanta; frightened ghosts on ARC-FACC + 2, due at >= 5 = 2/5 of the quanta = 40 % of
    the Pac-Man quantum rate (half of the normal-ghost rate). ARC-FACC = 0 when a fright starts and when it ends, so
    the step pattern is the same in every run. A step with ghosts is due when either accumulator is due;
    ARC-MOVEN/ARC-MOVEF tell PACAI which ones move.
- In the step where a fright starts (or restarts) no frightened ghost moves (ARC-MOVEF = 0 at the eat); the
  reversal is taken on its next frightened move.
- LEVEL1 has no dead ends (tests/test_mvs8.py), so the "reverse only when nothing else is open" flee rule cannot fire
  on this map (as D13 for AI2/AI3); a pending reversal blocked by a wall (a ghost frightened at its home, facing its
  start direction) is reachable and tested (GPREVB).
- Fright end: when ARC-FR reaches 0 every F ghost becomes N (direction kept, pending reversal cleared), chain 0.
- Warning window (display only): ARC-FR <= 5 turns / 10 quanta.

### 4.3 Tick order
- One fright tick (`ATIK`): ARC-FR - 1 (fright end at 0), ARC-FTURN + 1 while the fright lasts, every eyes wait - 1;
  a wait reaching 0 revives the ghost as N at its home with its home direction, unless Pac-Man stands on the home
  cell: then the wait stays 1 (retry next tick). A revived ghost is NORMAL (lethal) even when a fright is running;
  since the tick comes first, it may take its normal step in that same turn / quantum.
- TURN: every MOVE (blocked moves too; invalid commands are not turns) = ATIK, player move + eat, hit check, ghost
  move, hit check (the 1.0-MVS order).
- REALTIME: every running quantum (started, not paused, not frozen) = ATIK first, then the cadence and the P/G/B step
  as in D33. A death still freezes 10 quanta; no ticks while frozen or paused.
- Pause (and the pre-start wait) freezes every GP1 timer and counter: fright, warning, eyes waits, ARC-FTURN, both
  accumulators. Invalid commands, PA2 redraws and visual ticks are not ticks either.

### 4.4 Collisions (both hit checks, same cell only; swaps are not hits, as in 1.0-MVS)
This ordering is authoritative for every simultaneous edge case.
Ghosts on Pac-Man's cell in index order: E = nothing (eyes are never lethal); F = eaten (points by chain, chain + 1, ARC-EATEN + 1, the ghost
goes to its home at once as E with wait TURN 10 turns / REALTIME 20 quanta, pending reversal cleared); N = hit.
Eaten ghosts are scored before a hit is applied. A hit costs a life as today; it also ends any fright and every eyes
wait deterministically (all ghosts reset to N at their homes with their home directions, pending reversals 0,
ARC-FR/ARC-FTURN/ARC-FACC/ARC-CHAIN 0, eyes waits 0; in ARCADE PACRT also resets its normal-ghost
accumulator to 0 at the death, which CLASSIC REALTIME does not do and keeps not doing); points already scored, power pellets eaten and ARC-EATEN stay. Pac-Man eating
`o` onto a cell holding a ghost: the eat comes first, so that ghost is frightened and eaten. Last item + hit in one
tick keeps the 1.0-MVS rule (WON after the life is lost, LOST at 0 lives).

### 4.5 What stays as in 1.0-MVS
Maze, start cells, ghost homes, lives (3), AI0-AI3, seed 12345 (AI1 random draws happen only for N ghosts), TURN
counting, REALTIME T/TTL/freeze/pause, no ghost house, no pathfinding for eyes.

### 4.6 SCORE in ARCADE
Points go to ARC-SCORE; SCORE (PIC 9(4), PACSTATE) mirrors its low 4 digits so any display reading SCORE stays sane.
Every ARCADE display shows ARC-SCORE with 7 digits.

## 5. Text output (BAT, TSO line mode, REALTIME batch)
- Header: the usual banner, then `RULES ARCADE` (ARCADE only).
- After each status line (TURN) / RT line + ghosts line (REALTIME), one ARCADE line:
  `A S=0001234 PW=3 FR=017 FT=003 CH=1 EV=GHST P=0200 GM=F,E,N W=000,010,000`
- Board text: `o` power pellet, ghosts `G` normal, `F` frightened, `E` eyes.
- End: `SCORE 0001234` (7 digits) in place of `SCORE nnnn`; `GHOSTS EATEN 001` is the last end line (after `LIVES`
  and, in REALTIME, `QUANTA`).
- CLASSIC output: unchanged.

## 6. Screens (GP1.3)
| Profile | Power pellet | Frightened ghost | Warning window | Eyes |
|---|---|---|---|---|
| CLASSIC glyphs | `o` white | `G` blue | `G` white | `"` white |
| BASE | `o` white | its frames, blue | white | `"` white |
| GRAPHIC | `o` white (base set; CP310 `○` is the Pac-Man shut frame) | `∩`/`⍝` blue | white | `"` white |
| SCALE 4 / 3 | reserved GS sprite ` ▄▄ ` / ` ▀▀ ` white | ghost sprite blue, eyes `°°` without reverse | white body | only the `°°` eyes, white |
Power pellets blink (highlight X'F1') when highlighting is on. Score: 7 digits in every layout (80x24 text rows,
GS layout B, GX wide/tall HUD); the title shows `ARCADE`. Values only in PACPAL; size guard (<= 2048 bytes) asserted on
every ARCADE stream. Sound unchanged (S1 events; no new bells in GP1).

## 7. Tests (D9, D10, D12)
- Independent model tests/ref_arcade.py (rules from this document, not from the COBOL), TURN and REALTIME.
- CLASSIC regression: every reference stream of test_s1/test_rt/test_gx/test_gs/test_g4 and the 1.0-MVS oracle
  byte-identical; test_core_frozen PASS after the authorised change (and fails on any unauthorised one).
- Edge cases, one case each: `o` eaten with no ghost near; second `o` during a fright (restart, chain reset, ghost
  already F reverses again); fright end in TURN and REALTIME (exact tick); frightened ghost walks into Pac-Man (eaten);
  Pac-Man walks into it; two F ghosts on one cell (200 + 400); F + N on one cell (eaten, then the life lost); eaten
  ghost whose home is Pac-Man's cell (revival waits); revival during the fright (revived ghost is N and dangerous); eyes
  harmless; death during fright and during eyes (full reset); last item = `o`; last item + hit; reversal blocked by a
  wall; dead-end flee; AI0 frightened (still, eaten); AI1 seed sequence; 1/2/3 ghosts; REALTIME half cadence (2/5) and
  normal cadence (4/5) in one fright; pause and freeze stop the fright; TSO line mode; PARM column 21 absent/blank/`A`.
- Screens: ARCADE TSD runs per profile (full/partial, anim, hilite, scale 4/3, layouts) = models; size guard.
- Live (GP1.4): RULES(ARCADE) at the GS 120x27 REALTIME profile: power pellet blink, fright and flee, warning, eat a
  ghost (score), eyes at home and revival, death during fright, end screens; RULES(CLASSIC) unchanged.

## 8. Decisions (user, 2026-10-11)
1. Power pellet cells (2,4), (19,4), (2,8), (19,8): approved; verified as existing `.` corridor cells of LEVEL1, none a
   ghost home or the player start; the maze topology is unchanged.
2. Fright 20 turns / 40 quanta, warning 5 / 10, eyes wait 10 / 20: approved; constants centralised (3a).
3. Separate PACARC copybook passed explicitly: approved; PACSTATE untouched, no CLASSIC field overlaid or repurposed
   (SCORE only mirrors the low 4 digits of ARC-SCORE for any reader of SCORE, 4.6).
4. Wording: REALTIME frightened cadence is 2/5 of the quanta (40 % of Pac-Man), TURN is 1 move per 2 Pac-Man turns;
   they are different discrete rules. No GP2 behaviour in GP1. GP1.3 starts only when GP1.2 (core/text model and
   CLASSIC regressions) is green.

## 9. GP1.2 result (2026-10-11): COMPLETE
- Core (authorised, docs/CORE_CHANGES.md): PACMAP LDA/EAT/CNT, PACGAME ATIK + ARCADE branches + table K-ARC, PACAI
  flee/cadence, copybook PACARC, maps/ARCADE1.txt (both added to the frozen set). Driver/text: PACMAIN (PARM column
  21, PAC-ARC on every PACGAME/PACRT/PACDISP call), PACRT (ATIK, ARC-FACC, ACC reset at a death), PACDISP (ARCADE
  lines), PACREQ +REQ-RULES, CLIST `RULES(CLASSIC)` (source only; installed with GP1.3). Screen side untouched.
- Model tests/ref_arcade.py; edge-case search tests/search_gp1.py -> tests/gpcases (12 searched + GPAI0, GPHOME
  scripted, RTGPA/RTGPD searched, RTGPP = RTGPA with a pause in the fright, GPTSO = GPHOME with a TSO redraw).
- Deck `GP1` (job PACBLGP1): `python3 tools/make_deck.py GP1 && python3 tools/run_deck.py build/GP1.jcl`, then
  `python3 tests/test_gp1.py build/PACBLGP1-<n>.txt`. JOB 238 (after COMPRESS JOB 237): 192 steps RC 0000, no
  warnings, S1 regression PASS (CLASSIC byte-identical, 1.0-MVS oracle), 26 ARCADE runs = model (11363 lines), 3
  column-21 CLASSIC runs = oracle/model. Evidence: docs/evidence/gp1-build-text.txt.
- Earlier phase tests pin their own sources to their tags; they run as regressions with `PACMAN_LATER_PHASE` set
  (test_rt, test_s1), the listing/behaviour checks unchanged.

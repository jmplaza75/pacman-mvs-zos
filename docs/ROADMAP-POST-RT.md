# Post-RT roadmap: gameplay, polish and final release (APPROVED with amendments, 2026-10-11)
Status: roadmap approved by the user on 2026-10-11 (decisions below). Phases still start one at a time, on the user's go.
MVS-S1 COMPLETE (tag mvs-s1, 2026-10-11). MVS-GP1 COMPLETE (tag mvs-gp1, 2026-10-12). MVS-GP2 COMPLETE (tag mvs-gp2, 2026-10-12). MVS-HS COMPLETE (tag mvs-hs, 2026-10-12, D38, docs/HS-HISCORE.md). MVS-RP COMPLETE (tag mvs-rp, 2026-10-13, D39 + D40, docs/RP-POLISH.md; SPEED(NORMAL|FAST) 150 / 125 ms). Next on
the order below: MVS-S2 (in progress since 2026-10-13; D41 frozen, docs/S2-PATTERNS.md).

## Where the project stands
- Mechanics: 1.0-MVS core (frozen, tests/core_baseline.json): 20x10 maze, 100 pellets x 10 points, 3 lives, 1-3 ghosts,
  AI0-AI3 deterministic (seed 12345). No power pellets, frightened ghosts, fruit, levels or high score.
  `SCORE PIC 9(4)` and `LIVES PIC 9` are too small for arcade scoring (D13-D14 rule: counters beyond 99).
- Presentation: GS 4x2 scaled renderer (80x20 maze), 120x27 IBM-DYNAMIC canvas, REALTIME at T = 150 ms (CLIST default).
- Closed negative: G5 Programmed Symbols (D30), G6 blocked.
- Loose ends: the ESTAE abend-restore exit in PACFSIO is not validated live (since G1). Long pauses and pre-start waits
  are not soak-tested (RT). The maze cannot grow at 4x2: 120x27 holds at most a 30x12 logical grid.

## User decisions (2026-10-11)
1. Gameplay scope: YES. GP1 and GP2 may change the frozen core under `RULES(ARCADE)`, through the authorised-core-change
   procedure (`tools/core_baseline.py --authorize`, docs/CORE_CHANGES.md). `RULES(CLASSIC)` stays byte and behaviour
   compatible with 1.0-MVS; the oracle and all reference outputs stay unchanged.
2. Default rule set: after GP1 and GP2 are complete and live-validated, the CLIST defaults to `RULES(ARCADE)` (as D34 did
   for REALTIME). `RULES(CLASSIC)` stays the explicit historical/compatibility mode. The default does not change during
   GP1 development.
3. `2.0-MVS-MAX` is the final MVS release. Any z/OS work is a separate roadmap.
4. Persistent high score on MVS disk: IN, before 2.0. Mac/client PCM companion audio: optional, after 2.0, never blocks
   the MVS release.

## Rule for gameplay work: opt-in rule set
All new gameplay goes behind `RULES(CLASSIC|ARCADE)` (next free PARM column). CLASSIC = 1.0-MVS, byte for byte: batch
SYSOUT, the oracle, TURN and RT reference streams stay identical (D16-D18). ARCADE gets its own state block (appended copy
member with its own 01, D16), its own counters, its own SYSOUT lines and its own independent Python model (D9-D10).

## Approved order
`S1 -> GP1 -> GP2 -> HS -> RP -> S2 -> G7 -> G8 / 2.0-MVS-MAX`, then optional S3/S4 after the release.

| # | Phase | Content | Size |
|---|---|---|---|
| 1 | MVS-S1 alarm | Probe E15: is the 3270 WCC alarm audible through the live c3270 path (full and partial writes)? Evidence in docs/evidence/. Only if it is: `SOUND(AUTO\|YES\|NO)`, bell on start, death and end of game. Renderer side only; no client audio. | S |
| 2 | MVS-GP1 power pellets | ARCADE: 4 power pellets (`o`, 50 pts), frightened ghosts, eaten ghosts 200/400/800/1600 and return home (design below), 7-digit score. | L |
| 3 | MVS-GP2 progression | ARCADE: level counter, maze refill on clearing it, per-level table (ghost cadence, AI level, fright time), extra life at 10000, fixed-position bonus fruit per level. Lives counter widened. | M |
| 4 | MVS-HS high score | Top ARCADE score kept in `HERC01.PACMAN.DATA(HISCORE)` through PACPLAT (read at start, rewritten when beaten). GAME never sees the file. A missing or bad member means 0, never a failure. Batch tests use a test member. | S |
| 5 | MVS-RP polish | READY!/GAME OVER screens, death animation (visual only), score popup on an eaten ghost, HUD level and high score, narrow `SPEED` option (below), live ESTAE validation (forced abend in a test build), one soak test of a 10-minute pause. | M |
| 6 | MVS-S2 alarm patterns | Timed alarm sequences, only if the S1 evidence shows separate bells are not merged. May close negative on the S1 evidence alone. | S |
| 7 | MVS-G7 host graphics | Paper phase: the E5 Query Reply announces no graphics codes, x3270 documents none, and TK4- has no GDDM. Close negative with that evidence plus one check for a GDDM load library. | XS |
| 8 | MVS-G8 / 2.0-MVS-MAX | Final capability matrix, CLIST default `RULES(ARCADE)` + best profile (GS, REALTIME, SOUND if S1 passes), benchmarks (bytes/frame, frame jitter), screenshots, README "what runs on MVS vs the client", rebuild from empty libraries under a new prefix, tag `2.0-mvs-max`. Final MVS release. | M |
| - | S3/S4 companion audio | Optional, after 2.0: a Mac-side listener on the c3270 trace that plays PCM on game events, labelled as a client extension (requirements sec. 27). | M |

Not proposed: a larger maze (does not fit at 4x2 on any validated canvas), a branch for an emulator that supports Programmed Symbols (D30 option),
anything ZOS-* / Zowe.

## Design corrections fixed before GP1 (to be frozen as a D-number in GP1)
- Score: ARCADE score is at least 7 digits (`PIC 9(7)`), in the ARCADE state block; CLASSIC keeps `SCORE PIC 9(4)`.
- Frightened cadence: the existing 4/5 ghost accumulator (ACC + 4, due at >= 5) is not "half speed". The exact rates:
  - REALTIME: normal ghosts 4/5 of the quanta; frightened ghosts 2/5 (same accumulator, increment 2 instead of 4,
    due at >= 5), which is exactly half the normal ghost rate. The accumulator is reset to 0 when fright starts and when it
    ends, so the step pattern is the same in every run.
  - TURN: normal ghosts move every turn; frightened ghosts move on every second fright turn (fright turn counter 2, 4,
    6, ...), exactly half.
  - Frightened movement: reverse once when fright starts, then flee deterministically (step that maximises the Manhattan
    distance from Pac-Man, tie order U,D,L,R, D14). Fright length is a fixed count of quanta (REALTIME) or turns (TURN),
    set in the GP1 design.
- Return home of an eaten ghost (no ghost house; the 20x10 maze has none and none is added): each ghost already has a
  home, its start cell in PACGAME GS-DATA (corners 19,9 / 2,9 / 19,2), used today by RESET-GHOST after a death. An eaten
  ghost is moved to its home cell at once (no pathfinding, no "eyes" travelling through the maze), stops being frightened
  and waits there for a fixed delay (quanta or turns, set in GP1) as eyes: harmless, no move, no collision. When the
  delay ends it revives as a normal ghost; if Pac-Man stands on the home cell then, the revival waits one more step
  (deterministic, no instant hit). A death during the delay resets every ghost as today.
- SPEED (RP): narrow scope. At most `SPEED(NORMAL|FAST)` = T 150 / 125 ms on the existing absolute-deadline loop, accepted
  with one live capture analysed by tools/c3270_rt_game.py (median and p95 frame gap, keyboard restore). The broad E14
  timing research is not reopened.

## Acceptance pattern per phase (unchanged)
Probe first when a capability is unproven, then design (D-number), build on Hercules with tools/validate_source.py,
deterministic tests against an independent model, live c3270 checklist, evidence in docs/evidence/, README and
CURRENT_PHASE updated, tag. Regression kept: test_rt, test_gx, test_gs, test_g4, test_core_frozen, 1.0-MVS oracle.

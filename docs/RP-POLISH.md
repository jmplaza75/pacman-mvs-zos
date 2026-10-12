# MVS-RP: presentation and gameplay polish - design (D39, APPROVED 2026-10-12)
Source: docs/ROADMAP-POST-RT.md row 5 ("READY!/GAME OVER screens, death animation (visual only), score popup on an
eaten ghost, HUD level and high score, narrow `SPEED` option, live ESTAE validation (forced abend in a test build), one
soak test of a 10-minute pause") and the items GP2 / HS deferred to RP (READY / intermission, HUD high score).
Rule of the phase: **display, platform and test work only.** GAME / MAP / AI / PACARC are not touched: no authorised
core change, tests/core_baseline.json unchanged. Batch and TSO line-mode SYSOUT stay byte-identical for every rule set
(CLASSIC, ARCADE), so every text reference (1.0-MVS oracle, ref_arcade, ref_gp2, ref_hs, ref_rt) is unchanged.

## 0. Steps
| Step | Content | Exit |
|---|---|---|
| RP.0 | ESTAE live validation (section 7) - independent of the rest, done first | docs/evidence/rp-estae-live.md |
| RP.1 | this design | user approval, D39 frozen |
| RP.2 | PACRT (publish freeze count + death cell), PACREQ (appended), PACSCR/PACPAL/PACDISP (sections 2-5), models | deck `RP` (TSD runs = model), regression decks GP2/GP23/HS rerun |
| RP.3 | `SPEED(NORMAL\|FAST)` (section 6): PARM column 24, PACPLAT period, CLIST | deck `RP` + CLIST job; live capture analysed |
| RP.4 | live c3270 checklist + the 10-minute pause soak (section 8) | docs/evidence/rp-live.md, README, CURRENT_PHASE, tag `mvs-rp` |

## 1. Scope rule (proposed D39.1)
- READY!, death animation, level-clear flash, score popups, end screen and HUD high score are **RULES(ARCADE) only**.
  CLASSIC screens stay byte-identical to their GS/RT/S1 reference streams (test_gs, test_gx, test_rt, test_s1 unchanged).
- Full-screen colour modes only (TSC and its TSD dry run). BAT, TSO line mode and REALTIME batch: nothing changes.
- Timed effects (death animation, flash, popup lifetime) exist in REALTIME only, driven by quanta that already exist
  (the 10-quantum freeze, ordinary quanta). No extra host write, no new wait inside the game loop, no change to game
  timing: every effect is a different drawing of a frame that is sent anyway. TURN gets the static parts only
  (READY!, popup on the screen of the eating turn, end screen, HUD).
- Every RP frame obeys the existing size guard (DS-LIMIT 2048). New rule: an RP decoration that would make a stream
  exceed the limit is **dropped for that frame** (the plain frame is sent); it never triggers the G4 fallback.
- `SPEED` (section 6) is a platform option for any REALTIME game, CLASSIC included (opt-in, default NORMAL = today).

## 2. READY!
- When: REALTIME before the first direction (REQ-RTSTAT `WAIT`), and during the last 4 quanta of a death or
  level-clear freeze (after the animation / flash, with the reset positions already drawn). TURN: the first screen
  (no move yet) and the screen after a death or a level clear.
- Where: `READY!` in the player colour (PAL-PLAYER) over the solid central wall bar of ARCADE1, row y = 4, cells
  x = 8..13 (`#.##.#.######.#.##.#`): the arcade place (the middle of the maze), and it covers walls only - never a
  pellet, the fruit or a corridor an actor can stand on. Unscaled: exactly the 6 wall cells. Scaled: the 6 characters
  centred in the 24 x 2 bar (upper tile row), written over the maze image; the normal diff restores the wall when it
  goes.
- Pause shows ` PAUSED ` as today (pause before the start keeps READY! away: PAUSED wins).

## 3. Death animation and level-clear READY! (REALTIME, the existing 10-quantum freeze)
- PACRT publishes two values it already knows (PACREQ appended, own fields): `REQ-RTFRZ PIC 99` (freeze quanta left)
  and `REQ-DTHX/REQ-DTHY PIC 99` = the death cell. PACRT computes it before PACGAME MOVE: the player's cell after his
  move of this step (pre-step cell + RT-CUR when the step moves him, else the pre-step cell). Every hit happens on that
  cell (GP1 4.4: same cell only), so no core field is needed. The freeze cause comes from the flags the core already
  leaves untouched during a freeze (ARC-ED `D`, ARC-EC `C`: ATIK is not called while frozen).
- Death (ARC-ED = D), freeze quanta 10..5 = 6 animation frames at the death cell; ghosts, eyes and the reset Pac-Man
  hidden. Frames (scaled 4x2): full sprite, mouth open, half (`▄▀▀▄` shape), small (` ▄▄ `), dot, burst (`*  *`);
  unscaled glyphs: player glyph, `c`, `o`, `.`, `*`, blank. Quanta 4..1: the reset board + READY!.
- Final death (F-LOST = 1, no freeze today): PACDISP plays the same 6 frames before the GAME OVER screen, paced by
  PACPLAT CLOK / WDLN at the current period (TSD: frames emitted without waiting). Display/platform only.
- Level clear (ARC-EC = C): no flash (user, 2026-10-12). Quanta 10..5 as GP2.3 (refilled maze, `CLEARED`, new
  level); quanta 4..1 add READY!.
- Death + level clear in one step (G2CLRD): the death animation wins (one effect per freeze).

## 4. Score popups
- Ghost eaten (ARC-EVT `GHST`, ARC-PTS 200/400/800/1600): the points at the eating cell (Pac-Man's cell of that step).
  Scaled: the 4 digits (`200 ` / `1600`) in the cyan popup colour on the tile's upper row - exactly one 4x2 tile, no
  neighbour cell touched. Unscaled: `GHOST 1600` in the message row.
- Fruit eaten (ARC-EF `F`, ARC-BV points): same mechanism at (10,8), fruit colour (`100 ` ... `5000`). Proposed as
  part of RP (arcade behaviour, same code path); approved.
- Lifetime: REALTIME 6 quanta (0.9 s) kept in PACSCR's own display state (cell, text, quanta left; PACSCR already keeps
  display state such as VS-PREV). A new popup replaces the old one; a death, a level clear or the end removes it.
  TURN: shown on the screen of the eating turn only. No game freeze (the arcade pause after a ghost is not copied:
  game timing and the deterministic references stay as they are).
- Drawing order: map -> fruit -> popup -> eyes -> Pac-Man -> ghosts (an actor on the cell hides the popup).

## 5. HUD high score and end screen
- HUD high score = max(REQ-HISCORE, ARC-SCORE) - the value HS already defines (D38), no per-step state. Shown only
  when REQ-HSST is R or Z (loaded / zero); N (no DD) and E (unavailable) show nothing.
  - Wide: left column `HI-SCORE` + 7 digits at W-B0 + 13 (free row).
  - Tall: title row, after `LEVEL nn` (`HI nnnnnnn`).
  - 80x24 (GS layout B and G family): `HI nnnnnnn` on the title row right of `P A C - M A N   A R C A D E` (the
    61-column status line is full, D37 tradeoff unchanged).
- End screen (scaled families, as today's GS end banner + 3 s WAIT): ARCADE adds under the banner `SCORE nnnnnnn`
  and, when HS is active, `HIGH SCORE nnnnnnn` plus `NEW HIGH SCORE` (REQ-HSNEW Y, player colour, blinking with
  highlighting). HS-END already runs before END, so the values are known. The line-mode end lines are unchanged.
- Level shown in the HUD: already done in GP2.3 (wide / tall / status line) - no change.

## 6. SPEED (RP.3, the roadmap's narrow scope)
- `SPEED(NORMAL|FAST)` = period T 150 / 125 ms on the existing absolute-deadline loop (PACPLAT RT-PERIOD). PARM column
  24 (N / F, absent = N). CLIST keyword `SPEED(NORMAL)`; the CLIST zero-pads LEVEL to 2 digits so column 24 is fixed
  (PACMAIN: PARM-LEN 22-23 parsing unchanged, column 24 read only when PARM-LEN > 23).
- Everything counted in quanta (ghost cadence, fright, fruit, freeze, RP effects) simply runs 1.2x faster; nothing
  is rescaled. Batch / TSD output unchanged (no clock there).
- Acceptance: one live capture at FAST analysed by tools/c3270_rt_game.py: median frame gap 125 ms +-10 %, p95 within
  the NORMAL run's margin, keyboard restored on every frame (no lost key). If FAST misses, SPEED closes at NORMAL only
  (documented), no timing research is reopened (E14 stays closed).

## 7. ESTAE live validation (RP.0)
The PACFSIO abend exit (since G1) is validated with a **test driver, not a hook in the game**: `src/probe/PACRPE.cob`
(load member `PACRPE` in HERC01.PACMAN.LOAD, never called by the game) linked with the production PACFSIO and PACHSIO
objects. CLIST `RPESTAE` runs it from TSO READY.
- E1: FSON, SEND a screen ("PRESS ENTER TO ABEND"), RECV, then a forced 0C7 (invalid packed field) in full-screen mode.
- E2: as E1 but PACHSIO READ (DD DUMMY) runs first, so PACHSIO's own ESTAE is created and deleted before the abend:
  proves the nested exit leaves PACFSIO's in place.
- E3 (control): FSOF first, then the 0C7: a plain line-mode abend, no exit.
- Pass: after E1/E2 the terminal is back in line mode with the abend message and READY, typing works (`TIME`), and an
  immediate `EXEC ... CLIST(PACMAN)` game starts and ends cleanly. Evidence: c3270 screen captures + trace excerpts.

## 8. Soak test (RP.4)
One live REALTIME ARCADE game paused with PF9 for 10 minutes (blocking TGET, no CPU), then resumed and played to a
QUIT: no S522 / timeout, the clock restarts from the resume (no catch-up burst: the first frame gap after the resume is
one period), screen and keyboard intact. The pre-start WAIT (also never soak-tested, RT note) is held 10 minutes in the
same session before the first direction. The TK4- JWT / TSO wait limits are read first and noted in the evidence.

## 9. Tests (D9, D10, D12)
- Independent model: the ref_gs/gx/g4 screen models get an RP branch (ARCADE only) keyed on the published freeze count,
  death cell, popup state and HS values; every RP TSD stream = model byte for byte; size guard asserted on every stream.
- CLASSIC: every existing screen reference unchanged (test_gs, test_gx, test_g4, test_rt, test_s1); text references
  unchanged in both rule sets; tests/test_core_frozen.py unchanged.
- Edge cases (each one a TSD run): death at the start cell; death on the fruit cell; death + extra life in one step;
  death + level clear (G2CLRD, death wins); final death (end-path animation) for LOST; ghost eaten on the last pellet
  (popup + clear: the flash removes it); two ghosts in one step (the later popup wins); popup under an actor; pause
  during a popup and during a freeze (counts stop); PA2 redraw during a freeze frame; READY! with PAUSED before the
  start; HS N / E / R / Z HUD and end screen; NEW HIGH SCORE; LEVEL(n>1) start (practice: shown, not saved); every
  family (W, T, B, G) and SCALE 3; an RP frame over the limit (SCALE T, 1000-byte test limit: decoration dropped, no
  fallback).
- SPEED: PARM parsing cases (absent, N, F, garbage = N; LEVEL 1-digit vs 2-digit with column 24).

## 10. Decisions (user, 2026-10-12) - D39 frozen
1. RP visuals are RULES(ARCADE) only; CLASSIC screens stay byte-identical to their references.
2. Fruit points popup: IN (same mechanism as the ghost popup).
3. Level-clear maze flash: OUT. Between levels: the GP2.3 frame, then READY! in the last 4 freeze quanta.
4. `SPEED(NORMAL|FAST)` = 150 / 125 ms for any REALTIME game (CLASSIC included), opt-in, default NORMAL.
5. ESTAE validation through the separate test driver PACRPE (no abend hook in the game), run first as RP.0.

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
| RP.2b | D40 startup hardening (section 11): PACQRY validity + bounded selection, PACPLAT TRY-COLOUR loop | PACQRYT sequence cases = model; every earlier reference unchanged |
| RP.3 | `SPEED(NORMAL\|FAST)` (section 6): PARM column 24, PACPLAT period, one conversion (PACRT, PACGAME core), CLIST | deck `RP` + CLIST job; live capture analysed |
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
- Where: `READY!` in the player colour (PAL-PLAYER) over the solid central wall bar of ARCADE1, row y = 5, cells
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
- Drawing order (corrected in RP.2, 2026-10-12): map -> fruit -> eyes -> Pac-Man -> popup -> ghosts. The popup
  starts on Pac-Man's own cell, so drawn under him it would never show in TURN (one screen); over him the eating
  screen shows the points, as in the arcade, and he reappears when he moves on. A ghost on the cell hides it.

## 5. HUD high score and end screen
- HUD high score = max(REQ-HISCORE, ARC-SCORE) - the value HS already defines (D38), no per-step state. Shown only
  when REQ-HSST is R or Z (loaded / zero); N (no DD) and E (unavailable) show nothing.
  - Wide: left column `HIGH    nnnnnnn` (HUD-LEFT format) at W-B0 + 13 (free row).
  - Tall: title row, column W-C0 + 69, after `LEVEL nn`: `HI nnnnnnn`.
  - 80x24 GS layout B: `HIGH SCORE nnnnnnn` on row 24, column 2; G family: row 20, column 2 (neither layout has a
    title row and the 61-column status line is full, D37 tradeoff unchanged). (Corrected in RP.2: the first draft
    named a title row that these layouts do not have.)
- End screen (scaled families, as today's GS end banner + 3 s WAIT): ARCADE adds after the banner on the message row
  `SCORE nnnnnnn` (message column + 15) and, when HS is active, `HIGH SCORE nnnnnnn` (+ 30) plus `NEW HIGH SCORE`
  (+ 50; REQ-HSNEW Y, player colour, blinking). HS-END already runs before END, so the values are known. The
  line-mode end lines are unchanged.
- Level shown in the HUD: already done in GP2.3 (wide / tall / status line) - no change.

## 6. SPEED (RP.3; amended by the user 2026-10-12, core change authorised 2026-10-13; implemented, JOB 285)
Superseded first draft: "everything counted in quanta runs 1.2x faster". User rule (2026-10-12): FAST changes the
movement cadence only; every timed event keeps its wall-clock length.
- `SPEED(NORMAL|FAST)` = quantum 150 / 125 ms, PARM column 24 (`F` = FAST, anything else / absent = NORMAL), CLIST
  keyword `SPEED(NORMAL)` (default; first letter, like every keyword). The CLIST pads LEVEL to 2 characters (`7` ->
  `07`; any length other than 1 or 2 -> `01`) so column 24 is fixed. A digit in column 24 makes columns 22-24 one
  3-digit start level (= 1, the D37 rule) and SPEED NORMAL: every pre-RP.3 PARM keeps its meaning (GP2 `A123`).
  REALTIME only (TURN ignores it), CLASSIC and ARCADE, in TSC, TSD and BAT (so FAST is testable); NORMAL = every
  current output.
- One place for the quantum: PACMAIN sets `REQ-RTPER` (150 / 125, PACREQ appended); PACPLAT's deadline period
  (DO-WDLN, otherwise unchanged: absolute deadlines, missed periods skipped, no catch-up) and every conversion read it.
  No other 125 in the sources (checked).
- One conversion, `Q' = (Q x 300 + P) / (2 x P)` (Q quanta designed at 150 ms, P = REQ-RTPER, integer division =
  round half up; P = 150 gives Q exactly), paragraph RT-CONV, identical in PACGAME and PACRT (checked). Applied
  where a REALTIME duration is loaded:
  - core (PACGAME, ARCADE, REQ-PLAY R; authorised core change 2026-10-13, docs/CORE_CHANGES.md): fright and warning
    (FRIGHT-START, LEVEL-ROW), eyes wait (EAT-GHOST), fruit time (FRUIT-SPAWN);
  - PACRT RINI: the death / level-clear freeze (10), READY! (4) and the popup (5), published as `REQ-RTFRT`,
    `REQ-RTRDY`, `REQ-RTPUQ` (CLASSIC uses the freeze only).
  FAST values: freeze 12, READY! 5, popup 6, fruit 72, eyes 24, fright 48/41/32/24/16/41/16/16/8/41/16/8/8, warning
  12/12/12/8/8/12/8/8/4/12/8/4/4 quanta (each = the NORMAL length within half a quantum; warning <= fright on every
  row). Pause stops every one of them (no quantum is played while paused).
- Presentation boundaries (REALTIME; deterministic from quantum counts x REQ-RTPER, never from measured time), with
  REQ-RTFRZ = the freeze quanta left as published (REQ-RTFRT in the death / clear quantum, then down to 0):
  - READY!: before the start, and in the freeze quanta with 0 < REQ-RTFRZ <= REQ-RTRDY (4 at NORMAL = 600 ms, 5 at
    FAST = 625 ms);
  - death animation (flag D): the freeze quanta with REQ-RTFRZ > REQ-RTRDY; frame = min(6, E / 150 + 1), E =
    (REQ-RTFRT - REQ-RTFRZ) x REQ-RTPER ms elapsed since the death quantum (150 ms a frame). NORMAL: frames 1..6 in
    REQ-RTFRZ 10..5 (= 11 - REQ-RTFRZ); FAST: 1 1 2 3 4 5 6 in 12..6;
  - the final death (PACDISP): the same frames, REQ-RTFRZ from REQ-RTFRT down to REQ-RTRDY + 1;
  - popup: shown in the quanta t0 .. t0 + REQ-RTPUQ (t0 = its first quantum; 5 at NORMAL = 6 frames, 6 at FAST = 7
    frames, 900 / 875 ms on screen), removed earlier by a death or a level clear. TURN popups: unchanged.
  At NORMAL these are exactly the RP.2 rules (RP.2 streams byte-identical, JOB 285).
- Unchanged: ghost and Pac-Man cadence per quantum (the game is faster: that is FAST), the RT-VIS animation phase
  (every 3 quanta), the direction TTL (3 steps), D28, keyboard restore. No 100 ms option, no E14/RT0 reopening.
- Tests: tests/test_rp.py sections 2b / rp3_check; FAST cases tests/rpcases/RP3TIM, RP3PAU (tests/search_rp.py
  --rp3); deck RP RP3 runs (12 TSD, 9 BAT, the CLIST PARM lines under the batch TMP). Live (RP.4): one FAST capture
  analysed by tools/c3270_rt_game.py (median frame gap 125 ms +-10 %, p95, freeze and fright wall-clock lengths,
  keyboard restore). A renderer / deadline margin problem at 125 ms is reported, not redesigned.

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

## 11. D40 startup hardening (APPROVED 2026-10-12, implemented RP.2b: JOB 275, docs/evidence/rp2b-d40-build.txt)
Found by RP.0 (docs/evidence/rp-estae-live1.md, rp-estae-live2.md): with line output pending at game start TSO shows
`***`; the ENTER that releases it is queued and TRY-COLOUR's single query read takes it as the reply -> line-mode
fallback, and the real reply is later read as commands. Not an RP.0 / ESTAE defect.

### 11.1 Valid Query Reply (PACQRY, pure; new output QO-VALID, appended to QRY-OUT)
A record is a valid Query Reply only if ALL hold: length >= 5; byte 1 = AID X'88'; it is an exact chain of structured
fields from byte 2 to the last byte, each with length LL >= 4 (2 bytes, LL = 0 not accepted), ID X'81' and its whole
length inside the record; the first field is QCODE X'80' (Summary). Every recorded reply (tests/qreply_*.hex) and the
live RP.0 reply (180 bytes once telnet escaping is removed) satisfy it. ENTER / PF / PA / CLEAR AIDs, typed data, empty
input, truncated or overlong replies, a wrong field ID or a broken chain are invalid. Capability parsing (colour,
highlight, GE, sizes) is unchanged; its results are used ONLY from the accepted record.

### 11.2 Bounded selection (PACQRY, pure state step; QS-ACT / QS-NREC / QS-NWAIT appended to QRY-OUT)
One PACQRY call = one inbound event: a record (length > 0) or an empty read (length 0 = one 0.5 s wait). PACPLAT zeroes
QS-NREC / QS-NWAIT before the first event.
- valid record -> QS-ACT `A` (accept; this record's capabilities are used);
- invalid record -> QS-NREC + 1; empty read -> QS-NWAIT + 1;
- then QS-ACT `F` (fallback) when QS-NREC = 8 or QS-NWAIT = 6, else `R` (read again).
Bounds: the first read is today's blocking QRY read (unchanged); after it at most 8 rejected records and 6 empty waits
(3 s); the fallback drain reads at most 8 more records.

### 11.3 PACPLAT TRY-COLOUR (the only I/O change; PACFSIO unchanged, existing op RECT)
- `QRY` exactly as today (query + first read) -> PACQRY. FS-RC not 0 -> today's path (no colour).
- While QS-ACT = `R`: `RECT` (one TGET NOWAIT; none = 0.5 s wait, length 0) -> PACQRY. A RECT error -> `F`.
- `A`: HAS-COLOUR / HAS-HILITE / HAS-GE / size from QRY-OUT, exactly as today.
- `F`: HAS-* = 0 -> today's conservative fallback (FSOF, line mode) after a drain: `RECT` until an empty read (at most
  8), records discarded. Skipped and drained records are consumed by TGET and never reach the game or line mode.
- Normal clean start (first record valid): `A` at once, no extra PACFSIO call: the same host writes, the same reads,
  the same timing. D28 press-to-start is untouched (nothing after the accepted reply changes). COLOR(YES) (no query),
  TSD and batch never enter this code: every TSD / TSC model stream, the 1.0-MVS oracle and all CLASSIC references
  stay byte-identical.

### 11.4 Tests (D9, D10, D12)
PACQRYT gains a sequence mode (test driver only; its existing single-reply lines unchanged): cards with a record number
in column 9 form one sequence; a card without hex = an empty read. One line per sequence:
`QSL name ACT=a NREC=nn NWAIT=nn C=n H=n GE=n`; expected values from an independent Python model (tests/qry_cases.py).
| Case | Sequence | Expected |
|---|---|---|
| Q1 valid first | real reply | A, NREC 0, NWAIT 0, C/H/GE 1 (= clean start: no extra read) |
| Q2 ENTER first | `7D` + cursor; real reply | A, NREC 1 |
| Q3 typed junk | `7D` + cursor + SBA + EBCDIC text; real reply | A, NREC 1 |
| Q4 other AIDs | PF9 `F9`, PA2 `6E`, CLEAR `6D`; real reply | A, NREC 3 |
| Q5 malformed | truncated reply; LL overrun; wrong ID X'82'; no Summary first; LL = 0; then real reply | A, NREC 5 |
| Q6 empty reads | ENTER, 3 empty reads, real reply | A, NREC 1, NWAIT 3 |
| Q7 no reply (records) | 8 invalid records | F, NREC 8 |
| Q8 no reply (time) | ENTER, 6 empty reads | F, NWAIT 6 |
| Q9 single-record validity | each existing case (C3270 ... ONLY85) and the 4 recorded terminal replies | V as the model |
Clean start unchanged (constraint 6): Q1 + all earlier references byte-identical (TSD streams, oracle, PACQRYT lines) +
a source check that PACPLAT reads again only while QS-ACT = `R`. Live (RP.4): (a) a normal start = the same wire shape
as hs-live (`7E C3`, query, reply, screen, no extra read); (b) the RP.0 reproduction (RPESTAE E3, then the game):
`***`, ENTER -> the full-screen game (no line-mode fallback, no `INVALID COMMAND`).

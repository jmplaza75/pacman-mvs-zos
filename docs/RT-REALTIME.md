# MVS-RT real-time gameplay - plan and frozen design (D33)
Baseline: tag `mvs-gs`, commit 62ab854. Plan approved 2026-10-09. RT0 (probe E14) CLOSED 2026-10-10
(docs/evidence/rt-e14-timing.md). RT1 design APPROVED 2026-10-10 (section "RT1 frozen design" below). Next: RT2.

## Goal
From `direction + ENTER -> one logical turn` to real time: Pac-Man moves on a logical clock, ghosts move on their own under
their AI, a direction key changes the requested direction without ENTER, Pac-Man keeps going until blocked or until a
buffered turn becomes legal, visual animation stays independent of logical movement, partial redraw and the 120 x 27 / 4x2
GS renderer stay in use. Acceptance: one press keeps Pac-Man moving smoothly, ghosts move independently, turns buffer
naturally at intersections, no ENTER during normal play.

## Approved architecture
- A separate REALTIME path (`RT-LOOP`), not automatic movement inserted into the TURN loop.
- `PLAY(TURN|REALTIME)` (new PARM column). Absent = TURN = the mvs-gs behaviour byte for byte (D17). REALTIME becomes the
  CLIST default only after live validation.
- Future `PACRT`: terminal-independent controller (no I/O; same rules as GAME/MAP/AI in test_mvs7): current direction,
  requested direction + TTL, cadence accumulators, pause, death freeze, its own wide counters.
- Separate logical and visual timing; absolute deadlines (`next_deadline += T`, wait only for the remainder); at most one
  terminal write per quantum; partial redraw.
- Per quantum: drain input -> Pac-Man step if due (buffered turn if legal, reverse at once, else continue or stand) -> eat
  -> hit -> ghosts if due (PACAI) -> hit -> life/state -> render. When both are due this is exactly the TURN order. The
  1.0-MVS rule "a crossing is not a hit" is kept and documented as a deviation from the arcade.
- Deterministic ghost cadence via an integer accumulator (no independent real-time timers); AI keeps seed 12345 and tie
  order U,D,L,R (D14).
- Batch REALTIME (one card = one quantum, `+` = no input) is the reference; independent model `tests/ref_rt.py`.
- Core change foreseen (needs authorisation at RT2, not before): `PACREQ` append-only `REQ-STEP` B/P/G, PACGAME player-only
  and ghost-only steps; TURN uses only B.

## Decisions (user, 2026-10-09)
| Topic | Decision |
|---|---|
| Input | c3270 keymap: arrow keys -> four distinct PF AIDs (one direct AID, cleanest latency). Native PF keys stay for diagnostics/tests; `U/D/L/R + ENTER` stays the compatibility fallback. Exact PF numbers chosen after E14. |
| Buffered direction | TTL = 3 Pac-Man steps (provisional), configurable to compare 2/3/4 in RT3; never kept indefinitely. |
| Ghost speed | 4/5 of Pac-Man (provisional), integer accumulator; tuned live later. |
| TICK-COUNT | PACSTATE not widened. RT counters live in PACRT; no RT behaviour may depend on the `PIC 999` counter; TURN keeps state and output. Before RT2: establish what happens when TICK-COUNT exceeds 999; if it can affect game behaviour (not only display), stop and propose the smallest safe change. |

## Phases
| Phase | Content | Gate |
|---|---|---|
| RT0 | Isolated probe E14: timing, input, keyboard restore, typeahead, D28, renderer cost, CPU -> docs/evidence/rt-e14-timing.md | User review of the measurements |
| RT1 | Freeze the REALTIME design with the measured T (D33) | User approval |
| RT2 | PACRT, PACGAME step selector, ref_rt, batch cases | Hercules JOB, all = model |
| RT3 | TSO real-time loop on 120x27 / 4x2 GS, partial redraw | Build JOB + live c3270 |
| RT4 | Live acceptance, CLIST default decision | Evidence, README |

## RT0 / probe E14 scope (authorised)
Isolated from PACMAN: no change to PACMAIN, GAME/MAP/AI, PACSCR, PACPLAT, PACFSIO, PACTSO or the frozen core. Experimental
TIME/POLL/WAIT services live only in the probe; they do not authorise production changes.
- Periods 100, 150, 175, 200, 250 ms, absolute deadlines, STCK/TOD; per period: min / avg / p95 / max period, every overrun,
  busy time per quantum, TPUT return codes, host (Hercules) CPU. Outliers shown; isolated spike vs sustained inability.
- Synthetic tiny frames and representative GS 120 x 27 / 4x2 partial frames from the unchanged renderer.
- Input: per direction AID the smallest keyboard-restore Write; from c3270: prompt unlock, screen intact, no field/cursor
  damage, a second direction at once, rapid AIDs not lost. Typeahead: several AIDs inside one quantum, drain TGET NOWAIT
  until empty, record the exact order (all queued / coalesced / only the latest reliable). PA2, CLEAR, invalid AIDs.
- D28: with and without the COLOR(AUTO) query (query path unchanged): does the first direction AID release the retention?
- Whether `RECT` (fixed 0.5 s) is usable; whether production needs `PACFSIO POLL` and a PACTSO TOD/deadline service.
- Period rule: the smallest tested period with p95 error <= 10%, no sustained overruns (heavy frames included), frames at
  the intended cadence at c3270 (no bursts), reliable AIDs, acceptable keyboard restore/typeahead and CPU. If none passes:
  say so and propose the next experiment.

## RT0 result (measured, docs/evidence/rt-e14-timing.md)
Absolute deadlines: no drift, 0 missed deadlines in all live quanta; STIMER wake jitter 0-12.8 ms at every period; GS
120x27 partial frame about 21 ms, full about 37 ms (80x24: 17 / 32 ms); isolated host stalls up to 108 ms; c3270 receives
frames at the requested cadence; AIDs in order, at most one per keyboard-restore write (2 per quantum observed when an
AID arrives between poll and write); first direction AID releases the D28 retention; CLEAR is swallowed by TSO; c3270
typeahead ON builds seconds of stale autorepeat backlog, OFF drops only keys pressed while locked (0 of 24 direction
changes dropped, no backlog). NOT obtained: a valid physical four-direction burst under 0.5 s (no further probe; with
typeahead OFF keys pressed while the keyboard is locked can be dropped - accepted constraint, mitigated by the 150 ms
restore interval and the 3-step buffered request; fast cornering is an RT3 control-design question if it feels
unreliable). TICK-COUNT (PIC 999): JOB 217 (unchanged mvs-gs, 1,005 blocked turns, RC 0) wraps silently T999 -> T000, no
data exception, display only (status line, HUD, TURNS line); no logic reads it -> PACSTATE unchanged.

## RT1 frozen design (D33, approved 2026-10-10)
Values: T = 150 ms (175 ms fallback/tuning; 100 ms not for production). UP PF7, DOWN PF8, LEFT PF10, RIGHT PF11; U/D/L/R +
ENTER fallback. Request TTL 3 player steps. Player every quantum; ghosts 4/5 by integer accumulator (acc += 4; due when
acc >= 5, then acc -= 5; acc starts at 0: quanta 1..5 = no, yes, yes, yes, yes). Animation frame VIS = (q / 3) mod 2
(flips every 3 quanta = 450 ms; 0 before the start, as the TURN first screen). Death freeze 10 quanta (1.5 s).
Compatibility: `PLAY(TURN|REALTIME)` -> PARM column 19 (`R` = REALTIME, anything else / absent = TURN = mvs-gs byte for
byte). REALTIME needs TSC (or the batch BAT / TSD reference modes); TSO line mode runs TURN. CLIST default stays TURN
until RT4.
Modules:
- PACRT (new, terminal-independent, no I/O, own wide counters RT-Q / RT-STEPS PIC 9(7), state in its WORKING-STORAGE):
  ops RINI (reset), RIN (one input event), RQ (one quantum). Owns current / requested direction, TTL, cadences, pause,
  death freeze, start. Legality via PACMAP WALL (read only); all state changes via PACGAME. Reports its state to the
  driver in PACREQ (REQ-RTSTAT WAIT / RUN / PAUS / FRZ, display fields).
- PACGAME (authorised core change): REQ-STEP B (= the existing turn), P (player only: move, eat, hit, life, state; no
  PACAI), G (ghosts only: hit, PACAI, hit, life, state; no player move, TICK-COUNT not incremented). Anything not P/G = B.
  TURN always B. No-swap / crossing rule unchanged.
- PACREQ (append only): REQ-PLAY, REQ-STEP, REQ-AID, REQ-VIS, REQ-TIME (ms, S9(9) COMP), REQ-RTSTAT, REQ-RTQ, REQ-RTIN,
  REQ-RTCUR, REQ-RTREQ, REQ-RTTTL, REQ-RTFR.
- PACMAIN: separate RT-LOOP (TURN loop untouched). Before start: blocking read (TSC RECV, no RECT polling); the first
  direction starts the clock (deadline base = now) and is quantum 1's input. Per quantum: drain input until empty
  (PACINPT RT read -> PACRT RIN), PACRT RQ, one frame (PACDISP RTQF), deadline += 150 (PACPLAT WDLN; skipped deadlines
  counted). Pause: blocking read until P; resume re-bases the clock. TSC failure -> line mode and the TURN loop.
- PACINPT RT read: TSC = PACPLAT POLL (non-blocking): F7 U, F8 D, 7A L, 7B R, 6E (PA2) RDR, 7D ENTER = typed field
  (U/D/L/R, Q quit, P pause, empty = RDR, else INV); other AIDs ignored; none = NON. BAT/TSD = one card per quantum,
  characters in order = inputs of that quantum (U/D/L/R any case, Q, P, `*` = PA2, `.` `+` blank = none, others INV);
  before the start only a direction makes a card a quantum; a first `A` card is the config.
- PACPLAT: POLL (PACFSIO POLL), CLOK (PACTSO TIME -> REQ-TIME ms), WDLN (PACTSO WAIT until REQ-TIME), RECV with REQ-AID.
- PACFSIO: + POLL = one TGET ASIS,NOWAIT, no wait (existing services byte-identical). PACTSO: + TIME (STCK, ms since the
  first TIME) and DLWT (STIMER WAIT,MICVL for the remainder to an absolute ms deadline; RC 4 if already passed).
- PACDISP / PACSCR: RTQF = one write per quantum. After ENTER / INV / RDR in the quantum: the existing PRMT (WCC C3,
  input field reset, full screen on RDR). Otherwise the new PACSCR op RTQF: the whole image rebuilt from the state with
  VIS from PACRT, diff against the terminal image, WCC C2 (typed text kept), always sent (no change = C2 + SA reset: the
  keyboard restore). BAT: one RT status line per quantum; end lines + `QUANTA nnnnnnn` in REALTIME only.
- c3270 for REALTIME: tools/c3270_rt.sh (keymap above), typeahead OFF by default in that launcher only.
Tests (RT2): independent tests/ref_rt.py (built on the ref_mvs6 game model and the ref_gx_screen renderer) for batch
REALTIME cases and TSD REALTIME streams; the existing regression suite and the 1.0-MVS oracle unchanged.

## RT2 result (2026-10-10, Hercules JOB 222, docs/evidence/rt2-build.txt)
Deck RT (job PACBLDRT, 137 steps RC 0000, no warnings) = the whole GX deck + PACRT + 12 batch and 6 TSD REALTIME runs.
`tests/test_rt.py` PASS: TURN regression (tests/test_gx.py on the GX part: 1.0-MVS oracle unchanged, 61 GS/GX TSD runs,
PACQRY), 12 batch REALTIME runs = tests/ref_rt.py line for line, 181 TSD REALTIME streams = model byte for byte (31 of
them restore-only `C2 28 00 00`). Cases (tests/rtcases): RTLINE (runs to the wall, 4/5 cadence P B B B B, ghost-only
quanta), RTCORNER (buffered corner), RTTTL (3-step expiry), RTREV (reversal), RTMULTI (several inputs in one quantum,
latest wins), RTPRE (input before the start), RTSTILL (hit while stationary, 10-quantum freeze, respawn, LOST), RTPAUSE
(pause/resume, invalid input, PA2 redraw, quit), RTLONG (1102 quanta, legacy TICK-COUNT wraps), RTWIN, RTEDGE /
RTEDGE0 (last pellet eaten onto a ghost: WIN with a life lost / LOST). Core change authorised (docs/CORE_CHANGES.md).
Defects found and fixed during RT2: PACPLAT signed VALUE (JOB 219, IKF2190I-W); BAT read-ahead event overwritten before
the start (JOB 221). NOT exercised by RT2 (needs a live terminal, RT3): the TSC path (POLL, blocking RECV with the AID,
CLOK / WDLN deadlines, PACTSO TIME / DLWT, keymap AIDs, D28 release, CLEAR).
Behaviour details fixed by the implementation (within D33): a blocked player is not a PACGAME call (HUD LAST keeps the
last real move, no BLOCKED); the HUD/end TURN counter is the legacy player-step count (mod 1000), QUANTA the wide RT
counter; inputs before the start or during a pause are reported in the next quantum's IN; ENTER-typed input, invalid
input or PA2 make that quantum's single write a prompt screen (field reset / full redraw); unknown AIDs are ignored;
P + ENTER pauses (no visual pause indicator yet: RT3 presentation); the deciding quantum gets its frame, then the end
banner as in TURN.


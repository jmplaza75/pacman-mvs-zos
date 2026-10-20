# ZOS-7 ARCADE - discovery and design report (2026-10-19; design APPROVED with decisions D1-D5, see the end)

Status: discovery only. No source / JCL / dataset change, no z/OS access, no build, no live run, nothing committed.
Handoff check PASS: branch `zos`, working tree clean, HEAD e2d92e1 = annotated tag `zos-6` ("ZOS-6 realtime live
acceptance"), no remote / upstream configured (no push required).
Oracle: 2.0-mvs-max (frozen MVS behaviour, oracles 307-316 in tests/oracle20, the independent models in tests/).
Plan reference: docs/ZOS-MIGRATION-PLAN.md section 6 "ZOS-7 ARCADE" (objective, "nothing in src/ changes", gp1 / gp2 /
rp tests, live scenarios). This report refines that plan with the ZOS-6 findings.

## A. Exact scope
ARCADE = `RULES(ARCADE)` = PARM column 21 `A` (CLIST keyword RULES, default ARCADE since D43): the 2.0 game rules of
D36 (GP1 power pellets, fright, 200 / 400 / 800 / 1600 chain, eyes / return home), D37 (levels 1-99, refill, per-level
table, fruit, extra life at 10000, WON after level 99), D39 (RP: READY!, death animation, popups, ARCADE HUD and end
screen, SPEED conversion) and the ARCADE presentation of D38 (HUD / end-line high score). CLASSIC stays 1.0-MVS.
ZOS-7 proves on z/OS, with the installed zos-6 module (no rebuild proposed):
1. ARCADE batch / TSD output = the frozen models (and oracle blocks where they exist), including ARCADE under
   PRESENT(COALESCED) for the events ZOS-6 did not dry-run (final death, level clear, extra life, ghost chain);
2. ARCADE live on the real TSO / TN3270E path: one TURN case (no timing) and REALTIME cases with
   PRESENT(COALESCED) explicit, every write = the canonical model, the ARCADE end sequence and closure;
3. the high-score path only as far as ARCADE needs it to run: READ-only (see section I); no write, no recovery test.
Out of ZOS-7: high-score persistence / write / UNAVAILABLE / NOT SAVED live, ESTAE / PACFSIO C3 (E2), sound and alarm
patterns live (ZOS-8); the full GP1 / GP2 / GP23 / RP regression batteries (too large for the site, ZOS-9 / 10);
the release default of PRESENT (deferred, EVERY stays default).

## B. Current-state findings (the 12 questions)
1. **Entry / mode selection.** CLIST(PACMAN) keyword RULES(ARCADE) (default) -> PARM column 21 `A`; PACMAIN sets
   ARC-ON; LEVEL(n) -> columns 22-23; SPEED -> 24; ALARM -> 25; PRESENT(COALESCED) -> column 26 `C` (Z5). The CLIST
   runs its HS block only for ARCADE (`IF &W = A`: `&SYSDSN('<p>.DATA') = OK` -> `ALLOC F(PACHS)
   DA('<p>.DATA(HISCORE)') SHR`, else DUMMY; FREE F(PACHS) at every exit).
2. **Source modules.** PACMAIN (driver, HSRD after INIT / HSWR at the end), PACGAME (ATIK, ARCADE move / hit, K-LVL
   table, fruit, extra life), PACMAP (LDA, power pellets, CNT), PACAI (flee, cadence), PACRT (freeze, READY!, popups,
   death-frame publication, SPEED conversion), PACDISP (ARCADE lines, alarm classes, FINAL-DEATH, end pause), PACSCR
   (ARCADE screens, HUD, popups, RTQS), PACPLAT (HSRD / HSWR, PSLT), PACHSIO (PDS I/O), PACINPT (cards / TSO input),
   PACFSIO / PACTSO (terminal, clock), PACQRY (Query Reply).
3. **Copybooks / interfaces.** PACARC (all ARCADE state, own 01; passed to GAME / AI / RT / DISP / SCR), PACSTATE
   (unchanged; SCORE mirrors ARC-SCORE low digits), PACREQ (REQ-RULES, level, REQ-HS*, REQ-RTPER, REQ-PMODE /
   REQ-PRES), PACMREQ, PACPAL (palette, layout), PAC-DS.
4. **Terminal / platform services.** The same as ZOS-6: PACFSIO FSON / QRY / SEND / RECV / POLL / FSOF (TPUT NOEDIT,
   TGET ASIS), PACTSO CLOK / WAIT / DLWT / WDLN, PACPLAT PSLT. ARCADE adds no service; it adds larger streams
   (HUD, popups, fruit, frightened colours) and the end sequence below.
5. **Persistence.** PACPLAT HSRD (always, ARCADE) -> PACHSIO READ (BLDL, OPEN TYPE=J); HSWR -> PACHSIO REPL / WRIT
   only when the score strictly beats the stored one AND the game is eligible (started at LEVEL 1). Verified in
   PACPLAT DO-HSWR: `REQ-HSELIG NOT = 'Y'` exits before any PACHSIO call. z/OS state: Z00000.PACMAN.DATA exists (PDS,
   ZOS-1 J1) and has never been written by the project (ZOS-3 used HSTEST.T1 / HSFULL.T1; ZOS-4/5/6 live = CLASSIC);
   HISCORE is expected absent (HSST Z, value 0) - to be confirmed by one read-only member listing before the live.
6. **Differences from REALTIME (ZOS-6).** ZOS-6 live was CLASSIC AI(0). ARCADE adds in the running loop: fright /
   warning colours, eyes, popups (RTQS-advanced, offline-proven), READY!, in-freeze death animation, level-clear
   freeze, fruit, HUD; and after the loop: **FINAL-DEATH** (finding F1 below) and the ARCADE end screen / lines.
7. **Differences from CLASSIC.** Rules (D36 / D37), PACARC state, 7-digit score, ARCADE status / level lines, end
   lines (TURNS 7 digits, GHOSTS EATEN, FRUITS EATEN, LEVEL, high-score lines), ARCADE-only RP visuals, the CLIST HS
   block, alarm classes from counters.
8. **Current MVS ARCADE behaviour.** 2.0-mvs-max: CLIST default ARCADE; GP1 / GP2 / HS / RP / S2 live PASS on TK4-
   (docs/evidence/gp1-live.md, gp2-live.md, hs-live.md, rp-live.md, s2-live.md, G8 smoke).
9. **Reference models / oracles.** tests/ref_arcade.py (GP1), ref_gp2.py (Level, LevelRT, rt_simulate), ref_rp.py
   (RP tracker, decorations, bells), ref_hs.py, ref_s2.py, ref_rt.py (present='C' since ZOS-6); oracles 310 (GP2 /
   GP23 / RTT / RTB), 309 (RP, known-boundary anchoring), 312 (HS).
10. **Test coverage.** MVS: test_gp1, test_gp2, test_rp (6265 streams), test_hs, test_s2, search_* edge generators.
    z/OS: tests/test_zos_tools.py - section 22 already runs every RP / GP2 REALTIME ARCADE case (10 cases x 2 speeds)
    through the COALESCED model (image invariant vs EVERY, popups on skipped quanta, final screens).
11. **Already portable / proven on z/OS (batch / TSD on PACZ2D or PACZ6D):** PACZ2G1 JOB09069 (10 ARCADE batch runs),
    PACZ2G2 JOB09114 (3 ARCADE REALTIME batch), PACZ2G3 JOB09128 (level clear TURN, fruit, level 2 / 3 frights),
    PACZ2RP JOB09245 (4 ARCADE FAST batch: RP3TIM, RP3PAU, RPLOST, G2RPAU), PACZ3HS1-8 (ARCADE HS batch incl.
    write / heal / full directory on test PDSs), PACZ3TD1-4 (12 ARCADE TSD S2 runs, EVERY), PACZ6DR1 / DR2 N5 / F5
    (ARCADE RPCLRPU TSD, COALESCED, both speeds). Every ARCADE batch rule is therefore already = oracle / model on z/OS.
12. **What still blocks ARCADE on z/OS:** no source blocker found. Open items:
    - F1 FINAL-DEATH writes outside the presentation slot under COALESCED (design decision D1);
    - no ARCADE live run has ever happened on z/OS; the ZOS-6 driver / checker are CLASSIC-only (model() = ref_rt
      with `AI0 1`, CLASSIC end lines, no HS lines, no end-sequence writes);
    - the MVS live tools (tools/gp2_live.py + c3270_gp2_trace.py: one card per quantum, `Wait(Output)` lockstep) are
      incompatible with z/OS REALTIME (writes only every 2nd / 3rd quantum; AIDs only in TN3270E send windows) -
      scenarios LIVEA / LIVEC cannot be replayed; LIVEB (TURN) can;
    - the CLIST HS block will touch Z00000.PACMAN.DATA in any ARCADE live game (read; write if eligible) - boundary in I.

**Finding F1 (FINAL-DEATH under COALESCED).** PACDISP SCR-ENDS -> FINAL-DEATH (ARCADE, LOST, REALTIME) plays the
death frames k = REQ-RTFRT down to REQ-RTRDY + 1 through SCR-RTQF directly, one WDLN period apart (150 / 125 ms),
bypassing PACMAIN's PSLT; then the end screen. ref_rt models exactly this (the frames are not slot frames), so source
and model agree; ZOS-6 dry runs N4 / F4 were CLASSIC and never reached it; ZV-D33 text speaks only of running quanta.
On z/OS this is a burst of ~6 (NORMAL) / ~7 (FAST) writes at T after the last input; the ZOS-6 evidence (R1-T3: 432
writes delivered at ~T with no input) says the writes are delivered; no input is expected in it. Not a functional
incompatibility; it is a presentation-contract question.
**Finding F2 (in-game death animation under COALESCED).** The 6 death frames inside a death freeze are quantum frames
and are coalesced like any other (stride 2: every 2nd frame shown; stride 3: every 3rd). Consistent with ZV-D33 (no
replay), already modelled and offline-tested; a visible characteristic, not a defect.

## C. Source-change proposal
**Proposed: none** (matches the migration plan "nothing in src/ changes" for ZOS-7).
- D1 option (a) RECOMMENDED: accept FINAL-DEATH as a documented ZV-D33 end-sequence exception (after the last
  logical quantum; no input; <= 7 writes at T; then the end screen and the unchanged 3 s end pause). The checker
  models these writes explicitly as END-SEQUENCE writes (exact count / order / bytes from the model, allowed only
  after the game-ending quantum), never as slot writes. Difficulty low, risk low.
- D1 option (b), only if you reject (a) or the live shows a problem: Z6 in PACDISP FINAL-DEATH - under REQ-PMODE C
  present only every 2nd / 3rd death frame (PSLT-equivalent), model change in ref_rt, rebuild (PACZ7BLD), dry runs,
  promotion. Difficulty medium, risk medium (source change, rebuild, re-promotion; touches a frozen-path paragraph).

## D. Modules guaranteed unchanged in ZOS-7 (with option a)
PACRT, PACGAME, PACMAP, PACAI, PACINPT, PACQRY, PACFSIO, PACTSO, PACHSIO, PACPLAT, PACDISP, PACSCR, PACMAIN, every
copybook (PACARC, PACSTATE, PACREQ, PACMREQ, PACPAL), the z/OS CLIST (not changed, not reinstalled), the installed
LOAD(PACMAIN) / PACZ6D / PACZ2D, CEEOPTS. Also frozen: zos5_live_check.py, zos6_live_check.py, zos6_drive.py,
zos6_dry.py (ZOS-6 evidence tools; ZOS-7 imports them, as ZOS-6 imported ZOS-5), the ZOS-6 gates.

Ownership / risk map:
| Module | Class | ZOS-7 change |
|---|---|---|
| PACGAME, PACMAP, PACAI, PACRT | A portable, frozen core (Z1 only) | none |
| PACINPT, PACQRY, copybooks | A | none |
| PACFSIO, PACTSO | B platform, validated (C3 open -> ZOS-8) | none |
| PACPLAT (PSLT), PACMAIN (Z4) | B validated in ZOS-6 | none |
| PACDISP, PACSCR (Z4) | B display, validated; ARCADE paths batch / TSD-proven; FINAL-DEATH = F1 | none (option a) |
| PACHSIO, PACPLAT HSRD / HSWR, CLIST HS block, DATA(HISCORE) | D service (ZOS-8) | none; read-only use |
| alarm (PACDISP bells, S2) | D (ZOS-8) | none; SOUND(NO) in every ZOS-7 live case |
| CLIST(PACMAN) | B (Z2, Z3, Z5) | none |
| ref_* models, zos7 checker / driver / dry tool, fixtures, tests | E | new / additive |

## E. Model / test additions (local)
1. tools/zowe/zos7_scen.py: builds the live REALTIME scenario cards and proves them offline (section G): canonical
   run + a jitter sweep (every key shifted -2 .. +2 quanta and the AID windows lo .. lo + 2) - every variant must keep
   the intended events (power, fright, ghost eaten, deaths, LOST). Already checked in discovery: the L2 plan below at
   LEVEL(2) gives LOST / 1 ghost eaten / SCORE 0000510 in 81 / 81 jitter variants at both speeds. Difficulty low.
2. tools/zowe/zos7_live_check.py (new; imports zos6_live_check / zos5_live_check helpers unchanged): ARCADE model
   (ref_rt + ref_gp2 Level / LevelRT, start level, hs input from the precheck), ARCADE end lines + HS lines, the
   END-SEQUENCE writes (F1), a TURN mode for L1 (model frames from ref_gp2, the ZOS-5 TURN boundary rules), the ZOS-6
   rules carried unchanged (stride 2 / 3, bounded backtracking placement, F1 C3 CONTROL narrow rule, envelope
   diagnostic-only under COALESCED, frozen GATES). Difficulty medium-high (largest item), risk medium.
3. tools/zowe/zos7_drive.py (new): plans L1 / L2 / L3, PRESENT(COALESCED) explicit for L2 / L3, SOUND(NO),
   LEVEL(n >= 2), the ZOS-6 driver contract (no logon, no trace control, no retry, Wait(5,Unlock)). L1 sends one
   command + ENTER per write (TURN, blocking read: no contention issue, as ZOS-5). Difficulty low-medium.
4. tests/zos7_fixture.py + tests/test_zos_tools.py section 24: synthetic traces from the models; positives L1 / L2 /
   L3; negatives (missing / extra / replayed write, an end-sequence write outside the end, wrong HS line, a write to
   the slot grid broken, F1 C3 outside its context, PRESENT absent in the EXEC); the FINAL-DEATH count per speed.
   Difficulty medium.
5. tools/zowe/zos7_dry.py: the dry-run decks + fail-closed comparator (pattern of zos6_dry.py). Difficulty low-medium.

## F. Batch / TSD validation plan (z/OS, PACZ6D test member = PACMAIN bytes; no rebuild, no promotion)
Two jobs, one at a time, each < 4,000 spool lines (split further if the generator estimate says so):
| Job | Steps (TSD wide 120 x 27 unless noted) | Proves |
|---|---|---|
| PACZ7DR1 | E3 one ARCADE REALTIME TSD step under PRESENT(EVERY) whose oracle 309 / 310 block is anchorable (chosen by the generator; the 309 RPT1 boundary avoided); N6 / F6 RPLOST COALESCED; N7 / F7 RPDCLR COALESCED | Z4 left ARCADE EVERY output = oracle; FINAL-DEATH end sequence (F1) and a death + level clear under coalescing |
| PACZ7DR2 | N8 / F8 G2RXD COALESCED (LEVEL 13, extra life); N9 / F9 RTGPA COALESCED (ghost chain); NL2 / FL2 = the L2 / L3 live scenario cards (canonical placement) | extra life / chain / the exact live scenarios on the host, deterministic |
Each step: CC 0000, every TSD write = model (ref_rt present='C' + ref_gp2), end lines exact; SOUND N except where an
oracle block needs Y. Batch rules (BAT) need no new job: already = oracle on z/OS (B.11).

## G. Live validation plan (one c3270 session, ISPF option 6, 120 x 27, same procedure as ZOS-6)
Precheck (read-only, before the session): LOAD(PACMAIN) = PACZ6D (zos-6 state), CLIST(PACMAN) = the zos-6 bytes, the
member list of Z00000.PACMAN.DATA (HISCORE present or not, and its record if present) -> the model's hs input.
| Case | EXEC operands | Plan | Proves (beyond ZOS-6) |
|---|---|---|---|
| L1 TURN | `RULES(ARCADE) AI(0) GHOSTS(1) LEVEL(13) PLAY(TURN) ANIM(NO) SOUND(NO)` | MVS scenario B (tests/gp2live/LIVEB.txt, 78 cards) typed one per write | ARCADE screens byte for byte with no timing: LEVEL 13 HUD / KEY 5000, power pellets, 4-turn fright, fruit appear / eat, two keys, extra life at 10000 and the 4th life icon, ARCADE end lines + `START LEVEL 13: HIGH SCORE NOT RECORDED` |
| L2 NORMAL | `AI(0) GHOSTS(1) RULES(ARCADE) LEVEL(2) PLAY(REALTIME) SOUND(NO) PRESENT(COALESCED)` | EXEC, `***`, ENTER; 2 s; PF8 (D: both left power pellets, stop at (2,9)); ~2 s; PF11 (R along row 9 into the frightened ghost: 200 popup, eyes); ~6 s; PF10 (L, leave home); ~6 s; PF11 (death 1); ~3 s; PF8, ~6 s, PF11 (death 2); ~3 s; PF8, ~6 s, PF11 (death 3 = GAME OVER); end sequence; `***`; ENTER; shell | ARCADE REALTIME under COALESCED stride 2 live: fright colours, popup on the presented grid, eyes / revive, death freezes with READY!, the FINAL-DEATH end sequence (F1), ARCADE end screen + 3 s pause, ARCADE end lines + HS lines, CLIST HS block read-only, closure |
| L3 FAST | L2 + `SPEED(FAST)` | the same keys, waits x 1 (the model fixes the quanta) | stride 3 with ARCADE FAST conversions (fright 34 -> 41, freeze 10 -> 12) and the FINAL-DEATH burst at 125 ms |
Every key of L2 / L3 is sent with Pac-Man standing at a wall or after a respawn, so the path does not depend on the
landing quantum; the checker still places every AID in its bounded window. L3 is recommended (the 125 ms end
sequence is the most aggressive write pattern of ZOS-7) but can be dropped by decision D4: every FAST ARCADE rule is
already batch / TSD-proven. Not repeated live (ZOS-6 proved them): pause / resume, PA2, invalid input, input
reaction, the CLASSIC freeze.

## H. Risks
| # | Risk | Likelihood / impact | Mitigation |
|---|---|---|---|
| R1 | FINAL-DEATH burst (F1) interacts badly with TN3270E contention (late / merged writes) | low / medium | writes are output-only (R1-T3 evidence); checker models them; option (b) as fallback |
| R2 | live scenario misses an intended event (late AID beyond the fright window) | low / low | wall-stop design + 81 / 81 jitter sweep; generous fright margin at LEVEL(2) (~10 quanta); the case still PASSes functionally if the model matches - "event not exercised" is reported, not hidden |
| R3 | HS read in TSO foreground fails (OPEN / BLDL under LE) -> HIGH SCORE UNAVAILABLE | low / medium | batch IKJEFT01 proved the read (ZOS-3); classify ENVIRONMENT, never retry; HS acceptance stays ZOS-8 |
| R4 | HISCORE state unknown -> HUD / end-line model mismatch | medium / low | read-only member listing in the precheck feeds the model |
| R5 | ARCADE coalesced frames larger (several quanta of HUD / popup diffs) | low / low | section 22 image invariant already passed for every ARCADE case; the checker reports max stream bytes per write |
| R6 | checker complexity (ARCADE + TURN + end sequence) | medium / medium | reuse frozen helpers; fixture negatives per rule; one local review before any live |
| R7 | site output limit (S722) on dry runs | medium / low | per-job line estimate from the generator, split before submission |
| R8 | ZOS-8 scope creep (HS write, bells) | low / medium | LEVEL(n >= 2) + SOUND(NO) everywhere in ZOS-7 live |

## I. Dependencies on ZOS-8 (high score / services)
ARCADE can be accepted in ZOS-7 without any new persistence behaviour. Boundary:
- every ZOS-7 live ARCADE case starts at LEVEL(n >= 2) -> not eligible -> PACPLAT DO-HSWR never calls PACHSIO
  (proved from source); Z00000.PACMAN.DATA is only allocated SHR and read (HSRD). No member is created or updated.
- if HISCORE is absent: HSST Z, value 0, HUD high score = the game score, end lines `HIGH SCORE nnnnnnn LEVEL nnn` +
  `START LEVEL nn: HIGH SCORE NOT RECORDED`; if present: its value (from the precheck).
- not in ZOS-7: an eligible LEVEL(1) live game, NEW HIGH SCORE / NOT SAVED / UNAVAILABLE live, the renamed-DATA case,
  ESTAE E1-E3, C3, audible alarm / S2 live (all ZOS-8). Batch / TSD dry runs never allocate the installed DATA.
- dependency direction: none from ZOS-7 on ZOS-8 work. ARCADE does not fundamentally need persistence (no DD /
  DUMMY = silent / unavailable paths exist and are batch-proven).

## J. Proposed implementation order (each step stops for review)
1. Decisions D1-D5 (below).
2. zos7_scen.py: L2 / L3 cards + jitter proof; L1 = LIVEB re-checked through the model with SOUND(NO). Low.
3. zos7_live_check.py + zos7_fixture.py + test section 24 (local). Medium-high.
4. zos7_drive.py plans L1 / L2 / L3 (local, fake x3270if tests). Low-medium.
5. zos7_dry.py: PACZ7DR1 / DR2 decks + comparator, line estimates (local). Low-medium.
6. Gate: review -> submit PACZ7DR1, then PACZ7DR2 (one at a time).
7. Gate: read-only precheck (load / CLIST identity, DATA member list).
8. Gate: live session L1 -> L2 -> (L3), one run each, checker after each, STOP on any non-PASS.
9. Closure: docs/evidence/zos7-arcade.md, CURRENT_PHASE, commit + tag zos-7.

## K. Explicit acceptance criteria
- Source: no change to any file under src/ (option a); zos_c2 / test_core_frozen / test_g8 / r3_gate PASS; frozen
  tools unchanged.
- Offline: test_zos_tools.py full PASS incl. section 24; jitter proof 100 % for L2 / L3.
- Batch: PACZ7DR1 / DR2 every step CC 0000; every write = model; E3 = its oracle block; FINAL-DEATH frame count
  and bytes = model at both speeds; end lines exact.
- Live L1: every PACMAN write = the ARCADE TURN model byte for byte; cards = LIVEB exactly; end lines exact incl. the
  HS lines; `***`, ENTER, shell.
- Live L2 / L3: canonical ARCADE model exact (all game writes and the end-sequence writes); writes only on the
  approved slots (stride 2 / 3, start base) inside the running loop, the end sequence only after the game-ending
  quantum; no stale replay, no catch-up burst inside the loop; AID placement exact; F1 C3 only under the narrow rule
  (counted); the frozen ZOS-6 gates for the principal segment (NORMAL 280-320 / <= 450 / <= 1000 / backlog <= 100;
  FAST 345-405 / <= 525 / <= 1000 / <= 100) and reactions (each <= 1000 / 1075, median <= 750 / 825); intended
  events present (ghost eaten 1, deaths 3, LOST) or reported as not exercised; envelope diagnostic only;
  Z00000.PACMAN.DATA unchanged (post-run member listing = precheck).
- Margins are not tuned after a result; a non-PASS is classified first, never rerun automatically.

## Decisions requested
- D1 FINAL-DEATH under COALESCED: (a) documented end-sequence exception, no source change (recommended) / (b) Z6.
- D2 accept F2 (coalesced in-game death animation) as a ZV-D33 characteristic.
- D3 HS boundary: LEVEL(n >= 2) in every ZOS-7 live case, read-only DATA, read-only member listing in the precheck.
- D4 live set: L1 + L2 (+ L3 recommended).
- D5 dry-run set of section F (two jobs on PACZ6D).

## Decisions (user, 2026-10-19) - ZOS-7 starts as VALIDATION-ONLY
No production source change unless real ZOS-7 evidence demonstrates a source defect.
- **D1 APPROVED (a): the ARCADE final-death sequence is an explicit, narrow end-of-game exception to COALESCED
  presentation.** Scope: the game is already logically LOST; only the final death animation (PACDISP FINAL-DEATH);
  NORMAL exactly 6 writes, FAST exactly 7, one logical quantum apart; then the end screen; no gameplay input expected.
  It permits no other non-coalesced ARCADE write. Acceptance: exact model bytes, exact frame order, no stale replay, no
  duplicate / catch-up frame beyond the model, the correct transition to the end screen. The stride-2 / stride-3 rule
  is not applied to these frames; their timing is reported separately (no gate). PACDISP is not changed.
- **D2 APPROVED:** the in-game death animation stays under ZV-D33 (NORMAL every 2nd, FAST every 3rd logical frame).
- **D3 APPROVED:** every ZOS-7 live case starts at LEVEL >= 2; ZOS-7 never writes high-score state; one read-only
  inspection of the existing high-score / DATA state before the first live session; no dataset / member is created,
  reset or updated. High-score writing and recovery stay ZOS-8.
- **D4 APPROVED:** live L1 (TURN, scenario B, LEVEL 13, ANIM(NO), SOUND(NO)), L2 (REALTIME NORMAL) and L3 (REALTIME
  FAST, REQUIRED: the fastest physical pattern of D1), all PRESENT(COALESCED) explicit, SOUND(NO); no other live case
  unless one of these exposes a genuine coverage gap. ZOS-6 rules carried forward unchanged (stride 2 / 3, the narrow
  F1 C3 CONTROL rule, the envelope diagnostic-only under COALESCED, the frozen gates).
- **D5 APPROVED:** PACZ7DR1 / PACZ7DR2 on PACZ6D, no rebuild; split a job if its predicted SYSOUT is unsafe, never
  drop approved coverage.
- Tools: new ZOS-7 tools may import the frozen ZOS-6 infrastructure; zos6_live_check.py is not made ARCADE-aware.

## Local implementation (2026-10-19; nothing built, submitted or run on z/OS, nothing committed)
| File | Role |
|---|---|
| tools/zowe/zos7_scen.py | the L2 / L3 wall-stop plan (keys + waits), cards, outcome, the landing-shift proof; L1 cards |
| tools/zowe/zos7_drive.py | the L1 / L2 / L3 plans; reuses zos6_drive.Driver unchanged |
| tools/zowe/zos7_live_check.py | the ARCADE checker (imports zos6_live_check / zos5_live_check unchanged) |
| tests/zos7_fixture.py | synthetic L1 / L2 / L3 traces (reuses the zos6_fixture renderer) |
| tools/zowe/zos7_dry.py, jcl/zos/PACZ7DR1.jcl, jcl/zos/PACZ7DR2.jcl | the dry-run decks of record + comparator |
| tests/test_zos_tools.py section 24 | everything above, offline |
Facts and choices made during the implementation (for review):
1. **L2 / L3 plan** (both speeds; seconds after the previous key): PF8 2.0 (start) - PF11 2.1 - PF10 6.0 - PF11 5.0 -
   PF8 34.0 - PF11 3.0 - PF8 6.0 - PF11 3.0; no Q (the game ends LOST). The 2.1 s wait is fixed by the maze: the right
   turn must land after Pac-Man reached (2,9) (else he turns into row 4 / 8) and soon enough to reach the ghost inside
   the LEVEL 2 fright (34 / 41 quanta). The 34 s quiet run after death 1 is the principal segment of the frozen ZOS-6
   gates (>= 200 logical quanta: 227 NORMAL / 272 FAST). Canonical outcome LOST / SCORE 0000510 / 1 ghost / LIVES 0 at
   both speeds; every combination of a -5 / 0 / +5 quanta landing shift of each key (2187 per speed) gives that
   outcome; no shift that still ends the game LOST gives another outcome (a late key leaves the game running: no
   closure, FUNCTIONAL FAIL / driver STOP).
2. **EXEC operands:** RULES(ARCADE) is not typed - it is the installed CLIST's default (D43; CLIST unchanged since
   zos-6) - so every EXEC is <= 113 characters, the longest proven live (R2): L1 `AI(0) LEVEL(13) PLAY(TURN) ANIM(NO)
   SOUND(NO) PRESENT(COALESCED)` (101), L2 `AI(0) LEVEL(2) PLAY(REALTIME) SOUND(NO) PRESENT(COALESCED)` (95), L3 the
   same + `SPEED(FAST)` (107). The checker proves ARCADE by the ARCADE model and end lines.
3. **Checker write classes** (no broad exemption): COALESCED gameplay writes (ZOS-6 grid rules), the D1 final-death
   writes (classify(): only in a LOST game, consecutive, after every gameplay write, immediately before the one end
   screen; count 6 / 7 and = the model's freeze - READY! quanta), the end screen (exactly one, last), transport /
   control records (KRI, narrow F1 C3). Final-death timing reported separately; the ZOS-6 timing / gates run on the
   gameplay writes only. The freeze-span proxy of each in-game death is reported as information (it was an R1 gate;
   no new ZOS-7 gate). Freeze mutants are reported (ARCADE shows READY!: on the synthetic traces DISCRIMINATED).
4. **States:** PASS, FUNCTIONAL FAIL, ENVIRONMENT / TIMING BLOCKED, and COVERAGE INCOMPLETE (every write = model but the
   intended outcome is missing: never PASS). L1 intended: QUIT / SCORE 0010780 / LIVES 4 (extra life) / 2 fruits.
5. **High score:** the checker takes the read-only precheck result (`--hiscore ABSENT` or the 80-byte record) for the
   HUD and the end lines (tests/ref_hs.py); LEVEL >= 2 never saves (PACPLAT DO-HSWR exits before PACHSIO unless
   eligible - pinned in section 24).
6. **Dry runs:** PACZ7DR1 = E3 (oracle 311 G3R7: G2RPAU, ARCADE REALTIME, PRESENT(EVERY), its PARM exactly), N6 / F6
   RPLOST, N7 RPDCLR, F7 S2XLC; PACZ7DR2 = N8 G2RXD, F8 S2XLD, N9 / F9 RTGPA, NL2 / FL2 (the L2 / L3 cards), T1 (L1 =
   LIVEB TURN). RPDCLR / G2RXD are NORMAL-timed (at FAST both end LOST before their level clear / extra life), so FAST
   uses the FAST-designed S2 cases of the same events (S2XLC level clear + extra life, start 12; S2XLD death + extra
   life, start 13); the self-test pins death / level clear / extra life / ghost eaten / final death at both speeds
   under COALESCED. Estimated SYSOUT 2519 / 3333 lines (+ JES ~200): both below the 4,000-line rule, no split needed.
   SOUND N, ALARM S, no PACHS DD (the dry runs never read or write a high score). Comparator = the frozen ZOS-6
   parse_tsd / compare_tsd; self-test PASS (E3 = oracle 311 line for line; every injected fault detected, including a
   dropped / duplicated final-death frame at both speeds).

## Closure (2026-10-19): ZOS-7 COMPLETE
PACZ7DR1 JOB09981 and PACZ7DR2 JOB09992 PASS; live L1 / L2 / L3 PASS (one run each); D1 confirmed on z/OS (6 / 7
final-death writes); no production source change was required; DATA read only (HISCORE absent before and after).
Evidence: docs/evidence/zos7-arcade.md. ZOS-8 keeps high-score writing, recovery and live sound.

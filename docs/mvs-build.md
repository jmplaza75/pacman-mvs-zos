# MVS build procedure (MVS-0)
1. Hercules/TK4- running; `.env` (gitignored, mode 600) holds `HERC01_PASSWORD`.
2. First use only: `./tools/submit.sh jcl/mvs/ALLOC.jcl` (creates HERC01.PACMAN.COBOL/COPY/LOAD; not idempotent).
3. `python3 tools/make_deck.py PACHELLO && ./tools/submit.sh build/PACHELLO.jcl`
4. `./tools/job_output.py PACBLD00 > build/PACBLD00.txt && ./tools/check_hello.py build/PACBLD00.txt`
Pipeline: IEBGENER upload -> IKFCBL00 -> IEWL (SYS1.COBLIB) -> execute -> SYSOUT.
Environment notes: socket jobs need HERC01 credentials (injected in memory by send_deck.py, redacted in output);
printer output in ~/mainframe/tk4/prt/prt00e.txt.
## MVS-0 result (2026-10-07)
ALLOC JOB 111 RC 0000. PACBLD00 JOB 112: SRC1/COB1/LINK/RUN1 all RC 0000, banner printed;
rerun reproduced the same result. Evidence: docs/evidence/mvs0-pachello.txt.

## MVS-1: static board (2026-10-07)
Source `src/cobol/PACMAIN.cob` (map in WORKING-STORAGE, 20x10), data copy `maps/LEVEL1.txt`.
Build/run: `python3 tools/make_deck.py MVS1 && ./tools/submit.sh build/MVS1.jcl`, then
`./tools/job_output.py PACBLD01 > build/PACBLD01.txt && python3 tests/test_map.py build/PACBLD01.txt`.
Result: PACBLD01 JOB 114, all RC 0000, SYSOUT identical to tests/expected/MVS1.txt (no corruption).
Evidence: docs/evidence/mvs1-static-map.txt. No movement or ghosts yet.

## MVS-2: player by turns (2026-10-07)
`src/cobol/PACMAIN.cob` now reads U/D/L/R/Q (any case), one per SYSIN card; start (2,2); walls and map
bounds block; blocked moves count as a turn, invalid commands do not; Q or EOF ends. Pellets are not
consumed yet (MVS-3). Build: `python3 tools/make_deck.py MVS2 && ./tools/submit.sh build/MVS2.jcl`, then
`./tools/job_output.py PACBLD02 > build/PACBLD02.txt && python3 tests/test_mvs2.py build/PACBLD02.txt`.
Tests: `tests/cases/MOVES.txt` (moves, 3 wall bumps, invalid `X`, lowercase, QUIT with trailing command
ignored) and `EOF.txt`; expected output comes from the independent model `tests/ref_mvs2.py`.
Result: PACBLD02 JOB 117, SRC1/COB1/LINK/RUN1/RUN2 RC 0000, no warnings; SYSOUT equals expected.
Evidence: docs/evidence/mvs2-player.txt. Dialect notes: no reference modification (`X(1:1)`) - use
REDEFINES; end conditional performed paragraphs with `PERFORM ... THRU ...-EXIT`.
`tests/test_map.py` remains the local map-sync check; its MVS-1 runtime mode is superseded.

## MVS-3: pellets and score (2026-10-07)
PACMAIN adds SCORE (PIC 9(4)), PELLETS-LEFT (counted at init: 101 on LEVEL1), eat-on-entry (10 points), WIN
state and `S=`/`L=` fields in each status line; end lines `WIN|QUIT|EOF`, `TURNS nnn`, `SCORE nnnn`.
Build: `python3 tools/make_deck.py MVS3 && ./tools/submit.sh build/MVS3.jcl`, then
`./tools/job_output.py PACBLD03 > build/PACBLD03.txt && python3 tests/test_mvs3.py build/PACBLD03.txt`.
Cases: MOVES (revisit/bump score nothing), EOF, WIN (generated full-clear route of 185 turns plus one trailing
command that must be ignored; `tests/ref_mvs3.py --gen-win`). Expected output from `tests/ref_mvs3.py`.
Result: PACBLD03 JOB 119, all six steps RC 0000, no warnings; WIN run: 185 turns, SCORE 1010, L=000.
Evidence: docs/evidence/mvs3-pellets.txt. MVS-2 tests (test_mvs2.py) remain as local checks only; their
runtime expectations are superseded by the changed output format.

## MVS-4: basic ghost (2026-10-07)
PACMAIN adds one ghost (`G` on the board, `G=xx,yy` in each status line), AI0/AI1 config card and CAUGHT end.
Rules in docs/DECISIONS.md D9. Build: `python3 tools/make_deck.py MVS4 && ./tools/submit.sh build/MVS4.jcl`, then
`./tools/job_output.py PACBLD04 > build/PACBLD04.txt && python3 tests/test_mvs4.py build/PACBLD04.txt`.
Cases (tests/cases): MOVES, RAND (57 turns, ghost roams), CATCH1 (ghost walks into the player, found by model
search), WIN0 (AI0, full clear avoiding the ghost: 183 turns, 1000 points), CATCH0 (player walks into a still
ghost, trailing command ignored). Expected output from the independent `tests/ref_mvs4.py`; the runtime checker
also asserts the ghost never stands in a wall and moves at most one orthogonal step (zero in AI0).
Result: PACBLD04 JOB 120, SRC1/COB1/LINK/RUN1-5 all RC 0000, no warnings, outputs identical to the model.
Evidence: docs/evidence/mvs4-ghost.txt. MVS-3 runtime tests are superseded by the new format.

## MVS-5: lives and game cycle (2026-10-07)
PACMAIN adds LIVES, GAME-STATE (READY/RUNNING/WON/LOST/QUIT), respawn after a hit and the LOST end (rules: D11).
Build: `python3 tools/make_deck.py MVS5 && ./tools/submit.sh build/MVS5.jcl`, then
`./tools/job_output.py PACBLD05 > build/PACBLD05.txt && python3 tests/test_mvs5.py build/PACBLD05.txt`.
Twelve cases vs the independent model `tests/ref_mvs5.py`: MOVES, RAND, CATCH1 (ghost kills, play continues),
WIN0, CATCH0, DIE1 (die, move on, QUIT), LOST0 (three deaths = 72 turns, trailing command ignored),
WINAFTER (die once, then win with 2 lives), LOST1 (random ghost, game lost). Runtime invariants: lives drop by
exactly one per death, respawn cells, ghost steps/walls. The game is both winnable and losable.
Edge cases EDGE3/EDGE2/EDGE1 (last pellet + hit in one tick; WON with 2 or 1 lives, LOST with 0) were added afterwards.
Result: PACBLD05 (final run, JOB 122) 15 steps incl. RUN1-12 all RC 0000, no warnings. Evidence: docs/evidence/mvs5-lives.txt.

## MVS-6: smarter ghosts (2026-10-07)
PACMAIN: GHOST-TABLE (up to 3 ghosts), levels AI0-AI3 (rules: D14). Build: `python3 tools/make_deck.py MVS6 &&
./tools/submit.sh build/MVS6.jcl`, then `./tools/job_output.py PACBLD06 > build/PACBLD06.txt &&
python3 tests/test_mvs6.py build/PACBLD06.txt`. 19 runs vs the independent model `tests/ref_mvs6.py`:
the 12 MVS-5 cases (their output is byte-identical to MVS-5 apart from the header = regression) plus P2 (AI2),
P2N3 (AI2, 3 ghosts), R1N2 (AI1, 2 ghosts), C3WALK (chase while moving), C3 (waiting player is hunted down: LOST in
84 turns), C3N2 (two chasers: LOST in 21), MULTI (AI3, 3 ghosts, double hit costs one life).
The checker also re-derives from the real output that ghosts never enter walls, move one step, never reverse
(AI2/3), follow corridors (AI2), pick the first Manhattan minimum (AI3) and that lives fall by one per hit.
Result: PACBLD06 JOB 124 (first attempt JOB 123 failed to compile: nested subscripts, D13), 22 steps RC 0000.
Evidence: docs/evidence/mvs6-ai.txt.

## MVS-7: portability refactor (2026-10-07)
PACMAIN was split into PACMAIN/PACGAME/PACMAP/PACAI/PACINPT/PACDISP/PACPLAT + copybooks PACSTATE/PACREQ/PACMREQ
(see docs/ARCHITECTURE.md). No intended behaviour change. Build: `python3 tools/make_deck.py MVS7 &&
./tools/submit.sh build/MVS7.jcl`, then `./tools/job_output.py PACBLD07 > build/PACBLD07.txt &&
python3 tests/test_mvs7.py build/PACBLD07.txt`. The same 19 cases/expected files as MVS-6 are used (unchanged).
Checks: (1) all 37 steps RC 0000 (3 copybook + 7 source uploads, 7 compiles, link, 19 runs); (2) every run equals
the independent model; (3) BEFORE/AFTER: each SYSOUT block equals the pre-refactor evidence from JOB 124;
(4) the behaviour properties of MVS-6 re-derived from the real output; (5) static architecture rules (core has no
terminal/host verbs). Result: PACBLD07 JOB 126 (JOB 125 failed: copy members need their own 01 line, D16).
Evidence: docs/evidence/mvs7-refactor.txt. Load module is still HERC01.PACMAN.LOAD(PACMAIN).

## MVS-8: interactive TSO mode (2026-10-07, closed)
New: REQ-MODE/REQ-TEXT (PACREQ), PARM handling and TSO start flow in PACMAIN, mode validation + CLS in PACPLAT, prompt and
fresh-screen frames in PACDISP, TSO input rules in PACINPT, assembler stub src/asm/PACTSO.asm (assembled by IFOX00 in
the same deck), launcher CLIST (first install jcl/mvs/INSTCLST.jcl, update jcl/mvs/STORCLST.jcl). Details: D19, D20,
docs/INTERACTIVITY.md. Build: `python3 tools/make_deck.py MVS8 && ./tools/submit.sh build/MVS8.jcl`, then
`./tools/job_output.py PACBLD08 > build/PACBLD08.txt && python3 tests/test_mvs8.py build/PACBLD08.txt`.
Final result JOB 138: 43 steps RC 0000 + ASM1 RC 0; batch identical to MVS-7; 6 TSO replays pass. Manual c3270 validation
by the user on the same build. Evidence: docs/evidence/mvs8-interactive.txt (mvs8-tputprobe.txt: discarded TPUT path).
Earlier phase checkers now read the map literals from PACMAP.cob (moved there in MVS-7).

## MVS-9: release 1.0-MVS (2026-10-07)
- tools/make_deck.py gained `--prefix` and the decks ALLOC, CLIST, RUN and RELEASE (job PACREL10, same content as
  MVS8); tools/run_deck.py submits, waits for the new job number and saves build/<JOB>-<NO>.txt; tools/release_check.sh
  runs every local check, the RELEASE deck and tests/test_mvs8.py.
- From scratch under HERC01.PACMAN.R10: ALLOC JOB 139 RC 0 (4 libraries cataloged), CLIST JOB 140 RC 0, RELEASE JOB 141
  (43 steps RC 0000, ASM1 RC 0, no compiler/linker warnings, all checks PASS), RUN JOB 142 (WIN0 cards: WIN, 183 turns,
  1000 points). Evidence: docs/evidence/mvs9-fresh-r10-build.txt, mvs9-fresh-r10-install.txt.
- Default prefix: RELEASE JOB 143 PASS (docs/evidence/mvs9-release-build.txt); CLIST JOB 144 RC 0.
- Release decks and checksums: releases/1.0-MVS/. README rewritten with install, build, use and test instructions.

## MVS-G0: stable visual baseline (2026-10-07)
- Core frozen (D22): tests/core_baseline.json, tests/test_core_frozen.py, tools/core_baseline.py, docs/CORE_CHANGES.md.
- Oracle: `python3 tools/make_deck.py G0 && python3 tools/run_deck.py build/G0.jcl` (job PACBLDG0, = RELEASE content)
  must reproduce every 1.0-MVS block byte for byte. JOB 145: 43 steps RC 0000 + ASM RC 0, identical.
- Metrics and display replaceability: `python3 tools/make_deck.py G0X && python3 tools/run_deck.py build/G0X.jcl`
  (job PACG0X01, uses the installed load module). JOB 146: 10 steps RC 0000; METRICS lines match the values computed
  from the oracle output; PACALT (alternative display linked over PACMAIN) plays MOVES, MULTI and TSORDR with status
  lines identical to the oracle; core CSECT lengths identical (PACGAME FF8, PACMAP 858, PACAI E20).
- Check both: `python3 tests/test_g0.py build/PACBLDG0-<n>.txt build/PACG0X01-<n>.txt` -> MVS-G0 PASS.
- Capability matrix and cost baseline: docs/CAPABILITIES.md. Evidence: docs/evidence/g0-*.txt.
- Manual c3270 validation: docs/evidence/g0-manual-c3270.md (METRICS live 0004/00057/0001195/0003). G0 closed.

## MVS-G2: highlighting (2026-10-08)
`HILITE(AUTO|YES|NO)` (PARM column 13, REQ-HILITE appended to PACREQ), SA X'41' orders in PACSCR, values in PACPAL
(D26, docs/G2-HIGHLIGHT.md). Build + tests: `python3 tools/make_deck.py G2 && python3 tools/run_deck.py build/G2.jcl`, then
`python3 tests/test_g2.py build/PACBLDG2-<n>.txt`. JOB 164 (JOB 162/163: compiler warning IKF4072 in PACSCR, fixed by not
ending a paragraph with a conditional PERFORM): 56 steps RC 0000, no warnings, oracle byte-identical, 132 TSC screens
identical to tests/ref_g2_screen.py. CLIST reinstalled (JOB 165). Evidence: docs/evidence/g2-build-tsd.txt.
Validated live in c3270 by the user (docs/evidence/g2-manual-c3270.md). G2 closed (tag mvs-g2).

## MVS-G3: partial redraw + character animation (2026-10-08)
Probe E6 first (docs/evidence/g3-probe-analysis.md, JOB 167). Then PACSCR virtual image/diff, PACFSIO SENP/RECT, options ANIM/REDRAW
(D27, docs/G3-PARTIAL.md). Build + tests: `python3 tools/make_deck.py G3 && python3 tools/run_deck.py build/G3.jcl`, then
`python3 tests/test_g3.py build/PACBLDG3-<n>.txt`. JOB 168 failed the zero-warning rule (IKF4072 in PACSCR), JOB 169: 61 steps RC 0000,
oracle identical, 199 TSC streams identical to tests/ref_g3_screen.py. CLIST reinstalled (JOB 170).
Live test found the idle tick not running (TGET default WAIT blocks): RECT now TGET ASIS,NOWAIT, rebuilt JOB 172 (same 61 steps, same results). Idle ticks then ran only after the first command: RECTRACE
diagnostic counters added to PACPLAT (print only with M; JOB 174, regression identical) to see the first wait before choosing a fix.
Diagnosis (docs/G3-PARTIAL.md, docs/evidence/g3-tick-trace.md): TSO holds the idle ticks after the COLOR(AUTO) capability query until
the first input; BREAKIN (JOB 183), TCLEARQ INPUT (JOB 185) and FSOF+FSON (JOB 187) refuted and withdrawn; investigation closed (D28).
Final build JOB 188 (instrumentation removed, = JOB 184/186 state): 61 steps RC 0000, no warnings, oracle identical, 199 streams = model.
CLIST gained METRICS(NO|YES) (column 11, D23) - CLIST JOB 175. Final manual checklist PASS; G3 closed (tag mvs-g3). Evidence: docs/evidence/g3-build-tsd.txt.

## MVS-G4: glyph profiles (2026-10-08)
Probe E9 first (APL/CP310 via GE and SA X'43', full Query Reply; JOB 189/190, CLOSED PASS, docs/evidence/g4-probe-analysis.md).
Design approved: docs/G4-GLYPHS.md (D29). Changed: PACREQ (+REQ-GLYPHS), PACPAL (tile/glyph tables), PACSCR (profiles, GE per cell,
wall mask, facing), PACPLAT (glyph resolution, reply parsed by the new pure PACQRY), PACMAIN (PARM column 16), CLIST (GLYPHS).
New: src/cobol/PACQRY.cob, src/cobol/PACQRYT.cob (batch driver), tests/ref_g4_screen.py, tests/test_g4.py, tests/qry_cases.py,
tests/qreply_c3270.hex, tests/cases/FACE.txt. Core and PACFSIO untouched.
Build + tests: `python3 tools/make_deck.py G4 && python3 tools/run_deck.py build/G4.jcl`, then
`python3 tests/test_g4.py build/PACBLDG4-<n>.txt`. JOB 191: 82 steps RC 0000, no compiler warnings, oracle identical, 460 TSC streams
(12 G3 runs = CLASSIC + 14 G/B/C/A runs) identical to the independent model, 12 recorded Query Replies parsed as expected by PACQRY.
CLIST reinstalled (JOB 192). Live: mechanics PASS, but the neighbour-mask wall tiles were rejected (docs/evidence/g4-wall-diagnosis.md).
Revision (D29): filled walls (blank + wall colour + reverse when highlighting is on, `#` otherwise), tiles removed. JOB 193 SE37 on
the COBOL library -> new deck `make_deck.py COMPRESS` (JOB 194, IEBCOPY in place). JOB 195: 82 steps RC 0000, oracle identical,
460 streams = model, 12 PACQRY cases, 98 LEVEL1 wall cells occupied in all 460 replayed screens.
Evidence: docs/evidence/g4-build-tsd.txt (JOB 195). Live c3270 PASS (docs/evidence/g4-manual-c3270.md: GRAPHIC/BASE/CLASSIC/AUTO,
partial redraw with GE, filled walls, HILITE(NO) fallback). Core and PACFSIO unchanged. G4 closed (tag mvs-g4).

## MVS-G1 (in progress): step 1, 3270 capability probe
Separate probe program (not linked into the game): src/probe/PACG1P.cob + src/probe/PACFS.asm (STFSMODE, TPUT NOEDIT
Read Partition Query, TGET ASIS, TPUT FULLSCR colour/highlight screen generated by tools/g1_probe_screen.py), launcher
CLIST G1PROBE. Build: `python3 tools/make_deck.py G1P && python3 tools/run_deck.py build/G1P.jcl`. JOB 149: all steps
RC 0000; batch run reports "NOT A TSO SESSION: NOTHING SENT" (no SVC issued outside TSO). Live run pending.

## MVS-G1: colour renderer TSC (2026-10-07)
Probes E1-E5: docs/evidence/g1-probe-analysis.md. Implementation (D24): src/asm/PACFSIO.asm (full-screen service),
src/cobol/PACSCR.cob (screen composer), copybooks PACPAL (palette/layout) and PACDS (data stream buffer), PACPLAT
(INIT colour selection, SEND/RECV/FSOF, fallback), PACDISP/PACINPT/PACMAIN (TSC/TSD routing), CLIST COLOR keyword.
Build + tests: `python3 tools/make_deck.py G1 && python3 tools/run_deck.py build/G1.jcl`, then
`python3 tests/test_g1.py build/PACBLDG1-<n>.txt`. JOB 160 (clear-buffer prefix; JOB 157 first build, JOB 159 black-screen variant): 54 steps RC 0000, no compiler/assembler warnings; the 25
batch/TSO oracle blocks byte-identical to 1.0-MVS; 88 TSC screens (5 TSD dry runs) byte-identical to the independent
Python renderer. CLIST reinstalled (JOB 158). Evidence: docs/evidence/g1-build-tsd.txt. Final build JOB 161 (length fix in PACFSIO SEND, D25) validated live in c3270: clean colour screen, R, Q, READY.
The ESTAE abend-restore exit is implemented but not validated live. G1 closed (tag mvs-g1).

## MVS-G5: Programmed Symbols experimental (2026-10-08) - closed negative (capability limit, D30)
Isolated probe E10, nothing of PACMAN changed: tools/gen_probe_e10.py -> src/probe/PACFSA.asm, src/probe/PACG5P.cob, CLIST G5PROBE.
Build: `python3 tools/make_deck.py G5P && python3 tools/run_deck.py build/G5P.jcl` (job PACG5P01). JOB 196: 6 steps RC 0000, severity 0,
batch `RC=0004 LOADRC= NONE`. Live (c3270 -trace): `RC=0012 QLEN=0180 SCRNS=0002 AID=7D LOADRC=0000 ILEN=0053`; Query Reply = E9, no
loadable sets; Load PS `unsupported ID 0x06`, no terminal response; set C1 shows the base set, APL control works. LOADRC = host TPUT
accepted the send; ILEN 53 = tail of the screen-1 ENTER record beyond the 256-byte key TGET (not a response). Evidence:
docs/evidence/g5-probe-build.txt, g5-probe-analysis.md, g5-c3270-e10-window.txt. G6 blocked (depends on PS).

## MVS-GS: scaled renderer (2026-10-08)
Study + probe E11 (JOB 198) and design docs/GS-SCALED.md (approved, D31). Implementation in PACSCR/PACPAL/PACREQ/PACMAIN/PACPLAT/
PACDISP/PACTSO/CLIST (core and PACFSIO untouched). Build + tests: `python3 tools/make_deck.py GS && python3 tools/run_deck.py
build/GS.jcl`, then `python3 tests/test_gs.py build/PACBLDGS-<n>.txt`. COMPRESS JOB 199 first. JOB 200: 100 steps RC 0000, no
warnings, oracle identical, 931 streams = models (26 G4 runs = SCALE(NO) regression + 18 GS runs), 395 scaled streams replayed on
a 3270 image = model. CLIST reinstalled (JOB 201). Evidence: docs/evidence/gs-build-tsd.txt. Live: 4x2 proportions PASS.
Geometry (D32, docs/GS-GEOMETRY.md): probe E12 (JOBs 202/203, docs/evidence/gs-e12-geometry.md); implementation deck `GX`:
`python3 tools/make_deck.py GX && python3 tools/run_deck.py build/GX.jcl`, then `python3 tests/test_gx.py build/PACBLDGX-<n>.txt`.
COMPRESS JOB 204; JOB 207: 117 steps RC 0000, oracle identical, 1371 streams = models, 394 W x H replays = model. CLIST JOB 208.
Evidence: docs/evidence/gs-geometry-build-tsd.txt. Live PASS (docs/evidence/gs-manual-c3270.md). MVS-GS closed (tag mvs-gs).


## MVS-S1: sound (2026-10-11)
Probe E15 first (isolated: src/probe/PACS1P.cob + PACS1A.asm from tools/gen_probe_e15.py + the unchanged PACFSIO; deck `S1P`,
JOB 228; live PASS `ANS=NYYY33`, docs/evidence/s1-e15-alarm.md). Implementation (D35): PACREQ +REQ-SOUND/REQ-BELL, PACMAIN PARM
column 20, PACPLAT (SOUND resolution, SET-ALARM on the WCC), PACDISP (SET-BELL, end bell-only write), CLIST SOUND(AUTO); the
core, PACRT, PACSCR, PACINPT, PACFSIO and PACTSO unchanged. Reference models gained an optional (lives, won) snapshot hook
(tests/ref_snap.py). Build + tests: `python3 tools/make_deck.py S1 && python3 tools/run_deck.py build/S1.jcl`, then
`python3 tests/test_s1.py build/PACBLDS1-<n>.txt`. JOB 230: IKF4072I-W (SET-ALARM ended with an IF); JOB 231: SE37 in LINK
(LOAD full) -> `make_deck.py COMPRESS` now also compresses LOAD (JOB 232). JOB 233: 161 steps RC 0000, no warnings, test_rt
PASS on the RT part, 15 SOUND runs = model (1785 streams, 38 bells), 3 silent runs = oracle/model. CLIST JOB 234.
Evidence: docs/evidence/s1-build-tsd.txt. Live 1: bells PASS; game end 0C4-4 from a latent RT2 PACTSO defect (WAIT fell
into DOTIME), fixed by one `B DONE` (docs/evidence/s1-live-0c4.md); COMPRESS JOB 235, rebuild JOB 236 PASS. Live retest pending.

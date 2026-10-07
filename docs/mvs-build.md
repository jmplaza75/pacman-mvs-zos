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

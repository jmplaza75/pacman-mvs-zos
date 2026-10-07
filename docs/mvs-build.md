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

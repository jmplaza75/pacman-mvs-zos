# MVS-S1 live: PACMAIN ENDED DUE TO ERROR at every game end - diagnosis and fix (2026-10-11)
Live run (user): `TYPEAHEAD=false tools/c3270_rt.sh ~/s1-live2.txt`, `python3 tools/rt_play.py` with SOUND(AUTO) and with
SOUND(NO). Bells PASS (start and death with AUTO, silent with NO). Every game end (LOST and QUIT, both SOUND values)
showed `PACMAIN  ENDED DUE TO ERROR+` then READY, and no end lines (LOST/TURNS/SCORE/LIVES/QUANTA).

## Findings
1. Code: `?` at READY (sent through the c3270 script port) -> `SYSTEM ABEND CODE 0C4   REASON CODE 004`.
2. Same path for LOST and QUIT: both end a scaled game with PACDISP SCR-ENDS = the end-banner screen (SEND), then
   PACPLAT WAIT -> PACTSO 'WAIT' (3 s), then FSOF. Trace (first game): last death frame `Write(reset,alarm,restore)`
   20:13:42.543, end banner `EraseWriteAlternate` 20:13:42.545, nothing for 3.0 s, then 20:13:45.553 TSO line mode
   (`EraseWriteAlternate` + `PACMAIN  ENDED DUE TO ERROR+`, then `READY`). Five games, five identical endings.
3. Last operation: PACPLAT WAIT -> PACTSO WAIT. src/asm/PACTSO.asm since RT2 (commit ad94b2d):
   ```
   PAUSE    STIMER WAIT,BINTVL=WAITT
            SR    4,4
   DOTIME   L     5,8(1)       <- no branch: WAIT fell into TIME
            LA    5,0(5)
            BAL   14,NOWMS
            ST    1,0(5)       <- clock stored at an address taken from garbage
   ```
   RT2 inserted DOTIME/DODLWT between PAUSE and DONE (in mvs-gs PAUSE fell into DONE). WAIT is called with two
   parameters, so 8(R1) (R1 left by STIMER) is not a parameter address: a wild 4-byte store -> 0C4-4 when it hits
   protected storage, silent corruption when it does not.
4. Terminal restoration: the abend came after the 3 s pause and BEFORE FSOF; TSO was back in line mode at READY, i.e.
   the PACFSIO ESTAE exit (FSON) restored line mode and percolated (the G1 pending note - consistent with the exit
   working; not a controlled test). The end lines were DISPLAYed or not yet; either way the SYSOUT buffer was lost
   with the abend.
5. The S1 additions are not involved: the failing instruction is in PACTSO, which S1 did not change; it happens with
   SOUND(NO), where no S1 code runs in the live path apart from option resolution.
6. mvs-rt baseline: PACTSO in mvs-rt is byte-identical (tests/test_s1.py asserted it), so the defect is there too. The
   RT3 live QUIT ended cleanly because the wild store then landed on writable storage (the load module layout changed
   since). Batch cannot reach PAUSE (not TSO: WAIT returns before it), so no batch test could see it.

## Fix
`B DONE` after `SR 4,4` in PAUSE (one added line, PACTSO). tests/test_s1.py asserts PACTSO = mvs-rt + that line and
that every PACTSO block ending at DOTIME/DODLWT/LATE/DONE/NOWMS/SAVE ends with an unconditional branch.
Build JOB 236 (after COMPRESS JOB 235): 161 steps RC 0000, tests/test_s1.py PASS (RT/GX/TURN regression and 1.0-MVS
oracle unchanged, 15 SOUND runs = model with 38 bells, 3 silent runs = oracle/model). Live retest pending.

# MVS-S1 live validation in c3270 (user, 2026-10-11)
Build: Hercules JOB 236 (deck S1, tests/test_s1.py PASS), CLIST SOUND(AUTO) JOB 234. Terminal: `TYPEAHEAD=false
tools/c3270_rt.sh <trace>` (120x27 IBM-DYNAMIC), macOS Terminal "Audible bell" on, games started by `python3
tools/rt_play.py`. Traces stay outside the repository (they contain the logon).

## Live 1 (`~/s1-live2.txt`, JOB 233 build) - bells PASS, game end FAIL
Start and death bells with SOUND(AUTO), silence with SOUND(NO). Every game end (5 games, LOST and QUIT) abended
0C4-4: latent RT2 defect in PACTSO (WAIT fell into DOTIME) -> docs/evidence/s1-live-0c4.md, fixed, rebuilt JOB 236.

## Live 2 - retest after the PACTSO fix (`~/s1-live3.txt`, JOB 236 build)
| Check (user) | Result |
|---|---|
| SOUND(AUTO): start bell, death bells | PASS |
| SOUND(AUTO): GAME OVER screen, ~3 s wait, LOST/TURNS/SCORE/LIVES/QUANTA, READY, no ENDED DUE TO ERROR | PASS |
| SOUND(NO): completely silent, end lines, READY, no ENDED DUE TO ERROR | PASS |

Trace (raw host records, WCC = second byte):
```
game 1 SOUND(AUTO)  20:48:02-20:48:38  96 writes, 4 with the alarm bit:
  20:48:02.271 F1 C7  first game screen (start)
  20:48:23.972 F1 C6  death 1
  20:48:29.526 F1 C6  death 2
  20:48:34.503 F1 C6  death 3 (last), then 20:48:34.504 EraseWriteAlternate = GAME OVER banner, no alarm
  20:48:37.516 line mode (3.0 s later): LOST / TURNS 064 / SCORE 0590 / LIVES 0 / QUANTA 0000090 / READY
game 2 SOUND(NO)    20:49:08-20:49:30  108 writes, 0 with the alarm bit
  20:49:26.347 GAME OVER banner (3 deaths, silent); 20:49:29.349 line mode:
  LOST / TURNS 069 / SCORE 0620 / LIVES 0 / QUANTA 0000102 / READY
`PACMAIN ENDED DUE TO ERROR`: 0 occurrences.
```
Note: both traced games ended LOST (GAME OVER). The ENTER at 20:49:28.765 came during the 3 s banner wait of game 2,
after the end; no QUIT banner appears in this trace. The QUIT end runs the same path (end screen, PACPLAT WAIT ->
PACTSO WAIT, FSOF) with another banner text; the QUIT end screen and its end lines are covered in batch (TSD) by
tests/test_s1.py (S1T1, S1T5, S1T9, S1T10, S1R5) and tests/test_rt.py.

## Live 3 - QUIT end after the fix (`~/s1-live4.txt`, JOB 236 build) - PASS
User checklist: start bell, Q + ENTER while alive, QUIT banner, ~3 s wait, QUIT/TURNS/SCORE/LIVES/QUANTA, READY, no
ENDED DUE TO ERROR - all PASS. Trace:
```
31 writes, 1 with the alarm bit: 20:53:44.994 F1 C7 (first game screen = start)
20:53:53.664 inbound ENTER with 'Q'
20:53:53.691 EraseWriteAlternate = QUIT end banner (no alarm)
20:53:56.703 line mode (3.0 s later): QUIT / TURNS 000 / SCORE 0000 / LIVES 3 / QUANTA 0000000 / READY
`PACMAIN ENDED DUE TO ERROR`: 0 occurrences.
```
Q was entered before the first arrow (TURNS 000, QUANTA 0: the clock had not started); the end path is the same
(end screen, PACPLAT WAIT -> PACTSO WAIT, FSOF), the one that abended in live 1.
Result: MVS-S1 live PASS - bells (start, death, last death), SOUND(NO) silent, LOST and QUIT ends clean.

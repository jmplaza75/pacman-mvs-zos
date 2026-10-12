# MVS-GP2 GP2.4 live acceptance in c3270 - trace analysis
Build of record GP2.3: JOB 246 (deck GP23) + JOB 247 (deck GP2); CLIST JOB 248. 120x27 IBM-DYNAMIC, trace
`~/gp2-live.txt` (outside the repository), driver `tools/gp2_live.py` (commit 0513790), analysis
`tools/c3270_gp2_trace.py TRACE --scenario X --from HHMMSS` (live writes replayed through tests/ref_gp2.py + the screen
models, byte for byte; write 0 carries the platform clear prefix 11 40 40 3C 40 40 00 that the TSD dry run does not
print). Checklist: docs/evidence/gp2-live-checklist.md.

## Run 1 (user, 2026-10-12 13:24-13:26; driver log ~/gp2-live-driver.log)
The user saw all three scenarios run to the end and return to READY. Trace analysis:
| Scenario | --from | Live writes = model | Alarm writes | Result |
|---|---|---|---|---|
| A (REALTIME, level 1) | 132452 | 103 / 103 ALL IDENTICAL | [0] | game correct for the inputs received, but the planned route was NOT played: 100 quanta instead of 200, score 0000170, no fruit, no level clear (driver defect below) |
| B (TURN, LEVEL(13)) | 132542 | 78 / 78 ALL IDENTICAL | [0, 76] | PASS, exactly as planned |
| C (REALTIME, LEVEL(13)) | 132558 | 45 / 45 ALL IDENTICAL | [0, 29] | game correct for the inputs received, but desynchronised: 43 quanta, one death at Q29, no extra life (driver defect below) |
No live / model discrepancy in any scenario: every host write equals the model for the inputs that reached the host.

### Scenario B (accepted): 78/78 writes identical, alarms [0, 76]
Fresh LEVEL(13) game (score 0, 3 lives, HUD LEVEL 13 / KEY 5000, AI0); T2 and T6 power pellets with a 4-turn fright
(level 1: 20); T32 key fruit shown, T38 eaten (score 0005440); T74 second key shown, T76 eaten: score 0010780, extra
life (4 lives, 4th icon) and its alarm on write 76; Q: QUIT / TURNS 0000076 / SCORE 0010780 / LIVES 4 / GHOSTS EATEN
0000 / FRUITS EATEN 002 / LEVEL 013, back at READY.

### Driver defect found in run 1 (GP2.4 test-tool integration, not gameplay)
Driver log timings: after a card that sends a key, `Wait(5,Output)` blocked for one host write (A median 146 ms, C
136 ms); after an idle card ('.', no key) it returned at once (median 7 ms, 100 of 100 in A, 104 of 104 in C). c3270's
Wait(Output) only waits for output after an AID, so the REALTIME driver ran ahead of the quanta and sent the route keys
too early (A: 201 cards in 100 quanta). TURN (B) sends a key on every card and was not affected.
Fix (tools/gp2_live.py, scenarios unchanged): an idle card sends PF1. In REALTIME PF1 is ignored by the game (PACINPT
RT-TSC: every AID other than PF7-PF11, PA2 and ENTER is IGN, dropped by PACMAIN RT-EVENT before PACRT: no input, no
frame change) and the analyser maps it to '.', so every card is one AID and every Wait(Output) blocks for one host
write. Self-test: synthetic traces of A and C with a PF1 on every idle quantum replay ALL IDENTICAL with the alarm
writes [0, 184] and [0, 44, 113, 145]. Scenarios A and C are to be rerun with the fixed driver.

## Run 2 (user, 2026-10-12 13:32-13:34, fixed driver commit ca39c67): A and C rerun; B accepted from run 1
Trace `~/gp2-live2.txt`. Both scenarios ran with the expected live timing (A 38 s, C 27 s from the driver start to
READY) and returned to READY. The cards rebuilt from the trace equal the scenario files exactly (A 202, C 148), i.e.
the driver delivered every key in its quantum. Host write gaps: median 150 ms, p95 160 / 159 ms.
```
$ python3 tools/c3270_gp2_trace.py ~/gp2-live2.txt --scenario A --from 133253
game writes: live 203, model 203, identical 203 | ALL IDENTICAL      (write 0 carries the clear prefix)
writes with the alarm bit (WCC X'04'): [0, 184]
end: QUIT / TURNS 0000188 / SCORE 0001350 / LIVES 3 / QUANTA 0000200 / GHOSTS EATEN 0000 / FRUITS EATEN 001 / LEVEL 002
$ python3 tools/c3270_gp2_trace.py ~/gp2-live2.txt --scenario C --from 133350
game writes: live 149, model 149, identical 149 | ALL IDENTICAL      (write 0 carries the clear prefix)
writes with the alarm bit (WCC X'04'): [0, 44, 113, 145]
end: QUIT / TURNS 0000110 / SCORE 0010850 / LIVES 1 / QUANTA 0000147 / GHOSTS EATEN 0000 / FRUITS EATEN 002 / LEVEL 013
```
### Scenario A - REALTIME, RULES(ARCADE) AI(0) GHOSTS(1), LEVEL default 1
Start: HUD LEVEL 01 / CHERRY 0100, alarm on write 0. Q2 / Q6 power pellets (fright 40). Q32 fruit appears (item 30,
BT 60); Q52 Pac-Man enters (10,8): fruit eaten, +100. Q78 second fruit appears; Q95 / Q99 power pellets with the fruit
shown (BT 43 / 39). After Q108 pause (PAUSED write 109, held 3033 ms) and resume: BT 030 before and after - the fruit
timer and the level stood still. Q121 PA2 full redraw with the fruit shown (BT 018, LEVEL 01): identical to the model.
Q138 the untouched fruit expires: exactly 60 running quanta after Q78 (the pause not counted). Q183 last item: level
clear (flag C), alarm on write 184, maze refilled (L=100), Pac-Man (2,2) and the ghost home, LAST `L CLEARED`, LEVEL 02,
STRAWBERRY 0300; freeze Q184-Q193 = writes 185-194, 1493 ms (1.5 s, normal 150 ms scheduling afterwards, no catch-up).
Q197 PA2 full redraw on level 2 (LEVEL 02 kept), then the power pellet at (2,4): fright 34 quanta (level 1: 40).
Q200 Q: end banner, line mode QUIT ... LEVEL 002, READY.
### Scenario C - REALTIME, RULES(ARCADE) AI(2) GHOSTS(1) LEVEL(13)
Start: LEVEL 13 / KEY 5000, AI2 + 2 = AI3 (HUD GHOSTS AI3, chasing ghost), normal ghosts on the 9/10 step; alarm on
write 0. Q2 / Q6 power pellets: fright 7 quanta (1.05 s; level 1: 40). Q40 key appears, Q43 eaten (0005410). Q44 the
ghost catches Pac-Man: death (flag D), alarm on write 44, lives 2, freeze 1502 ms. Q89 power pellet (fright 7). Q113
second death: alarm on write 113, lives 1, freeze 1505 ms. Q136 second key appears; Q145 Pac-Man eats it (0010850:
extra life at 10000) and is caught in the same quantum (flags F X D): ONE alarm on write 145, lives 1 + 1 - 1 = 1.
Q147 Q: end banner, line mode QUIT ... LEVEL 013, READY.

## Result - GP2.4 PASS (all three scenarios = the independent model, every host write byte for byte)
| Item | Evidence |
|---|---|
| ARCADE level HUD | A LEVEL 01 -> 02, B / C LEVEL 13, fruit name + points per level |
| fruit appearance / eating / timeout | A Q32 / Q52 / Q78 -> Q138 (60 quanta); B T32 / T38, T74 / T76; C Q40 / Q43, Q136 / Q145 |
| pause and PA2 with the fruit active | A pause after Q108 (3 s, BT 030 unchanged), PA2 Q121 (BT 018) |
| level clear, 1.5 s freeze, refill, LEVEL 02 | A Q183, writes 185-194 = 1493 ms, L=100, LEVEL 02 / STRAWBERRY |
| level-clear bell | A alarm writes [0, 184] |
| LEVEL(13) start, shorter frights | B (4 turns), C (7 quanta), A level 2 (34 quanta) |
| two 5000-point keys, extra life at 10000, 4th life icon | B T38 / T76: 0010780, LIVES 4, alarm write 76 |
| AI2 -> effective AI3 at level 13 | C HUD GHOSTS AI3, chase moves = model |
| death / freeze | C Q44 and Q113: alarms, 10-quantum freezes (1502 / 1505 ms) |
| extra life + death in one quantum = one alarm | C Q145, alarm writes [0, 44, 113, 145] |
| QUIT and READY | A, B, C: end banner, line-mode end lines, READY |
No live / model discrepancy in either run. The only defect found was in the GP2.4 test driver (run 1, fixed in
ca39c67, scenarios unchanged).

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

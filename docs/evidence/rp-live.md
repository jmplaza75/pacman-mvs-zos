# MVS-RP RP.4 live session - trace analysis (session 1)
Installed build: PACMAIN deck RP JOB 286, CLIST JOB 287. Session (user, 2026-10-13 20:08-20:32), c3270 120x27
IBM-DYNAMIC, trace `~/rp4-live.txt` (outside the repository; nothing before the first RPESTAE screen is read, inbound
records by AID byte only). The user's report arrived as the empty template; every result below comes from the trace.
TK4- wait limit: `JWT=60` (SMFPRM00, JOB 288, read-only): rp-live-checklist.md.

## Part A - D40 reproduction + NORMAL ARCADE game to GAME OVER
| Item | Trace | Result |
|---|---|---|
| A1 E3 control abend | 20:08:43 RPESTAE CASE E3 screen; ENTER; `RPE E3 LINE MODE RESTORED, FORCING 0C7`, `PACRPE ENDED DUE TO ERROR+`, READY (20:08:46.924) | PASS |
| A2 `***` reproduced | EXEC ENTER 20:09:10.686 -> blank line -> `***` 20:09:10.745 | PASS |
| A3 ENTER at `***` -> full screen | user ENTER 20:09:27.335 -> query (WSF F3 00 05 01 FF 02) -> reply AID 88 (184 bytes) -> ARCADE game screen 20:09:27.890; no line-mode game, no INVALID COMMAND | **PASS (D40 case b)** |
| Replay `c3270_gp2_trace.py --cfg 'AI1 1' --from 200920` | **262 / 262 writes = NORMAL models**, alarms [0, 125, 216, 254], model end lines = live (LOST / TURNS 0000160 / SCORE 0001020 / LIVES 0 / QUANTA 0000254 / ... / HIGH SCORE 0001430 LEVEL 001) | PASS |
| Death animation (2 deaths in play) | 6 frames 1-6, 899 / 894 ms; READY! 4 writes 609 / 601 ms | PASS |
| A5 final death + GAME OVER end screen + end lines + READY | final frames 1-6 (781 ms: FINAL-DEATH starts its own clock, the end screen follows the last frame at once), GAME OVER screen, LOST lines, READY 20:10:36 | PASS |
| Timers | fright 6010 ms (design 6000), freezes 1508 / 1495 ms (1500), fruit popup 6 writes 900 ms | PASS |
| Timing (`c3270_rt_game.py --from 200920`, 150 ms) | 261 writes over 261 periods; gap median 150, p95 160, max 319 ms; lateness median 5, p95 15 ms; 0 skipped; drift +1.9 ms / 100 quanta; 2 late writes, next 19 / 21 ms; keyboard lock median 75, p95 131, max 151 ms | PASS |
| A4 P during a death freeze; PA2 during a freeze | **not exercised**: no PF9 in Part A; the one PA2 came at Q173, outside both freezes (Q126-135, Q217-226) | NOT DONE live (Hercules: RPLOST, edges pause-freeze / redraw-freeze, JOB 285) |

## Part B - soak at SPEED(FAST)
| Item | Trace | Result |
|---|---|---|
| B1 10-minute pre-start hold | game screen 20:10:56.181, first arrow 20:11:21.889: **25.7 s**, not 10 minutes | **NOT DONE** |
| (instead) 10.75 minutes of unattended running play | 5164 quanta 20:11:21.918-20:22:07.433 on one arrow; one death (alarm, freeze 12) | extra endurance evidence |
| Schedule over the run | quantum 1 -> quantum 5164 = 645515 ms vs 5163 x 125 = 645375 ms (+140 ms = the last write's lateness): **no period skipped by the host in 10.75 min**; lateness median 7, p95 14 ms; drift -0.3 ms / 100 quanta; 8 late writes (7 in 20:21:49-20:22:06), each followed by one < 1 period late | PASS |
| Delivery bunching | 20:21:57.097 four writes in one millisecond after a 503 ms silence (and 3 within 5 ms at 20:22:06): more than the 2 back-to-back writes the host schedule can produce, so held downstream of the host (TN3270 / network / client); the host count above confirms no skip | noted (not a game fault) |
| B3 10-minute pause | PF9 20:22:07.518, PAUSED, 603 s, PF9 20:32:11.030; no abend / S522 | **PASS (soak)** |
| B4 resume, no catch-up | first frames +123, +249, +374, +499 ms after the resume; 189 writes over 189 periods, lateness median 5 / p95 12 ms, 0 skipped | **PASS (FAST pause / resume)** |
| Controls after the resume | 24 arrows in 23 s, keyboard lock median 68 / p95 108 / max 116 ms (whole game) | PASS |
| Q + ENTER | QUIT end lines, READY 20:32:37 | PASS |
| Replay `--speed F --from 201050 --cards docs/evidence/rp4-partB-cards.txt` | **5357 / 5357 writes = FAST models**, alarms [0, 864], end lines = live (QUIT / TURNS 0000136 / SCORE 0001390 / LIVES 2 / QUANTA 0005354 / GHOSTS EATEN 0001 / FRUITS EATEN 002) | PASS |
| Timers / decorations | freeze 1498 ms, eyes 3004, fright 6057 (one late write inside; design 1500 / 3000 / 6000); death 7 frames 1 1 2 3 4 5 6 873 ms; READY! 5 writes 625 ms; popups 7 writes 869-881 ms | PASS |

Card attribution note (Part B): the greedy search of the tool put the pause P one card early; the two P placements and
then each post-resume arrow were settled by a local search (each AID moved by one card when that made more writes
identical) until all 5357 matched; the resulting cards are kept (rp4-partB-cards.txt, game inputs only) and replay
with `--cards`.

## Tool fixes made during this analysis
- tools/c3270_rt_game.py: slots as DO-WDLN schedules them (a held write keeps its slot; skipped slots counted only after
  a write late by >= one period); the stretch reference is its first write.
- tools/c3270_gp2_trace.py: no trimming of trailing idle cards (a LOST game needs them), `timing()` defined before the
  entry point, `--cards`.

## Coverage exceptions (accepted by the user, 2026-10-13; no retest)
1. **10-minute pre-start hold (B1): not performed live.** The live start hold was 25.7 s (game screen 20:10:56.181,
   first arrow 20:11:21.889). The same session then showed 10.75 minutes (5164 quanta) of stable unattended REALTIME
   execution at SPEED(FAST) with no skipped period, and a separate 603 s live pause soak (B3/B4) with no abend and no
   catch-up. The pre-start WAIT itself was not held for 10 minutes live; this document does not claim it was.
2. **Pause during a death freeze and PA2 during a death freeze (A4): not observed in the human live route.** Part A had
   no PF9, and its one PA2 (Q173) fell outside both freezes. Both combinations are covered deterministically on
   Hercules: case `tests/rpcases/RPLOST` (pause + PA2 inside the first death freeze; RP edges `pause-freeze` and
   `redraw-freeze`) in deck RP JOB 285 / JOB 286, TSD streams = the independent models byte for byte. This document
   does not claim those two exact combinations were seen live.
The user accepted this mixed live + deterministic coverage as sufficient for the RP closure (same practice as GP1).

## Verdict
RP.4 PASS with the two documented coverage exceptions. Live: D40 case (a) (rp3-fast-live.md) and case (b), Part A
262/262 and Part B 5357/5357 writes = the models, FAST timing (no skip, no drift), the 10-minute pause soak, timers and
decorations measured. MVS-RP closed (tag `mvs-rp`).

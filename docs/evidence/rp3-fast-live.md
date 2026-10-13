# MVS-RP RP.3 FAST live capture - trace analysis
Installed build: PACMAIN deck RP JOB 286, CLIST JOB 287. Session (user, 2026-10-13 19:32-19:34): c3270 120x27
IBM-DYNAMIC, `tools/c3270_rt.sh ~/rp3-fast-live.txt` (trace outside the repository), `tools/rt_play.py 'RULES(ARCADE)'
'SPEED(FAST)'` (AI1 1, SOUND AUTO, persistent high score 0001430). Analysis reads nothing before the game title (the
startup records are shown by AID byte only).

End state (live line mode = model): QUIT / TURNS 0000189 / SCORE 0001410 / LIVES 2 / QUANTA 0000342 / GHOSTS EATEN 0001
/ FRUITS EATEN 002 / LEVEL 001 / HIGH SCORE 0001430 LEVEL 001, then READY.

## 1. Timing (`tools/c3270_rt_game.py ~/rp3-fast-live.txt --period 125`)
| Measure | Value |
|---|---|
| Pre-start READY! wait | 25.0 s, 1 write (no frames before the first arrow) |
| Running writes | 343 writes over 343 periods (42.8 s): one write per quantum, no skipped period |
| Frame gap (write to write) | median 125 ms, p95 133 ms, max 282 ms; 2 gaps > 187 ms, 2 gaps < 20 ms (the pair after each late write) |
| Lateness against the absolute grid (t0 + k x 125 ms) | median 7 ms, p95 13 ms, max 160 ms |
| Late writes (> 62 ms) | 2 of 343: slot 183 (19:33:58.776, 160 ms) and slot 196 (19:34:00.400, 159 ms; the PA2 arrived in the same millisecond) |
| Recovery | the write after each: 35 / 34 ms late (sent at once, same TCP read), the next 3 / 28 ms: back on the grid; no period skipped |
| Drift | +0.5 ms per 100 quanta (median lateness first / last third 6 / 7 ms): none |
| Keyboard lock per AID (47 AIDs: 45 arrows, PA2, ENTER) | median 59 ms, p95 118 ms, max 121 ms (< one period); no lock left open (no persistent X Wait) |
| Headroom | writes leave a median 7 ms (p95 13 ms) after their deadline: the quantum's game step, screen build and TPUT fit in a small part of 125 ms |

The two late writes are isolated host-side delays (a write held ~160 ms, then the next one due immediately behind it
in the same TCP read) of the same kind as the single 236 ms late wake at 150 ms in RT3 (docs/evidence/rt3-live.md);
the absolute schedule absorbed both without skipping or drifting.

Tool notes (fixed while analysing, tools/c3270_rt_trace.py `split_eor`): c3270 traced each late pair as ONE block with
two telnet records (two IAC EOR); the loader now splits blocks at every IAC EOR. Before the fix the pair looked like a
skipped period and the replay saw 342 instead of 344 writes.

## 2. Replay (`tools/c3270_gp2_trace.py ~/rp3-fast-live.txt --cfg 'AI1 1' --speed F`)
**344 of 344 live writes = the FAST models byte for byte (ALL IDENTICAL)**, write 0 with the platform clear prefix;
alarm writes [0, 267] (start, the death); model end lines = the live ones. Inputs: 45 arrows + PA2 + Q rebuilt into
342 quantum cards; every AID consumed in its quantum, in order (no stale typeahead backlog; c3270 typeahead off).
Tool notes: the HUD high score is read from write 0 (`HIGH` + SBA + 7 digits); ambiguous AIDs (sent within 60 ms
before a write) are attributed greedily (0, +1 or +2 writes: the PA2 shared its millisecond with a two-write block).

Game events (model state = what was on the screen): Q24 / Q28 power pellets, Q44 fruit shown (BT 72), Q54 fruit eaten,
Q81 / Q87 power pellets, Q92 ghost eaten (eyes 24), Q103 fruit shown (BT 72), Q141 fruit eaten, Q199 PA2 full redraw,
Q267 death (alarm), freeze Q268-Q279 (12 quanta), Q342 Q.

## 3. Wall-clock of the converted timers (live write times; quanta = model)
| Timer | Quanta (FAST) | Live ms | Quanta x 125 | NORMAL design |
|---|---|---|---|---|
| fright (Q28 pellet -> Q76) | 48 | 5999 | 6000 | 40 x 150 = 6000 |
| eyes wait (Q92 -> Q116) | 24 | 2998 | 3000 | 20 x 150 = 3000 |
| fright (Q87 pellet -> Q135) | 48 | 5997 | 6000 | 6000 |
| death freeze (Q267 -> last frozen Q279) | 12 | 1501 | 1500 | 10 x 150 = 1500 |
| fruit | 72 loaded (BT=072 at both spawns) | not run out: both fruits eaten (Q44->Q54, Q103->Q141) | 9000 | 60 x 150 = 9000 |

## 4. Decorations as shown (write runs; time from the first write showing it to the first write without it)
| Decoration | Writes | ms | Expected (design 6, FAST) |
|---|---|---|---|
| READY! before the start | 1 (held 25.0 s) | - | until the first direction |
| popup FRUIT 0100 (Q54-Q60) | 7 | 873 | t0..t0+6 = 7 frames, 875 ms |
| popup GHOST 0200 (Q92-Q98) | 7 | 872 | 7 frames |
| popup FRUIT 0100 (Q141-Q147) | 7 | 883 | 7 frames |
| death animation (Q267-Q273) | 7, frames 1 1 2 3 4 5 6 | 875 | 7 frames, 150 ms each |
| READY! after the death (Q274-Q278) | 5 | 626 | last 5 freeze quanta, 625 ms |

## 5. Startup (D40 case a, installed build)
EXEC ENTER (19:33:10.666) -> `7E C3` -> query (WSF `F3 00 05 01 FF 02`) -> reply AID 88 (184 bytes) -> game screen
`F1 C7` 47 ms later: the clean wire shape, no extra read.

## 6. Not exercised in this capture
- Pause / resume at FAST: no PF9 in the trace (no pause was taken). Folded into the RP.4 soak, which is run at
  SPEED(FAST) (docs/evidence/rp-live-checklist.md).
- Fruit run-out at FAST: covered on Hercules (deck RP JOB 285, RP3TIM: 72 quanta, model and TSD/BAT identical); live
  the loaded value (72) was confirmed by the replay.

## Decision gate (user, 2026-10-13)
Headroom adequate (median 7 ms, p95 13 ms past the deadline), no accumulating lateness (drift +0.5 ms / 100 quanta),
2 isolated late writes recovered at once, input / keyboard restore unaffected, rendering byte-identical: **FAST meets
the gate; SPEED(FAST) kept.** Pause / resume at FAST to be confirmed by the RP.4 soak.

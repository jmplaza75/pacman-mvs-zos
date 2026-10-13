# MVS-S2 S2.4 live acceptance (2026-10-13, 22:39-22:46) - PASS
Checklist: docs/evidence/s2-live-checklist.md. Installed build: PACMAIN JOB 297 / 298, CLIST JOB 299 (commit f993a64).
Trace `~/s2-live.txt` (outside the repository: it holds the logon), driver log `~/gp2-live-driver.log`. Analysis:
`python3 tools/c3270_s2_trace.py ~/s2-live.txt --scenario <S2x> --from <start>` (S2A run 2 also with `--aids`).

## Runs in the trace (driver log)
| Run | Start | Scenario | Played as scripted? |
|---|---|---|---|
| 1 | 22:39:35 | S2A ARCADE NORMAL PATTERN | yes (117 AIDs = the 117 cards) |
| 2 | 22:40:03 | S2A again | no: a DOWN arrow (PF8) not in the scenario reached the host at card 8 and 15 idle PF1s are missing (102 AIDs); a different game (LOST in 114 quanta, TURNS 9) |
| 3 | 22:40:38 | S2B ARCADE FAST PATTERN | yes (201 / 201) |
| 4 | 22:41:17 | S2D ARCADE NORMAL SINGLE | yes (117 / 117) |
| 5 | 22:41:50 | S2E CLASSIC NORMAL SOUND(NO) | yes (183 / 183) |
| 6 | 22:45:49 | S2C CLASSIC NORMAL PATTERN, win | yes (183 / 183); run after the first analysis, which found it missing |

## Byte-for-byte replay against the models
| Run | Live writes = model | Alarm writes (live = model) | Bells per event | Gaps inside a pattern (ms) | End screen -> line mode | Cadence (median / p95, late) |
|---|---|---|---|---|---|---|
| S2A 1 | **125 / 125 ALL IDENTICAL** | [0, 27, 29, 72, 74, 117, 119, 121] | START 1, DEATH 2, DEATH 2, OVER 3 | 297, 298 / 333, 295 (G = 300) | 3011 ms | 149 / 166 ms, 0 > 225 ms |
| S2A 2 (`--aids`) | **122 / 122 ALL IDENTICAL** (cards rebuilt from the AIDs) | [0, 24, 26, 69, 71, 114, 116, 118] | START 1, DEATH 2, DEATH 2, OVER 3 | 302, 298 / 329, 294 | 3007 ms | 150 / 160 ms, 0 |
| S2B | **202 / 202 ALL IDENTICAL** | [0, 183, 186, 189] | START 1, CLEAR 3 | 371, 374 (G = 375) | 3007 ms (QUIT, silent) | 125 / 133 ms, 0 > 188 ms |
| S2D | **125 / 125 ALL IDENTICAL** | [0, 27, 72, 117] | 4 single bells | - | 3010 ms | 150 / 161 ms, 0 |
| S2E | **185 / 185 ALL IDENTICAL** | [] (no alarm bit anywhere, no bell-only write) | - | - | 3002 ms | 150 / 157 ms, 0 |
| S2C | **188 / 188 ALL IDENTICAL** | [0, 183, 185, 186, 187] (185-187 = bell-only writes after the end screen 184) | START 1, WIN 4 | 304, 309, 300 | 3011 ms; bell-only writes at +302, +611, +911 ms | 150 / 158 ms, 0 |
End lines (line mode) = the model in every run; every run returned to `READY`.

## Findings
- The host sends exactly the modelled alarm writes in every run: patterns 1 / 2 / 3 bells in active play at NORMAL
  (S2A: deaths 2, game over 3 over the final death frames, 0.30 s apart within +-5 ms; the one 329-333 ms gap is the
  first game-over step: the final death frames are paced from a fresh clock read after the deciding write (RP
  FINAL-DEATH: CLOK, then WDLN), so the grid shifts once by that write's send time - existing RP timing, unchanged), 3 bells at
  FAST (S2B: 371 / 374 ms for G = 3 x 125 ms); ALARM(SINGLE) = the S1 / GP2 single bell per event (S2D);
  SOUND(NO) silent with the end pause unchanged (S2E).
- No regression of cadence or input: every running stretch at the period (median 149-150 / 125 ms), no late write;
  the end pause stays 3.0 s (3002-3011 ms from the end screen to the first line-mode record) in every run.
- S2A run 2: the extra DOWN arrow is an input outside the driver (a key pressed in c3270 while the scenario ran, or a
  keyboard event); the missing PF1s are idle quanta (no effect: the replay with the AIDs that arrived is exact). The
  program behaved exactly as modelled for the game it was given.

- S2C: the length-4 pattern - 1 bell on the deciding quantum, then 3 bell-only writes inside the end pause, 300 ms
  apart (+302 / +611 / +911 ms after the end screen) - and the end pause still 3.0 s (3011 ms): the bells fit inside
  it and never lengthen it (D41 5).

## Audible acceptance (the user)
- S2C: **PASS** - "4 distinct bells for the WIN pattern" (user, 2026-10-13).
- S2A, S2B, S2D, S2E: **PASS** - the user observed no audible anomaly in these scenarios and accepted them together
  with their trace evidence (user, 2026-10-13).

## Verdict
S2.4 **PASS** (user scope of 2026-10-13): PATTERN bells audible and separate (S2C heard; S2A / S2B accepted); lengths
1 (start, every run), 2 (S2A deaths), 3 (S2A game over in play, S2B level clear at FAST), 4 (S2C win); active-play
patterns at NORMAL (300 ms) and FAST (375 ms); the end pattern on bell-only writes inside the unchanged 3-s pause;
ALARM(SINGLE) = the historical single bell (S2D); SOUND(NO) silent (S2E); every live write = the models byte for byte
(six runs, 947 writes; S2A run 2 replayed from the AIDs the host actually received - a stray DOWN arrow, missing idle
PF1s - and still byte-identical); cadence at the period, no late write, clean READY after every run.
MVS-S2 closed on this evidence (user approval 2026-10-13, tag `mvs-s2`).

## References
Design docs/S2-PATTERNS.md (D41); build and install docs/evidence/s2-build-tsd.txt (deck S2 JOB 290, SINGLE regression
RP 291 / GP2 293 / HS 294, install S2 297 / RP 298 into PACMAIN, CLIST 299); live checklist
docs/evidence/s2-live-checklist.md; tools tools/gp2_live.py S2A-S2E, tools/c3270_s2_trace.py (`--aids`), scenarios
tests/s2live (tests/s2live/make_live.py).

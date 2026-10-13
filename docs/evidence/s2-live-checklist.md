# MVS-S2 S2.4 live acceptance in c3270 - checklist (prepared 2026-10-13; to be run by the user)
Installed build of record: HERC01.PACMAN.LOAD(PACMAIN) = JOB 297 (deck S2 checks) / JOB 298 (RP checks, last link,
same sources, commit baea879 + the run_step JCL fix); CLIST JOB 299 (default `ALARM(PATTERN)`). Evidence of the build
and install: docs/evidence/s2-build-tsd.txt.

Scope (user, 2026-10-13): the live run proves what the **terminal makes audible**; the mapping of all six events is
proved deterministically (deck S2: 25 TSD runs = model, 21 D41 edges). Nothing is played by hand: five short
deterministic scenarios are sent by `tools/gp2_live.py` through the c3270 script port (keys only; card k = the input of
quantum k, idle quanta = PF1, which the game ignores), each cut exactly at its game end. Each is then replayed from the
c3270 trace by `tools/c3270_s2_trace.py` (every live host write vs the independent model byte for byte, the alarm
writes, the gaps between bells, the end pause, the cadence). Scenario cards: `tests/s2live/LIVE[A-E].txt`
(`tests/s2live/make_live.py`, from the Hercules-tested cases RTSTILL, G2RCLR, RTWIN).

What the live run must show (user's S2.4 scope) and where:
| Requirement | Scenario |
|---|---|
| ALARM(PATTERN) audible as separate bells | A, B, C |
| pattern lengths 1, 2, 3 and 4 bells | 1 = start (all), 2 = death (A), 3 = game over (A) and level clear (B), 4 = win (C) |
| a multi-bell pattern in active play at NORMAL (2 quanta = 300 ms) | A (deaths: 2; game over: 3 on the final death frames) |
| a multi-bell pattern in active play at FAST (3 quanta = 375 ms) | B (level clear: 3) |
| an end-of-game pattern on bell-only writes inside the 3-s end pause | C (win: 1 bell on the last quantum + 3 in the pause) |
| ALARM(SINGLE) = the historical single bell | D (= A: 4 single bells) |
| SOUND(NO) completely silent | E (= C: no bell, end pause still 3 s) |
| no cadence / input regression, no extra delay, clean READY | every scenario (analyser cadence line; READY) |

## 0. Setup (about 2 minutes)
1. Hercules / TK4- running. macOS Terminal: window 120 x 30 or larger BEFORE connecting; Settings > Profiles >
   Advanced > "Audible bell" ON (and "Visual bell" OFF, so only the sound is judged); system volume up.
2. Terminal 1: `TYPEAHEAD=false tools/c3270_rt.sh ~/s2-live.txt` (trace OUTSIDE the repository: it holds the logon).
   Log on as HERC01 by hand and stay at `READY`.
3. Terminal 2 (repository directory): the commands below, one after the other, each from `READY`. Do not type in
   c3270 while a scenario runs. Note for each scenario the bells you hear (count and whether they are separate).

## 1. Scenario A - ARCADE, NORMAL, PATTERN (about 20 s): `python3 tools/gp2_live.py S2A`
`RULES(ARCADE) AI(3) GHOSTS(1)`; Pac-Man moves right once and then waits; the chasing ghost catches him three times.
| When (quantum, about Q x 0.15 s) | Expected sound | Check |
|---|---|---|
| start | 1 bell | length 1 |
| first death (write 27, ~4 s) | 2 bells, 300 ms apart, during the death animation | length 2, in play, NORMAL spacing |
| second death (write 72, ~11 s) | 2 bells, 300 ms apart | |
| last death (write 117, ~18 s) | 3 bells, 300 ms apart, over the final death animation; then the GAME OVER banner, 3 s, `READY` | length 3 in play |
Model alarm writes: [0, 27, 29, 72, 74, 117, 119, 121].

## 2. Scenario B - ARCADE, FAST, PATTERN (about 25 s): `python3 tools/gp2_live.py S2B`
`RULES(ARCADE) AI(0) GHOSTS(1) SPEED(FAST)`: the full-clear route of level 1 (still ghost), then Q.
| When | Expected sound | Check |
|---|---|---|
| start | 1 bell | |
| last pellet (write 183, ~23 s) | 3 bells, 375 ms apart, during the level-clear freeze (maze refilled, `LEVEL 02`) | length 3 in play at FAST, separate |
| Q | QUIT banner (silent), 3 s, `READY` | QUIT never rings |
Model alarm writes: [0, 183, 186, 189].

## 3. Scenario C - CLASSIC, NORMAL, PATTERN, win (about 30 s): `python3 tools/gp2_live.py S2C`
`RULES(CLASSIC) AI(0) GHOSTS(1)`: the 1.0-MVS full-clear route (WIN0) in REALTIME.
| When | Expected sound | Check |
|---|---|---|
| start | 1 bell | |
| last pellet (write 183, ~27 s) | 4 bells, 300 ms apart: the first on the last frame, then the YOU WIN banner and 3 more while it stays on screen | length 4; end pattern inside the pause |
| after the banner | still 3 s (not longer) to line mode, then `READY` | pause not lengthened |
Model alarm writes: [0, 183, 185, 186, 187] (185-187 = the bell-only writes after the end screen 184).

## 4. Scenario D - as A with ALARM(SINGLE) (about 20 s): `python3 tools/gp2_live.py S2D`
Expected: 1 bell at the start, 1 at each of the three deaths (4 single bells in all), as before S2.
Model alarm writes: [0, 27, 72, 117].

## 5. Scenario E - as C with SOUND(NO) (about 30 s): `python3 tools/gp2_live.py S2E`
Expected: no bell at all (start, win, end pause); the YOU WIN banner stays 3 s; `READY`.

## 6. After the run
`LOGOFF` in c3270 if you like, then tell Claude the trace file and what you heard (per scenario: bell count, separate or
merged, anything odd). The analysis (one line per scenario, run by Claude):
```
python3 tools/c3270_s2_trace.py ~/s2-live.txt --scenario S2A --from <HHMMSS of the scenario start>
```
(the start times are in the driver log `~/gp2-live-driver.log`). Pass = every live write identical to the model, the
AIDs = the scenario cards, alarm writes = the model, pattern gaps = G periods (300 / 375 ms, a few ms of host jitter),
end pause about 3 s, cadence median = the period, and your audible counts = the table above.
